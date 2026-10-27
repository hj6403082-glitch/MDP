# Units Verification (authoritative)

Source: `audit/reports/units_authoritative.csv` — per-sensor unit metadata fetched from the OpenAQ v3 API with an API key (`audit/fetch_units.py`). This is the authoritative record of what unit each sensor reports, and it supersedes any unit inferred from values.

## Verdict by pollutant

| Pollutant | Unit(s) reported | Stations | Stations with >1 unit | Verdict |
|-----------|------------------|----------|-----------------------|---------|
| CO | ppb; µg/m³ | 198 | 183 | **mixed (per-station duplicate sensors)** |
| NO | ppb | 197 | 0 | **uniform** |
| NO2 | ppb; µg/m³ | 199 | 187 | **mixed (per-station duplicate sensors)** |
| OZONE | ppm; µg/m³ | 191 | 1 | **near-uniform** |
| PM10 | µg/m³ | 194 | 0 | **uniform** |
| PM25 | µg/m³ | 202 | 0 | **uniform** |
| SO2 | ppb; µg/m³ | 191 | 178 | **mixed (per-station duplicate sensors)** |

**Unit-consistent (safe for quantitative cross-station use):** NO, OZONE, PM10, PM25.
**Unit-indeterminate (duplicate ppb + ug/m3 sensors per station):** CO, NO2, SO2.

## What this means

- `ppb` is a mixing ratio; `ug/m3` is a mass concentration. They are not comparable without converting via molecular weight and ambient temperature/pressure.
- For CO, NO2 and SO2, almost every station carries BOTH a ppb and a ug/m3 sensor. The stored dataset keeps a single value per pollutant per station-hour with no record of which sensor produced it, so the unit of any given CO/NO2/SO2 value is **indeterminate** and cannot be recovered or harmonized from the stored data alone.
- This **corrects an earlier value-based inference** that CO was uniform: the authoritative metadata shows CO is mixed. The authoritative source governs.

## Impact on the analyses (what survives)

- **Ozone prediction** — the target is ug/m3 at all but one sensor, so the leakage-safe R2 result is unaffected.
- **NO -> ozone** — NO is ppb at every station (unit-consistent), so the one stable association rests on a clean variable.
- **PM2.5 / PM10** — uniform ug/m3.
- **CO, NO2, SO2 as features** — unit-indeterminate; cross-station quantitative use is unreliable and should be dropped or explicitly caveated. Within-station temporal structure may still hold if a station used one sensor consistently, but this cannot be verified from the data.

## Fix

Re-collect retaining per-sensor unit (and sensor id) so each value's unit is known; convert ppb to ug/m3 per species before pooling. `data_collection.py` now captures per-sensor units for this reason.
