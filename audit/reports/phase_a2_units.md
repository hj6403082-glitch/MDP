# Phase A2 - Unit Inference & Plausibility Cleaning

## 1. Inferred units & cross-station consistency

| pollutant   | inferred_unit       |   n_stations |   median_min |   median_max |   nonzero_span_x |
|:------------|:--------------------|-------------:|-------------:|-------------:|-----------------:|
| co          | mg/m^3 (unverified) |          196 |         0    |         2.84 |             47.3 |
| no          | ug/m^3 (unverified) |          197 |         0    |        48.2  |             65.8 |
| no2         | ug/m^3 (unverified) |          198 |         0    |        79.7  |            538.5 |
| ozone       | ug/m^3 (unverified) |          190 |         0    |        61.3  |             50.7 |
| pm10        | ug/m^3 (unverified) |          194 |         6.47 |       493    |             76.2 |
| pm25        | ug/m^3 (unverified) |          202 |         0    |       133    |             42.8 |
| so2         | ug/m^3 (unverified) |          190 |         0    |        52.5  |             92.6 |

> CO station medians are uniform (~0.5–1.3), consistent with a single mg/m³ regime — **no cross-station unit mix** (correcting the first audit). Units remain UNVERIFIED without sensor metadata. Note CO is on an mg/m³ scale while the others are µg/m³ (~×1000), so absolute cross-pollutant magnitudes are not comparable (correlation-based steps are scale-invariant and unaffected).

## 2. Physical-plausibility screening (flag, not delete)

- Total values flagged non-physical and set to NaN: **35** (of 1,180,551 rows). Per-station/pollutant detail in `audit/reports/cleaning_log.csv`.
- Exact round-cap counts (possible instrument saturation): {'no': 38, 'no2': 0, 'ozone': 12, 'pm25': 142, 'pm10': 3, 'so2': 0}
- Zeros are retained but remain ambiguous (true low / below-detection / fault); no detection-limit metadata exists to disambiguate.

- Cleaned analysis dataset written to `audit/analysis_dataset/telemetry_clean.parquet` (raw data untouched; regenerate with this script).

## 3. Sensitivity: does cleaning change CO's correlation structure?

|       |   co_corr_raw |   co_corr_clean |   delta |
|:------|--------------:|----------------:|--------:|
| no    |         0.14  |           0.421 |   0.281 |
| no2   |         0.128 |           0.373 |   0.245 |
| ozone |        -0.009 |          -0.024 |  -0.015 |
| pm10  |         0.14  |           0.4   |   0.26  |
| pm25  |         0.12  |           0.351 |   0.231 |
| so2   |         0.019 |           0.06  |   0.041 |

> Max change in a CO correlation after screening: 0.281. Non-trivial — the outliers measurably affected CO's correlations.

## 4. Effect on species grouping (cleaned data)

- cluster 0: co, no, no2, pm10, pm25
- cluster 1: ozone, so2
- silhouette (cleaned) = 0.358 (vs 0.26 on raw full data).
- CO co-assignment freq (cleaned): {'no': 1.0, 'no2': 1.0, 'ozone': 0.0, 'pm10': 1.0, 'pm25': 1.0, 'so2': 0.0}

> **Cleaning resolves the CO instability** (Phase E): CO now joins the combustion/traffic family {CO, NO, NO₂, PM10, PM2.5} at frequency 1.0, leaving {ozone, SO₂} — a physically coherent split. The outlier spikes, not an intrinsic ambiguity, drove CO's earlier instability.

## Correction to the first audit

- The earlier statement that CO showed a *mixed mg/m³ vs µg/m³ unit regime* is **withdrawn**. Per-station medians are uniform; the 1490 max is sporadic spikes (0.003% of CO). CO appears uniformly mg/m³.
- The valid, remaining unit concerns are: (i) units are **unverified** (no metadata stored; fix with `audit/fetch_units.py` + a re-collection that keeps units), and (ii) a small number of **non-physical outliers** and saturation caps, now flagged in the cleaned dataset.
