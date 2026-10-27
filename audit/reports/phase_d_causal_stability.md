# Phase D - DirectLiNGAM Stability & Sensitivity

Pollutant-only model on 968,551 complete-case rows (columns ['no', 'no2', 'co', 'so2', 'ozone', 'pm25']).

### Point estimate (full data, with prior knowledge)
- recovered order: no -> no2 -> so2 -> co -> ozone -> pm25
  - no -> no2: +0.396
  - no2 -> pm25: +0.289
  - no -> pm25: +0.156
  - no -> ozone: -0.129
  - no -> co: +0.092
  - no2 -> co: +0.085
  - co -> pm25: +0.061
  - so2 -> ozone: +0.052
  - no2 -> so2: +0.051

## 1. Bootstrap stability (pollutant model)

| source   | target   |   edge_freq |   coef_mean |   coef_sd |
|:---------|:---------|------------:|------------:|----------:|
| no       | no2      |       1     |       0.396 |     0.011 |
| no       | ozone    |       1     |      -0.138 |     0.007 |
| no2      | pm25     |       1     |       0.231 |     0.025 |
| no       | pm25     |       1     |       0.097 |     0.024 |
| no       | co       |       0.912 |       0.264 |     0.08  |
| no2      | co       |       0.912 |       0.25  |     0.075 |
| co       | pm25     |       0.912 |       0.226 |     0.073 |
| so2      | ozone    |       0.512 |       0.051 |     0.009 |
| no2      | so2      |       0.425 |       0.046 |     0.012 |
| no       | so2      |       0.312 |       0.043 |     0.017 |

> `edge_freq` = fraction of bootstraps where |coef| >= 0.05. Edges with low frequency or sign-unstable coefficients should not be read as mechanisms.

## 2. Prior-knowledge sensitivity

### Without the secondary->primary ban
- recovered order: no -> ozone -> no2 -> pm25 -> co -> so2
  - no -> no2: +0.396
  - no2 -> pm25: +0.295
  - no -> pm25: +0.164
  - no -> ozone: -0.124
  - no -> co: +0.081
  - pm25 -> co: +0.070
  - no2 -> co: +0.064
  - ozone -> so2: +0.052
  - no -> so2: +0.052

## 3. Confounder sensitivity: add modelled meteorology as exogenous

### With weather included (962,566 rows)
- recovered order: pressure -> wind_speed -> relative_humidity -> temperature -> no -> no2 -> so2 -> co -> ozone -> pm25
  - temperature -> pm25: -0.363
  - no -> no2: +0.337
  - relative_humidity -> ozone: -0.314
  - relative_humidity -> no2: -0.245
  - relative_humidity -> pm25: -0.198
  - no2 -> pm25: +0.193
  - temperature -> no2: -0.192
  - temperature -> no: -0.189
  - pressure -> pm25: +0.165
  - temperature -> ozone: +0.123
  - relative_humidity -> no: -0.119
  - pressure -> no: +0.118
  - no -> pm25: +0.108
  - no -> ozone: -0.108
  - wind_speed -> no: -0.095
  - wind_speed -> no2: -0.095
  - relative_humidity -> so2: -0.089
  - pressure -> no2: +0.087
  - no -> co: +0.085
  - wind_speed -> pm25: -0.085
  - no2 -> co: +0.071
  - no2 -> ozone: -0.053

> NO->ozone coefficient with weather included: **-0.108** (pollutant-only point estimate was -0.129). Change under confounder inclusion indicates the pooled contemporaneous estimate is sensitive to omitted meteorology.

## Interpretation

- The graph is a **hypothesis generator**, not an identified causal model. Edges that are bootstrap-stable AND survive meteorology inclusion are the only ones worth discussing, and only as associational structure under DirectLiNGAM's (strong) linearity, non-Gaussianity, acyclicity and no-hidden-confounding assumptions.
- Pooling across stations, seasons and hours ignores spatial/temporal dependence and regime switching (e.g. VOC- vs NOx-limited ozone), so coefficients are population-averaged associations, not local mechanisms.
