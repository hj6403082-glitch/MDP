# Phase E - Exploratory Species Grouping: Stability

Species: ['co', 'no', 'no2', 'ozone', 'pm10', 'pm25', 'so2']. Rows: 1,180,551.

## Silhouette by k (point estimate)

- k=2: silhouette=0.259
- k=3: silhouette=0.218
- k=4: silhouette=0.198
- k=5: silhouette=0.216
- k=6: silhouette=0.173

Selected k=2 (silhouette 0.259). Groups:
  - cluster 0: no, no2, pm10, pm25
  - cluster 1: co, ozone, so2

## Bootstrap co-assignment stability (k=2)

Co-assignment frequency (fraction of bootstraps two species share a cluster):

|       |   co |   no |   no2 |   ozone |   pm10 |   pm25 |   so2 |
|:------|-----:|-----:|------:|--------:|-------:|-------:|------:|
| co    | 1    | 0.28 |  0.28 |    0.72 |   0.28 |   0.28 |  0.72 |
| no    | 0.28 | 1    |  1    |    0    |   1    |   1    |  0    |
| no2   | 0.28 | 1    |  1    |    0    |   1    |   1    |  0    |
| ozone | 0.72 | 0    |  0    |    1    |   0    |   0    |  1    |
| pm10  | 0.28 | 1    |  1    |    0    |   1    |   1    |  0    |
| pm25  | 0.28 | 1    |  1    |    0    |   1    |   1    |  0    |
| so2   | 0.72 | 0    |  0    |    1    |   0    |   0    |  1    |

- Bootstrap silhouette (k=2): mean 0.269, 5-95% [0.247, 0.305].
- Pairs near 1.0 are robustly grouped; pairs near 0.5 are unstable (cluster membership flips across resamples).

## Interpretation

- Silhouette is **0.26 here** (0.39 in the pipeline's mean-imputed Spark run); both indicate **weak** separation. The species do not fall into cleanly separated groups - the split is a convenience partition of a largely continuous correlation structure, and the exact silhouette/grouping depends on imputation and correlation details.
- **Only a core is stable:** {NO, NO2, PM10, PM2.5} and {ozone, SO2} each co-assign at 1.0. **CO is unstable** (co-assigns 0.72 with ozone/SO2, 0.28 with the traffic family) and the pipeline's reported grouping placed it differently again. CO's instability is consistent with its unresolved unit problem (mixed mg/m3 vs ug/m3), which corrupts its correlations.
- This is an **exploratory grouping of co-varying species**, driven by shared sources AND shared meteorological modulation. It is NOT source apportionment and assigns no quantitative source contributions.
