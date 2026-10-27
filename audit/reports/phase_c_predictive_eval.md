# Phase C — Leakage-Safe Predictive Evaluation

Target: **ozone** (contemporaneous estimation). Predictors: co, no, no2, pm10, pm25, so2, temperature, relative_humidity, wind_speed, pressure. Rows: **1,081,931**; stations: **190**.

XGBoost hyper-parameters fixed a priori (no tuning on any test set): `{'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.05, 'subsample': 0.8, 'colsample_bytree': 0.8, 'tree_method': 'hist', 'n_jobs': -1, 'random_state': 42}`.

## 0. Leaky random 80/20 split (the original design)

- **random-split(LEAKY) / xgboost** — R²=0.412, RMSE=23.72, MAE=14.90 (n=216,688) 
- **random-split(LEAKY) / global-mean** — R²=-0.000, RMSE=30.93, MAE=20.62 (n=216,688) 

> Rows from the same station/time sit in both train and test, so this number is optimistic and is reported only as the baseline to beat.

## 1. Blocked temporal holdout (train months 1–9, test 10–12)

- **blocked-temporal / xgboost** — R²=0.251, RMSE=26.49, MAE=16.19 (n=343,153) [90% CI R² 0.221–0.280]
- **blocked-temporal / global-mean** — R²=-0.010, RMSE=30.76, MAE=21.27 (n=343,153) 
- **blocked-temporal / per-station-climatology** — R²=0.041, RMSE=29.98, MAE=20.04 (n=343,153) 
- **blocked-temporal / persistence(prev-hour)** — R²=0.794, RMSE=13.88, MAE=5.57 (n=342,969) 

### 1b. Feature ablations (blocked temporal)

- **ablation-temporal / weather-only** — R²=0.140, RMSE=28.38, MAE=17.92 (n=343,153) 
- **ablation-temporal / pollutants-only** — R²=0.132, RMSE=28.51, MAE=19.08 (n=343,153) 
- **ablation-temporal / all-features** — R²=0.251, RMSE=26.49, MAE=16.19 (n=343,153) 

### 1c. Test-period performance by month

- month 10: R²=0.307, RMSE=26.56 (n=115,308)
- month 11: R²=0.231, RMSE=28.73 (n=113,916)
- month 12: R²=0.193, RMSE=23.99 (n=113,929)

## 2. Leave-stations-out (80% stations train, 20% unseen test)

- **leave-stations-out / xgboost** — R²=0.304, RMSE=27.94, MAE=18.45 (n=234,716) [90% CI R² 0.188–0.395]
- **leave-stations-out / global-mean** — R²=-0.001, RMSE=33.51, MAE=21.67 (n=234,716) 

## 3. Strictest: later months AND unseen stations

- **temporal x spatial / xgboost** — R²=0.219, RMSE=30.00, MAE=18.41 (n=70,275) 
- **temporal x spatial / global-mean** — R²=-0.006, RMSE=34.06, MAE=22.16 (n=70,275) 

## Interpretation

- **Leakage inflates skill.** The leaky random split (R²≈0.41, close to the originally-reported 0.43) drops to **R²≈0.25 (blocked temporal)** and **R²≈0.30 (unseen stations)** under honest held-out evaluation. The original headline number was optimistic by ~0.15 R².
- **A naive temporal baseline wins for gap-filling.** Previous-hour persistence attains R²≈0.79 — far above the model — because ozone is strongly autocorrelated. BUT persistence requires a recent ozone reading at the same station, so it only applies to *temporal gap-filling*, not to estimating ozone where/when no ozone sensor exists.
- **The model's honest contribution is spatial.** For the leave-stations-out task (estimating ozone at unsensored stations) the only valid naive baseline is the global/mean predictor (R²≈0); the model reaches R²≈0.30, a modest but real gain. It does **not** beat persistence for gap-filling.
- **Weather and pollutants contribute roughly equally and complementarily** (ablation R² 0.14 / 0.13 individually, 0.25 together).
- Neither predictive accuracy nor feature importance is causal evidence; units are unharmonised (CO), so cross-station magnitudes carry measurement error not modelled here.
