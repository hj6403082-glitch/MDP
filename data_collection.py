"""
data_collection.py - raw telemetry collection for Phase 1 of the MDP
Causal-AI-for-Air-Pollution pipeline.

What it does
------------
1. Resolves each configured city name to coordinates (Open-Meteo geocoding).
2. Fetches hourly historical air-quality data from OpenAQ (v3) for the primary
   pollutants (PM2.5, PM10, SO2, NO2, CO, NO, VOCs) and the secondary pollutant
   (Ozone) at monitoring stations near each city.
3. Fetches the matching hourly weather from Open-Meteo's historical archive
   (air temperature, relative humidity, wind speed, atmospheric pressure) for
   the same coordinates and date range.
4. Merges air-quality + weather on the hourly timestamp into one tidy table per
   city, with column names that line up with the Phase 1 config
   (``timestamp``, ``station_id`` id-columns; ``ozone``, ``pm25``, ``no2`` ...).
5. Writes Parquet (Spark-optimised) and optionally uploads straight to your
   Dataproc staging bucket via ``google-cloud-storage``.

The output schema matches ``config/pipeline_config.py`` defaults, so the files
drop into ``MDP_INPUT_PATH`` and Phase 1 reads them with no further mapping.

This is a *local* ETL utility (single-node pandas is appropriate here — it is
the step that *creates* the telemetry the Spark pipeline later consumes).

Quick start
-----------
    export OPENAQ_API_KEY="<your key from https://explore.openaq.org/account>"
    pip install -r requirements.txt

    python data_collection.py \
        --start 2023-01-01 --end 2023-12-31 \
        --gcs-prefix gs://YOUR_BUCKET/raw/telemetry/

    # Collect locally only (no upload), e.g. to inspect first:
    python data_collection.py --start 2023-01-01 --end 2023-03-31 --no-upload
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mdp.data_collection")


# ===========================================================================
# ## FILL THIS IN  ↓↓↓  — the cities to collect (highly polluted urban /     ##
# ## industrial areas). Plain names are fine; they are geocoded for you.     ##
# ===========================================================================
CITIES: List[str] = ["CITY_1", "CITY_2"]
# ===========================================================================


# OpenAQ parameter name -> our pipeline column name. Only parameters that a
# station actually reports are collected; the rest are simply absent (and the
# pipeline tolerates missing/NaN columns). 'o3' is renamed to 'ozone' to match
# the Phase 1 config's secondary-pollutant name.
POLLUTANT_PARAM_MAP: Dict[str, str] = {
    "pm25": "pm25",
    "pm10": "pm10",
    "so2": "so2",
    "no2": "no2",
    "co": "co",
    "no": "no",
    "o3": "ozone",
    # VOCs are reported inconsistently across networks; map the common codes.
    "voc": "voc",
    "nmhc": "voc",
}

# Open-Meteo hourly weather variable -> our pipeline column name.
WEATHER_VAR_MAP: Dict[str, str] = {
    "temperature_2m": "temperature",
    "relative_humidity_2m": "relative_humidity",
    "wind_speed_10m": "wind_speed",
    "surface_pressure": "pressure",
}

OPENAQ_BASE = "https://api.openaq.org/v3"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Be a good API citizen: OpenAQ's free tier is rate-limited (~60 req/min).
REQUEST_PAUSE_SEC = 1.1
MAX_RETRIES = 5


# --------------------------------------------------------------------------- #
# HTTP helper with retries, backoff and 429 (rate-limit) handling
# --------------------------------------------------------------------------- #
def _get(url: str, *, params: Optional[dict] = None,
         headers: Optional[dict] = None) -> dict:
    """GET a JSON endpoint with exponential backoff and rate-limit respect."""
    backoff = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.get(url, params=params, headers=headers, timeout=60)
        if resp.status_code == 429:  # rate limited - honour Retry-After if given
            wait = float(resp.headers.get("Retry-After", backoff))
            logger.warning("Rate limited; sleeping %.1fs (attempt %d)", wait, attempt)
            time.sleep(wait)
            backoff *= 2
            continue
        if resp.status_code >= 500:  # transient server error
            logger.warning("HTTP %d from %s; retrying in %.1fs",
                           resp.status_code, url, backoff)
            time.sleep(backoff)
            backoff *= 2
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Giving up on {url} after {MAX_RETRIES} attempts.")


# --------------------------------------------------------------------------- #
# 1) Geocoding: city name -> coordinates
# --------------------------------------------------------------------------- #
@dataclass
class GeoCity:
    name: str
    latitude: float
    longitude: float


def geocode_city(name: str) -> Optional[GeoCity]:
    """Resolve a city name to coordinates via Open-Meteo's geocoder (no key)."""
    data = _get(GEOCODE_URL, params={"name": name, "count": 1, "format": "json"})
    results = data.get("results") or []
    if not results:
        logger.error("Could not geocode city %r - skipping.", name)
        return None
    r = results[0]
    geo = GeoCity(name=name, latitude=float(r["latitude"]),
                  longitude=float(r["longitude"]))
    logger.info("Geocoded %r -> (%.4f, %.4f)", name, geo.latitude, geo.longitude)
    return geo


