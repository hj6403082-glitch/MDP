"""
data_collection.py - country-scale raw telemetry collection for Phase 1 of the
MDP Causal-AI-for-Air-Pollution pipeline.

Scope: the entire country of India (OpenAQ ``countries_id=9`` / ISO ``IN``).

What it does
------------
1. Dynamically fetches ALL OpenAQ (v3) monitoring locations in India (paged).
2. Extracts each station's coordinates and the sensors that report our target
   pollutants (PM2.5, PM10, SO2, NO2, CO, NO, VOCs, Ozone).
3. For each station: pulls hourly pollutant series from OpenAQ and the matching
   hourly weather (temperature, humidity, wind speed, pressure) from Open-Meteo,
   merges them on the hourly timestamp, and writes one Parquet file per station.
4. Optionally uploads each Parquet straight to the Dataproc staging bucket.

Designed for a massive job without falling over
-----------------------------------------------
* **Rate limits / transient errors**: every HTTP call retries with exponential
  backoff + jitter and honours ``Retry-After`` on HTTP 429; network errors and
  5xx are retried too. After the retry budget is exhausted the *station* is
  skipped (logged), never the whole run.
* **Weather call amplification**: Open-Meteo weather is cached by a rounded
  coordinate grid (default 0.1deg ~ 11 km). Clustered stations reuse one weather
  fetch, cutting weather calls from thousands to hundreds.
* **Resumability**: each station writes its own ``telemetry_IN_<id>.parquet``.
  On restart, stations whose file already exists are skipped, so a crash never
  restarts from zero. Spark reads the whole output directory as one dataset.
* **Politeness**: a configurable pause between calls keeps you under the free
  tier's per-minute ceiling.

Output columns match ``config/pipeline_config.py`` (``timestamp``/``station_id``
id-columns, ``ozone``, ``pm25`` ...), so the files feed Phase 1 directly.

Quick start
-----------
    export OPENAQ_API_KEY="<key from https://explore.openaq.org/account>"
    pip install -r requirements.txt

    # Smoke-test on 10 stations, locally, before the full run:
    python data_collection.py --start 2023-01-01 --end 2023-03-31 \
        --limit-locations 10 --no-upload

    # Full country run, uploading to your bucket:
    python data_collection.py --start 2023-01-01 --end 2023-12-31 \
        --gcs-prefix gs://YOUR_BUCKET/raw/telemetry/
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mdp.data_collection")


# ===========================================================================
# Geographic scope: the whole country of India.
# ===========================================================================
COUNTRY_ID = 9       # OpenAQ v3 countries_id for India
COUNTRY_ISO = "IN"   # used only for labelling output rows / filenames
# ===========================================================================


# OpenAQ parameter name -> our pipeline column name. 'o3' -> 'ozone' to match
# the Phase 1 config's secondary-pollutant name. Parameters a station does not
# report are simply absent (the pipeline tolerates missing/NaN columns).
POLLUTANT_PARAM_MAP: Dict[str, str] = {
    "pm25": "pm25",
    "pm10": "pm10",
    "so2": "so2",
    "no2": "no2",
    "co": "co",
    "no": "no",
    "o3": "ozone",
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
WEATHER_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Retry / politeness defaults (overridable via CLI).
MAX_RETRIES = 6
BACKOFF_BASE = 2.0
BACKOFF_CAP = 120.0
PAGE_SIZE = 1000


# --------------------------------------------------------------------------- #
# HTTP helper: retries, exponential backoff + jitter, 429 / 5xx / network
# --------------------------------------------------------------------------- #
def http_get_json(url: str, *, params: Optional[dict] = None,
                  headers: Optional[dict] = None,
                  max_retries: int = MAX_RETRIES) -> Optional[dict]:
    """GET JSON, surviving rate limits and transient failures.

    Returns the parsed JSON, or ``None`` if the retry budget is exhausted (the
    caller decides whether to skip that unit of work rather than crash).
    """
    backoff = BACKOFF_BASE
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=90)
        except requests.exceptions.RequestException as exc:
            # DNS / connection reset / read timeout: back off and retry.
            wait = min(backoff, BACKOFF_CAP) + random.uniform(0, 1.0)
            logger.warning("Network error on %s (%s); retry %d/%d in %.1fs",
                           url, exc.__class__.__name__, attempt, max_retries, wait)
            time.sleep(wait)
            backoff = min(backoff * 2, BACKOFF_CAP)
            continue

        if resp.status_code == 429:
            # Respect Retry-After when provided, else exponential backoff.
            wait = float(resp.headers.get("Retry-After", backoff)) + random.uniform(0, 1.0)
            logger.warning("Rate limited (429) on %s; sleeping %.1fs (retry %d/%d)",
                           url, wait, attempt, max_retries)
            time.sleep(wait)
            backoff = min(backoff * 2, BACKOFF_CAP)
            continue

        if resp.status_code >= 500:
            wait = min(backoff, BACKOFF_CAP) + random.uniform(0, 1.0)
            logger.warning("HTTP %d on %s; retry %d/%d in %.1fs",
                           resp.status_code, url, attempt, max_retries, wait)
            time.sleep(wait)
            backoff = min(backoff * 2, BACKOFF_CAP)
            continue

        if resp.status_code == 404:
            return None  # nothing there; caller treats as "no data"

        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            logger.error("Unrecoverable HTTP error on %s: %s", url, exc)
            return None
        return resp.json()

    logger.error("Giving up on %s after %d attempts.", url, max_retries)
    return None


def _openaq_headers() -> dict:
    key = os.environ.get("OPENAQ_API_KEY")
    if not key:
        raise SystemExit(
            "OPENAQ_API_KEY is not set. Get a free key at "
            "https://explore.openaq.org/account and `export OPENAQ_API_KEY=...`."
        )
    return {"X-API-Key": key}


# --------------------------------------------------------------------------- #
# 1) + 2) Fetch all India locations and their coordinates / sensors
# --------------------------------------------------------------------------- #
@dataclass
class Station:
    loc_id: int
    name: str
    latitude: float
    longitude: float
    # (sensor_id, pollutant_column) for sensors reporting target pollutants.
    sensors: List[Tuple[int, str]] = field(default_factory=list)


def _utc_date(value) -> Optional[str]:
    """Pull a 'YYYY-MM-DD' date from an OpenAQ datetime field, which is either a
    ``{"utc": "...", "local": "..."}`` dict or a plain ISO string."""
    if isinstance(value, dict):
        value = value.get("utc")
    return value[:10] if isinstance(value, str) else None


def _coverage_overlaps(loc: dict, start: str, end: str) -> bool:
    """True if a location's reported data coverage overlaps ``[start, end]``.

    OpenAQ returns location-level ``datetimeFirst`` / ``datetimeLast``. A
    station that never reported (``datetimeLast`` missing) is treated as dead.
    ISO ``YYYY-MM-DD`` strings compare correctly with plain string order.
    """
    last = _utc_date(loc.get("datetimeLast"))
    if last is None:
        return False  # never reported -> skip
    first = _utc_date(loc.get("datetimeFirst")) or "0000-01-01"
    return first <= end and last >= start


def fetch_country_locations(country_id: int, pause: float, start: str, end: str,
                            ignore_coverage: bool = False) -> List[Station]:
    """Page through every OpenAQ location in the country and return the ones
    that have usable coordinates, at least one target-pollutant sensor, and
    (unless ``ignore_coverage``) data coverage overlapping ``[start, end]``.

    The coverage filter is what makes a country run practical: it skips the
    hundreds of dead or long-defunct stations instead of querying each one's
    hourly endpoint only to get nothing back.
    """
    headers = _openaq_headers()
    stations: List[Station] = []
    skipped_coverage = 0
    page = 1
    while True:
        data = http_get_json(
            f"{OPENAQ_BASE}/locations",
            params={"countries_id": country_id, "limit": PAGE_SIZE, "page": page},
            headers=headers,
        )
        time.sleep(pause)
        if not data:
            break
        results = data.get("results", [])
        for loc in results:
            coords = loc.get("coordinates") or {}
            lat, lon = coords.get("latitude"), coords.get("longitude")
            if lat is None or lon is None:
                continue  # cannot fetch weather without coordinates
            if not ignore_coverage and not _coverage_overlaps(loc, start, end):
                skipped_coverage += 1
                continue  # no data in the requested window -> don't query it
            sensors = []
            for sensor in loc.get("sensors", []):
                param = (sensor.get("parameter") or {}).get("name", "").lower()
                if param in POLLUTANT_PARAM_MAP:
                    sensors.append((sensor["id"], POLLUTANT_PARAM_MAP[param]))
            if sensors:
                stations.append(Station(
                    loc_id=loc["id"], name=loc.get("name") or f"loc_{loc['id']}",
                    latitude=float(lat), longitude=float(lon), sensors=sensors))
        logger.info("Locations page %d: %d returned (%d usable so far, %d skipped: no data in window)",
                    page, len(results), len(stations), skipped_coverage)
        if len(results) < PAGE_SIZE:
            break  # last page
        page += 1
    logger.info("Usable stations in %s with data in %s..%s: %d (skipped %d outside window)",
                COUNTRY_ISO, start, end, len(stations), skipped_coverage)
    if not stations and not ignore_coverage:
        logger.warning("No station has data in %s..%s. Try a different date range "
                       "(many live Indian stations report recent data), or pass "
                       "--ignore-coverage to query regardless.", start, end)
    return stations


# --------------------------------------------------------------------------- #
# OpenAQ hourly pollutant series for one sensor
# --------------------------------------------------------------------------- #
def fetch_sensor_hours(sensor_id: int, start: str, end: str,
                       pause: float) -> List[dict]:
    """Paged hourly measurements for one sensor -> [{'timestamp','value'}]."""
    headers = _openaq_headers()
    rows: List[dict] = []
    page = 1
    while True:
        data = http_get_json(
            f"{OPENAQ_BASE}/sensors/{sensor_id}/hours",
            params={"datetime_from": start, "datetime_to": end,
                    "limit": PAGE_SIZE, "page": page},
            headers=headers,
        )
        time.sleep(pause)
        if not data:
            break
        results = data.get("results", [])
        for r in results:
            period = r.get("period", {}) or {}
            dt = (period.get("datetimeFrom") or {}).get("utc")
            value = r.get("value")
            if dt is not None and value is not None:
                rows.append({"timestamp": dt, "value": float(value)})
        if len(results) < PAGE_SIZE:
            break
        page += 1
    return rows


# --------------------------------------------------------------------------- #
# 3) Open-Meteo weather, cached by a rounded coordinate grid
# --------------------------------------------------------------------------- #
class WeatherCache:
    """Fetch-and-memoise hourly weather keyed on rounded coordinates.

    Nearby stations share a grid cell, so we fetch each cell's weather once.
    This is the single biggest reduction in outbound calls for a country run.
    """

    def __init__(self, start: str, end: str, round_dp: int, pause: float):
        self.start, self.end = start, end
        self.round_dp, self.pause = round_dp, pause
        self._cache: Dict[Tuple[float, float], object] = {}

    def get(self, lat: float, lon: float):
        import pandas as pd

        key = (round(lat, self.round_dp), round(lon, self.round_dp))
        if key in self._cache:
            return self._cache[key]

        data = http_get_json(
            WEATHER_ARCHIVE_URL,
            params={
                "latitude": key[0], "longitude": key[1],
                "start_date": self.start, "end_date": self.end,
                "hourly": ",".join(WEATHER_VAR_MAP.keys()),
                "timezone": "UTC",
            },
        )
        time.sleep(self.pause)
        df = None
        hourly = (data or {}).get("hourly", {})
        if hourly and "time" in hourly:
            df = pd.DataFrame(hourly).rename(columns=WEATHER_VAR_MAP)
            df["timestamp"] = pd.to_datetime(df["time"], utc=True).dt.floor("h")
            df = df.drop(columns=["time"])
        self._cache[key] = df  # cache None too, so we don't refetch a dead cell
        return df


# --------------------------------------------------------------------------- #
# Build one station's merged hourly table
# --------------------------------------------------------------------------- #
def build_station_table(station: Station, start: str, end: str,
                        weather: WeatherCache, pause: float):
    """Merge a station's pollutant series with its (cached) weather."""
    import pandas as pd

    long_records: List[dict] = []
    for sensor_id, column in station.sensors:
        for h in fetch_sensor_hours(sensor_id, start, end, pause):
            long_records.append({
                "timestamp": h["timestamp"], "parameter": column,
                "value": h["value"],
            })
    if not long_records:
        return None

    long_df = pd.DataFrame(long_records)
    long_df["timestamp"] = pd.to_datetime(long_df["timestamp"], utc=True).dt.floor("h")
    wide = (
        long_df.groupby(["timestamp", "parameter"])["value"].mean()
        .unstack("parameter").reset_index()
    )
    wide.columns.name = None
    wide.insert(1, "station_id", f"{COUNTRY_ISO}:{station.loc_id}")
    wide.insert(2, "city", station.name)
    wide.insert(3, "country", COUNTRY_ISO)

    wx = weather.get(station.latitude, station.longitude)
    if wx is not None:
        wide = wide.merge(wx, on="timestamp", how="left")
    return wide.sort_values("timestamp").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Parquet write + GCS upload
