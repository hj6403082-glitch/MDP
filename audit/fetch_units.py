"""
Fetch AUTHORITATIVE per-sensor measurement units from OpenAQ v3.

The units problem can be closed without re-downloading any measurements: units are
sensor metadata. This script reads the station ids from the committed filenames
(telemetry_IN_<id>.parquet), queries one OpenAQ location endpoint per station
(~204 calls total), and writes the real unit for every pollutant sensor. Compare
its output to the inferred units in audit/reports/unit_inference.csv to confirm
(or correct) them, and to decide any harmonisation.

Requires an OpenAQ API key (free: https://explore.openaq.org/account):

    export OPENAQ_API_KEY=...
    python audit/fetch_units.py            # writes audit/reports/units_authoritative.csv

This performs only lightweight metadata GETs; it does NOT re-collect measurements.
"""

from __future__ import annotations

import glob
import os
import time

import pandas as pd
import requests

BASE = "https://api.openaq.org/v3"
OUT = "audit/reports/units_authoritative.csv"
PAUSE = 1.1
TARGET_PARAMS = {"co", "no", "no2", "o3", "ozone", "pm10", "pm25", "so2"}


def station_ids():
    ids = []
    for f in glob.glob("data/raw/telemetry/*.parquet"):
        base = os.path.basename(f)                   # telemetry_IN_<id>.parquet
        try:
            ids.append(int(base.replace("telemetry_IN_", "").replace(".parquet", "")))
        except ValueError:
            pass
    return sorted(set(ids))


def get(url, headers, tries=5):
    back = 2.0
    for _ in range(tries):
        try:
            r = requests.get(url, headers=headers, timeout=60)
        except requests.exceptions.RequestException:
            time.sleep(back); back *= 2; continue
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", back))); back *= 2; continue
        if r.status_code >= 500:
            time.sleep(back); back *= 2; continue
        if r.status_code == 404:
            return None
        r.raise_for_status(); return r.json()
    return None


def main() -> int:
    key = os.environ.get("OPENAQ_API_KEY")
    if not key:
        raise SystemExit("Set OPENAQ_API_KEY (https://explore.openaq.org/account).")
    headers = {"X-API-Key": key}
    ids = station_ids()
    print(f"Fetching unit metadata for {len(ids)} stations...")
    rows = []
    for i, sid in enumerate(ids, 1):
        data = get(f"{BASE}/locations/{sid}", headers)
        time.sleep(PAUSE)
        if not data or not data.get("results"):
            rows.append({"station_id": sid, "parameter": None, "unit": None,
                         "note": "location not found / no access"})
            continue
        loc = data["results"][0]
        for s in loc.get("sensors", []):
            par = (s.get("parameter") or {})
            name = (par.get("name") or "").lower()
            if name in TARGET_PARAMS:
                rows.append({"station_id": sid,
                             "parameter": "ozone" if name == "o3" else name,
                             "unit": par.get("units") or s.get("units"),
                             "note": loc.get("name")})
        if i % 25 == 0:
            print(f"  {i}/{len(ids)} stations...")
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"\nWrote {OUT}")
    if not df.empty:
        print("\nUnit by parameter (authoritative):")
        print(df.dropna(subset=["unit"]).groupby(["parameter", "unit"]).size()
              .rename("n_stations").reset_index().to_string(index=False))
        print("\nParameters with MORE THAN ONE unit across stations (true unit mix):")
        mix = df.dropna(subset=["unit"]).groupby("parameter")["unit"].nunique()
        print(mix[mix > 1].to_string() or "  (none — units are consistent per parameter)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