# --------------------------------------------------------------------------- #
# 2) OpenAQ: find nearby stations and fetch hourly pollutant series
# --------------------------------------------------------------------------- #
def _openaq_headers() -> dict:
    key = os.environ.get("OPENAQ_API_KEY")
    if not key:
        raise SystemExit(
            "OPENAQ_API_KEY is not set. Get a free key at "
            "https://explore.openaq.org/account and `export OPENAQ_API_KEY=...`."
        )
    return {"X-API-Key": key}


def find_sensors(geo: GeoCity, radius_m: int, max_locations: int
                 ) -> List[Tuple[int, int, str]]:
    """Return ``(location_id, sensor_id, pollutant_column)`` tuples for stations
    near ``geo`` that report one of our target pollutants.
    """
    headers = _openaq_headers()
    data = _get(
        f"{OPENAQ_BASE}/locations",
        params={"coordinates": f"{geo.latitude},{geo.longitude}",
                "radius": radius_m, "limit": max_locations},
        headers=headers,
    )
    time.sleep(REQUEST_PAUSE_SEC)

    sensors: List[Tuple[int, int, str]] = []
    for loc in data.get("results", []):
        loc_id = loc["id"]
        for sensor in loc.get("sensors", []):
            param = (sensor.get("parameter") or {}).get("name", "").lower()
            if param in POLLUTANT_PARAM_MAP:
                sensors.append((loc_id, sensor["id"], POLLUTANT_PARAM_MAP[param]))
    logger.info("%s: %d matching sensors across nearby stations",
                geo.name, len(sensors))
    return sensors


def fetch_sensor_hours(sensor_id: int, start: str, end: str) -> List[dict]:
    """Fetch hourly-aggregated measurements for one sensor over [start, end].

    Pages through the OpenAQ v3 hourly endpoint. Returns a list of
    ``{"timestamp": <ISO utc>, "value": <float>}`` dicts.
    """
    headers = _openaq_headers()
    rows: List[dict] = []
    page = 1
    while True:
        data = _get(
            f"{OPENAQ_BASE}/sensors/{sensor_id}/hours",
            params={"datetime_from": start, "datetime_to": end,
                    "limit": 1000, "page": page},
            headers=headers,
        )
        results = data.get("results", [])
        for r in results:
            # v3 hourly results carry the period start under period.datetimeFrom.
            period = r.get("period", {}) or {}
            dt = (period.get("datetimeFrom") or {}).get("utc")
            value = r.get("value")
            if dt is not None and value is not None:
                rows.append({"timestamp": dt, "value": float(value)})
        time.sleep(REQUEST_PAUSE_SEC)
        # Stop when the last page returned fewer than the page size.
        if len(results) < 1000:
            break
        page += 1
    return rows


def collect_pollutants(geo: GeoCity, start: str, end: str, radius_m: int,
                       max_locations: int):
    """Build a wide hourly pollutant DataFrame (timestamp, station_id, <species>)."""
    import pandas as pd

    sensors = find_sensors(geo, radius_m, max_locations)
    long_records: List[dict] = []
    for loc_id, sensor_id, column in sensors:
        hours = fetch_sensor_hours(sensor_id, start, end)
        for h in hours:
            long_records.append({
                "timestamp": h["timestamp"],
                "station_id": f"{geo.name}:{loc_id}",
                "parameter": column,
                "value": h["value"],
            })
    if not long_records:
        logger.warning("%s: no pollutant measurements returned.", geo.name)
        return None

    long_df = pd.DataFrame(long_records)
    long_df["timestamp"] = pd.to_datetime(long_df["timestamp"], utc=True).dt.floor("h")
    # Average duplicate (timestamp, station, parameter) readings, then pivot to
    # one column per pollutant species.
    wide = (
        long_df.groupby(["timestamp", "station_id", "parameter"])["value"]
        .mean()
        .unstack("parameter")
        .reset_index()
    )
    wide.columns.name = None
    return wide


