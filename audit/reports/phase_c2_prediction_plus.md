# Phase C2 - Stronger Predictive Modelling

Blocked temporal split; train 738,778 rows, test 343,153 rows, 190 stations.

## 1. Contemporaneous: what weather vs pollutants explain

- **weather only** - R2=0.14, RMSE=28.38 (n=343,153) 
- **pollutants only** - R2=0.131, RMSE=28.53 (n=343,153) 
- **weather + pollutants** - R2=0.257, RMSE=26.39 (n=343,153) 
- **+ time harmonics** - R2=0.337, RMSE=24.92 (n=343,153) 
- **+ station mean (train-only)** - R2=0.413, RMSE=23.44 (n=343,153) [station memorisation - helps gap-filling, NOT unsensored sites]

> Incremental value of pollutants *beyond weather* is the honest signal; the station-mean gain is site memorisation and does not transfer to stations without an ozone sensor.

## 2. Forecasting ozone at t+1h (vs persistence)

- **persistence (y(t+1)=y(t))** - R2=0.812, RMSE=13.25 (n=334,791)
- **xgboost (pollutants+weather+time+lags)** - R2=0.865, RMSE=11.22 (n=334,791)

## Interpretation

- Weather alone explains R2=0.14 of ozone; adding pollutants raises it by **+0.117** - the genuine incremental pollutant signal (small).
- Time harmonics add a little; the station-mean 'gain' is memorisation that does not generalise to unsensored sites.
- For 1-hour-ahead forecasting, persistence gives R2=0.812; the model gives R2=0.865 (beats persistence by +0.053).
- None of this is causal evidence.
