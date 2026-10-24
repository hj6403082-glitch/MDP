# Pseudocode — MDP Air-Quality ML Pipeline

Algorithm-level pseudocode for every stage. Each block mirrors the actual code
(`data_collection.py`, `src/phases/`, `audit/`) but is written to be read and
defended in a review, not executed. Notation: `D` = dataset (rows = station-hours,
columns = pollutants + weather), `S` = set of stations, `μ,σ` = per-column
train-fold mean/std.

---

## Algorithm 0 — Data Collection (`data_collection.py`)

```
INPUT:  country = India, year = 2025, pollutants P = {CO,NO,NO2,O3,PM10,PM25,SO2}
OUTPUT: one Parquet file per station in data/raw/telemetry/

for each station s in OpenAQ(country, has_data_in=year):          # v3 API
    sensors  <- GET /locations/{s}/sensors                        # capture units!
    meas     <- GET /measurements for each sensor, hourly, year
    weather  <- Open-Meteo reanalysis at nearest 0.1 deg grid cell of s
                 for {temperature, relative_humidity, wind_speed, pressure}
    table    <- OUTER-JOIN(meas, weather) ON timestamp (hourly)
    write Parquet(table) with station_id, lat, lon, units-manifest
end
merge per-station files -> 204 files, ~1.18M station-hours
```

Design note: units are stored per sensor so that comparability can be *verified*
later (the original collection discarded them — a defect the audit fixed).

---

## Algorithm 1 — Phase 1: Species Grouping by K-means (`phase1_clustering.py`)

```
INPUT:  D, species columns C, k (default 3)
OUTPUT: cluster label per species + silhouette score

# features are per-species correlation PROFILES, not raw concentrations
R <- pairwise_correlation_matrix(D[C])          # |C| x |C|
X <- rows of R                                   # each species -> vector of its
                                                 # correlations with all others
for k' in candidate range:                       # model-selection
    model   <- KMeans(k=k', seed=42).fit(X)
    score   <- silhouette(X, model.labels)
choose k with best silhouette
RETURN model.labels, score
```

Why correlation profiles: species that co-vary with the *same* other species are
grouped, which is the closest K-means can get to "behaves like a common source".

---

## Algorithm 2 — Phase 2a: Predictive Baseline (`phase2_causal.py`, XGBoost)

```
INPUT:  D, target y = ozone, features F = other pollutants + weather
OUTPUT: fitted model + HONEST held-out skill

# --- leakage-safe splitting (the core correctness fix) ---
TRAIN, TEST <- blocked_temporal_split(D, train = months 1..9, test = 10..12)
           OR  leave_stations_out(D, S)           # unseen-station generalisation

mu, sigma   <- mean,std of F over TRAIN only      # fit preprocessing on train only
TRAIN, TEST <- standardize(F, mu, sigma)

model <- XGBoostRegressor(n_estimators=250, max_depth=6, lr=0.05,
                          subsample=0.8, tree_method=hist, seed=42)   # fixed a priori
model.fit(TRAIN[F], TRAIN[y])

R2 <- r2_score(TEST[y], model.predict(TEST[F]))
# baselines for honest comparison
R2_persist  <- r2(TEST[y], previous_hour_value)
R2_clim     <- r2(TEST[y], per_station_mean(TRAIN))
CI          <- station_block_bootstrap(R2)        # uncertainty
RETURN model, R2, R2_persist, R2_clim, CI
```

The *a priori* hyper-parameters and train-only preprocessing are what make the
reported R² trustworthy; tuning on TEST would re-introduce leakage.

---

## Algorithm 3 — Phase 2b: Causal Structure Discovery (DirectLiNGAM)

```
INPUT:  standardized pollutants Z, prior K (forbid secondary -> primary edges)
OUTPUT: adjacency matrix + per-edge bootstrap stability

model <- DirectLiNGAM(prior_knowledge = K).fit(Z)
A     <- model.adjacency_matrix                   # weighted DAG among species
persist manifest{columns, mu, sigma, A, threshold, seed, versions}

# stability + confounding check (the part that makes it defensible)
for b in 1..B:                                     # station-block bootstrap
    Z_b   <- resample stations with replacement
    A_b   <- DirectLiNGAM(K).fit(Z_b).adjacency
    tally edge frequencies and sign
re-fit WITH weather nodes {temp,RH,wind,pressure} as exogenous
RETURN edges with frequency, mean weight, and weather-sensitivity flag
```

An edge is reported only if it is bootstrap-stable **and** survives the inclusion
of meteorology (otherwise it was confounded).

---

## Algorithm 4 — Phase 3a: Multi-Objective Policy Search (Optuna NSGA-II)

```
INPUT:  response model f (ozone, PM2.5 vs standardized concentration levers x)
OUTPUT: Pareto set of trade-off policies

study <- Optuna.create_study(directions=[minimize,minimize],
                             sampler = NSGAIISampler(seed=42))   # NOT the TPE default
for trial in 1..N:
    x       <- trial.suggest levers over supported variables only   # reject VOC etc.
    (o, pm) <- f.evaluate(x)                       # raise if x uses an unfitted var
    report (o, pm)
RETURN study.best_trials                            # non-dominated front
```

Guard (audit fix): decision variables are intersected with the *fitted* graph;
asking to move a variable the model never learned raises, instead of silently
returning a meaningless "optimum".

## Algorithm 4' — Exact frontier (audit check, `analytic_pareto.py`)

```
# because f is LINEAR, the true Pareto front is closed-form
front <- { x on the boundary of the feasible box minimizing lambda*o+(1-lambda)*pm
           for lambda in [0,1] }
for each saved metaheuristic policy p:
    assert exists q in front with q dominates p     # all 19 were dominated
```

---

## Algorithm 5 — Phase 3b: Explanation (SHAP)

```
INPUT:  fitted XGBoost model, background sample B
OUTPUT: per-feature attributions

explainer <- TreeSHAP(model)
phi       <- explainer.shap_values(B)               # exact for trees
rank features by mean(|phi|); inspect NO contribution to ozone
```

SHAP agreeing with DirectLiNGAM on the NO sign is **internal consistency** of two
models on the same data — reported as such, not as independent validation.