# --------------------------------------------------------------------------- #
# 3) Open-Meteo: hourly weather for the same coordinates / range
# --------------------------------------------------------------------------- #
def collect_weather(geo: GeoCity, start: str, end: str):
    """Fetch hourly weather and return a DataFrame (timestamp, <weather cols>)."""
    import pandas as pd

    data = _get(
        WEATHER_ARCHIVE_URL,
        params={
            "latitude": geo.latitude, "longitude": geo.longitude,
            "start_date": start, "end_date": end,
            "hourly": ",".join(WEATHER_VAR_MAP.keys()),
            "timezone": "UTC",
        },
    )
    hourly = data.get("hourly", {})
    if not hourly or "time" not in hourly:
        logger.warning("%s: no weather data returned.", geo.name)
        return None

    df = pd.DataFrame(hourly).rename(columns=WEATHER_VAR_MAP)
    df["timestamp"] = pd.to_datetime(df["time"], utc=True).dt.floor("h")
    df = df.drop(columns=["time"])
    return df


# --------------------------------------------------------------------------- #
# 4) Merge + write Parquet
# --------------------------------------------------------------------------- #
def build_city_table(geo: GeoCity, start: str, end: str, radius_m: int,
                     max_locations: int):
    """Merge pollutant + weather into one hourly table for a city."""
    pollutants = collect_pollutants(geo, start, end, radius_m, max_locations)
    if pollutants is None:
        return None
    weather = collect_weather(geo, start, end)

    merged = pollutants
    if weather is not None:
        # Left join: weather is city-level, broadcast onto each station row.
        merged = pollutants.merge(weather, on="timestamp", how="left")
    merged.insert(2, "city", geo.name)
    merged = merged.sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    logger.info("%s: merged table %d rows x %d cols",
                geo.name, len(merged), merged.shape[1])
    return merged


def write_parquet(df, local_dir: str, city: str) -> str:
    """Write a city DataFrame to a local Parquet file; return its path."""
    os.makedirs(local_dir, exist_ok=True)
    safe = city.lower().replace(" ", "_").replace("/", "_")
    path = os.path.join(local_dir, f"telemetry_{safe}.parquet")
    # Snappy-compressed Parquet via pyarrow - exactly what Phase 1's Spark
    # reader expects.
    df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)
    logger.info("Wrote %s", path)
    return path


# --------------------------------------------------------------------------- #
# 5) Upload to GCS
# --------------------------------------------------------------------------- #
def parse_gs_uri(uri: str) -> Tuple[str, str]:
    """Split ``gs://bucket/prefix/`` into ``(bucket, prefix)``."""
    if not uri.startswith("gs://"):
        raise ValueError(f"Not a gs:// URI: {uri!r}")
    without = uri[len("gs://"):]
    bucket, _, prefix = without.partition("/")
    return bucket, prefix.strip("/")


def upload_to_gcs(local_path: str, gcs_prefix: str) -> str:
    """Upload a local file under ``gs://bucket/prefix/`` and return the gs URI."""
    from google.cloud import storage

    bucket_name, prefix = parse_gs_uri(gcs_prefix)
    blob_path = f"{prefix}/{os.path.basename(local_path)}" if prefix \
        else os.path.basename(local_path)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
    uri = f"gs://{bucket_name}/{blob_path}"
    logger.info("Uploaded -> %s", uri)
    return uri


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run(args: argparse.Namespace) -> int:
    if any(c.startswith("CITY_") for c in CITIES):
        logger.warning(
            "CITIES still contains placeholders %s - edit the CITIES list at "
            "the top of data_collection.py before a real run.", CITIES)

    written: List[str] = []
    for name in CITIES:
        geo = geocode_city(name)
        if geo is None:
            continue
        table = build_city_table(
            geo, args.start, args.end, args.radius, args.max_locations)
        if table is None or table.empty:
            logger.warning("No data collected for %s - skipping.", name)
            continue
        local_path = write_parquet(table, args.local_dir, name)
        written.append(local_path)
        if not args.no_upload:
            upload_to_gcs(local_path, args.gcs_prefix)

    if not written:
        logger.error("No telemetry was collected for any city.")
        return 1
    logger.info("Done. %d city file(s) written%s.", len(written),
                "" if args.no_upload else " and uploaded")
    return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Collect air-quality + weather telemetry and stage it as "
                    "Parquet for the MDP Phase 1 pipeline.")
    p.add_argument("--start", required=True, help="Start date, YYYY-MM-DD (UTC).")
    p.add_argument("--end", required=True, help="End date, YYYY-MM-DD (UTC).")
    p.add_argument("--gcs-prefix", default="gs://YOUR_BUCKET/raw/telemetry/",
                   help="Destination gs:// prefix for the Parquet files.")
    p.add_argument("--local-dir", default="./telemetry_out",
                   help="Local directory for the Parquet files before upload.")
    p.add_argument("--radius", type=int, default=12000,
                   help="Search radius around each city centre, metres "
                        "(OpenAQ max 25000).")
    p.add_argument("--max-locations", type=int, default=50,
                   help="Max monitoring stations to pull per city.")
    p.add_argument("--no-upload", action="store_true",
                   help="Write Parquet locally only; skip the GCS upload.")
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.exit(run(parse_args(sys.argv[1:])))