# --------------------------------------------------------------------------- #
def write_parquet(df, local_dir: str, loc_id: int) -> str:
    os.makedirs(local_dir, exist_ok=True)
    path = os.path.join(local_dir, f"telemetry_{COUNTRY_ISO}_{loc_id}.parquet")
    # Cast every measurement column to float64 so all station files share a
    # consistent schema. Open-Meteo returns some values (e.g. humidity) as whole
    # numbers, which would otherwise be stored as int in some files and float in
    # others, breaking Spark's schema merge on read.
    id_cols = {"timestamp", "station_id", "city", "country"}
    for col in df.columns:
        if col not in id_cols:
            df[col] = df[col].astype("float64")
    df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)
    return path


def parse_gs_uri(uri: str) -> Tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Not a gs:// URI: {uri!r}")
    bucket, _, prefix = uri[len("gs://"):].partition("/")
    return bucket, prefix.strip("/")


def upload_to_gcs(local_path: str, gcs_prefix: str, _client_cache: dict) -> str:
    from google.cloud import storage

    bucket_name, prefix = parse_gs_uri(gcs_prefix)
    blob_path = f"{prefix}/{os.path.basename(local_path)}" if prefix \
        else os.path.basename(local_path)
    client = _client_cache.get("client")
    if client is None:
        client = storage.Client()
        _client_cache["client"] = client
    client.bucket(bucket_name).blob(blob_path).upload_from_filename(local_path)
    return f"gs://{bucket_name}/{blob_path}"


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run(args: argparse.Namespace) -> int:
    stations = fetch_country_locations(
        COUNTRY_ID, args.pause, args.start, args.end, args.ignore_coverage)
    if not stations:
        logger.error("No stations found for %s - aborting.", COUNTRY_ISO)
        return 1
    if args.limit_locations > 0:
        stations = stations[:args.limit_locations]
        logger.info("Limiting to first %d stations (testing).", len(stations))

    weather = WeatherCache(args.start, args.end, args.weather_round, args.pause)
    gcs_clients: dict = {}
    n_ok = n_skip = n_empty = n_fail = 0

    for i, station in enumerate(stations, start=1):
        out_path = os.path.join(
            args.local_dir, f"telemetry_{COUNTRY_ISO}_{station.loc_id}.parquet")
        # Resume: skip stations already collected unless --overwrite.
        if os.path.exists(out_path) and not args.overwrite:
            n_skip += 1
            continue

        logger.info("[%d/%d] station %s (%s)",
                    i, len(stations), station.loc_id, station.name)
        try:
            table = build_station_table(
                station, args.start, args.end, weather, args.pause)
        except Exception as exc:  # noqa: BLE001 - never let one station kill the run
            logger.exception("Station %s failed (%s); skipping.",
                             station.loc_id, exc)
            n_fail += 1
            continue

        if table is None or table.empty:
            n_empty += 1
            continue

        path = write_parquet(table, args.local_dir, station.loc_id)
        n_ok += 1
        if not args.no_upload:
            try:
                upload_to_gcs(path, args.gcs_prefix, gcs_clients)
            except Exception as exc:  # noqa: BLE001 - keep local file, keep going
                logger.error("Upload failed for %s (%s); kept local copy.",
                             path, exc)

        if n_ok % 25 == 0:
            logger.info("Progress: %d written, %d skipped, %d empty, %d failed",
                        n_ok, n_skip, n_empty, n_fail)

    logger.info("DONE. written=%d skipped(resume)=%d empty=%d failed=%d",
                n_ok, n_skip, n_empty, n_fail)
    return 0 if (n_ok > 0 or n_skip > 0) else 1


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Collect India-wide air-quality + weather telemetry as "
                    "Parquet for the MDP Phase 1 pipeline.")
    p.add_argument("--start", required=True, help="Start date, YYYY-MM-DD (UTC).")
    p.add_argument("--end", required=True, help="End date, YYYY-MM-DD (UTC).")
    p.add_argument("--gcs-prefix", default="gs://YOUR_BUCKET/raw/telemetry/",
                   help="Destination gs:// prefix for the Parquet files.")
    p.add_argument("--local-dir", default="./telemetry_out",
                   help="Local directory for Parquet (also the resume checkpoint).")
    p.add_argument("--no-upload", action="store_true",
                   help="Write Parquet locally only; skip the GCS upload.")
    p.add_argument("--overwrite", action="store_true",
                   help="Re-collect stations even if their Parquet already exists.")
    p.add_argument("--limit-locations", type=int, default=0,
                   help="Process only the first N stations (0 = all). For testing.")
    p.add_argument("--ignore-coverage", action="store_true",
                   help="Do not skip stations whose reported data coverage falls "
                        "outside --start/--end (query every station regardless).")
    p.add_argument("--pause", type=float, default=1.1,
                   help="Seconds to sleep between API calls (rate-limit safety).")
    p.add_argument("--weather-round", type=int, default=1,
                   help="Decimal places to round coords for the weather cache "
                        "(1 = ~11km grid; higher = more calls, finer weather).")
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.exit(run(parse_args(sys.argv[1:])))
