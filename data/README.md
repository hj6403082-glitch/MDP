# Data

## `raw/telemetry/` — collected air-quality + weather telemetry

204 Parquet files, one per Indian monitoring station (OpenAQ v3), each merged
with co-located hourly Open-Meteo weather for 2025 (~1.18M station-hours total).
Produced by `data_collection.py` (see repo root `README.md`).

**Schema** (per file): `timestamp`, `station_id`, `city`, `country`, the
pollutant columns present at that station (`co, no, no2, ozone, pm10, pm25,
so2`), and weather (`temperature, relative_humidity, wind_speed, pressure`).
All measurement columns are `float64` (normalised for consistent Spark schema
merging; see `scripts/normalize_telemetry.py`).

This directory is what `MDP_INPUT_PATH` points at — Phase 1 reads it directly.
Regenerate / extend with:

    python data_collection.py --start 2025-01-01 --end 2025-12-31 --no-upload
