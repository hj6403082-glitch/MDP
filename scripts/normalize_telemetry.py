"""
Normalize per-station telemetry Parquet files to a consistent schema.

Why this exists
---------------
Open-Meteo sometimes returns whole-number values (e.g. relative humidity of
80 instead of 80.0), so pandas stored that column as an integer (BIGINT) in some
station files and as a float (DOUBLE) in others. When Spark reads the whole
directory with schema merging, it fails:

    [CANNOT_MERGE_INCOMPATIBLE_DATA_TYPE] Failed to merge incompatible data
    types "BIGINT" and "DOUBLE"

This script rewrites every telemetry Parquet file, casting all non-identifier
columns to float64. Afterwards every file shares a consistent numeric type, so
Spark can union the (still differing) column sets across stations without error.
It is idempotent - safe to run repeatedly.

Usage:
    python scripts/normalize_telemetry.py [telemetry_dir]   # default: telemetry_out
"""

from __future__ import annotations

import glob
import os
import sys

import pandas as pd

# Columns that stay as-is (timestamp + string identifiers); everything else is
# a measurement and becomes float64.
ID_COLUMNS = {"timestamp", "station_id", "city", "country"}


def normalize_dir(directory: str) -> int:
    files = sorted(glob.glob(os.path.join(directory, "*.parquet")))
    if not files:
        print(f"No .parquet files found in {directory!r}.")
        return 1

    changed = 0
    for path in files:
        df = pd.read_parquet(path)
        touched = False
        for col in df.columns:
            if col in ID_COLUMNS:
                continue
            # Coerce to numeric (non-numeric -> NaN) then to a uniform float64.
            new = pd.to_numeric(df[col], errors="coerce").astype("float64")
            if str(df[col].dtype) != "float64":
                touched = True
            df[col] = new
        if touched:
            changed += 1
        df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)

    print(f"Normalized {len(files)} files in {directory!r} "
          f"({changed} had a column re-typed to float64).")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "telemetry_out"
    sys.exit(normalize_dir(target))
