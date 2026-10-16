# MDP — Causal AI for Air Pollution

A multi-disciplinary causal-AI and optimization pipeline built for **Google
Cloud Dataproc (Apache Spark)**. See `CLAUDE.md` for the architecture.

## Pipeline phases

| Phase | Purpose | Key tech |
|-------|---------|----------|
| **1** | Data ingestion & K-means clustering to objectively group chemical species | PySpark MLlib |
| 2 | Predictive baseline + causal discovery of atmospheric regimes | `xgboost.spark`, `lingam` (DirectLiNGAM) |
| 3 | Multi-objective optimization (minimise PM2.5 **and** Ozone) | `optuna` (NSGA-II, SQLite backend) |

## Phase 1 — how it works

Phase 1 groups chemical *species* by how they co-vary across the whole
telemetry dataset:

1. **Ingest** the raw telemetry with Spark (Parquet preferred; CSV supported).
2. **Quality-filter** species by non-null coverage (one distributed pass).
3. **Build feature vectors**: compute the full inter-species correlation
   matrix with Spark MLlib (distributed across the cluster). Each species'
   row of that matrix becomes its feature vector. Only the tiny
   `n_species × n_species` matrix ever reaches the driver.
4. **K-means** with silhouette-based selection of `k`.
5. **Write** species→cluster assignments, the correlation matrix, and metrics
   back to the output store (GCS on Dataproc).

The heavy, data-parallel work stays in Spark; the driver only ever holds a
kilobyte-scale matrix — the memory discipline required by `CLAUDE.md`.

## Phase 2 — predictive baseline & causal discovery

**2a — Predictive baseline** (`src/phases/phase2_predictive.py`)
Trains `xgboost.spark.SparkXGBRegressor` **distributed** across the Spark
workers (one XGBoost worker per Spark task, `num_workers` auto-detected from
cluster parallelism) to predict a secondary pollutant (default: Ozone) from the
other species. Null predictors flow through as XGBoost-native missing values;
only rows with a null *target* are dropped. Reports RMSE / MAE / R² on a
held-out split and saves the model + metrics. Feature data is never collected
to the driver.

**2b — Causal discovery** (`src/phases/phase2_causal.py`)
Runs `lingam.DirectLiNGAM` to recover the causal **DAG** and the linear
**structural-equation models (SEMs)** linking primary pollutants (NO, NO₂, CO,
SO₂, VOCs) to secondary pollutants (Ozone, PM2.5). DirectLiNGAM is single-node,
so Spark does the column-pruning, mean-imputation and a **bounded random
sample** first; only that capped sample (default ≤ 50k rows) ever reaches the
driver, keeping its footprint constant regardless of source size. Prior
knowledge forbids physically impossible *secondary → primary* edges. Outputs
the edge list and per-variable SEM equations in causal order.

Run on Dataproc:

```bash
spark-submit --py-files config,src src/phases/phase2_predictive.py
spark-submit --py-files config,src src/phases/phase2_causal.py
```

Key Phase 2 overrides: `MDP_TARGET_COLUMN`, `MDP_XGB_NUM_WORKERS`,
`MDP_PRIMARY_POLLUTANTS`, `MDP_SECONDARY_POLLUTANTS`, `MDP_LINGAM_MAX_ROWS`,
`MDP_LINGAM_PRIOR`, `MDP_LINGAM_EDGE_THRESHOLD`.

## Phase 3 — policy optimization & explainability

**3a — Multi-objective optimization** (`src/phases/phase3_optimization.py`)
Uses Optuna's **`NSGAIISampler`** to **minimise PM2.5 and Ozone
simultaneously**, searching over emission-reduction interventions on the
primary pollutants. Each candidate is scored by applying it as a causal
*do*-operation on the Phase 2b SEM (fix the primaries, sever incoming edges,
propagate through the recovered causal order) and reading off the resulting
Ozone and PM2.5 — so the sign-sensitive ozone chemistry makes this a real
Pareto trade-off, not "reduce everything to zero".

The study lives in a **relational database** (`storage='sqlite:///db.sqlite3'`
by default). Every Spark worker calls `optuna.load_study(...)` against that
shared storage and runs its share of trials, so trials are evaluated **in
parallel across the cluster** with the RDBMS as the coordination point. Each
per-trial evaluation is pure NumPy over a tiny broadcast matrix — no big data
is shuffled and the driver only reads the final Pareto front back. Point
`MDP_OPTUNA_STORAGE` at Cloud SQL (MySQL/Postgres) for high parallelism.

**3b — Explainability (XAI)** (`src/phases/phase3_xai.py`)
Integrates **SHAP** (`TreeExplainer`) against the Phase 2a XGBoost baseline to
extract per-feature importance and render a **summary (beeswarm) plot** showing
the magnitude and direction of each chemical species' effect. SHAP is
single-node, so Spark bound-samples the feature rows (default ≤ 5k) before only
that capped sample reaches the driver. Outputs the plot plus a
mean(|SHAP|) importance table.

Run on Dataproc:

```bash
spark-submit --py-files config,src src/phases/phase3_optimization.py
spark-submit --py-files config,src src/phases/phase3_xai.py
```

Key Phase 3 overrides: `MDP_OPTUNA_STORAGE`, `MDP_OPTUNA_STUDY`,
`MDP_OPTUNA_TRIALS`, `MDP_OPTUNA_WORKERS`, `MDP_OPTUNA_OBJECTIVES`,
`MDP_INTERVENTION_LOW`/`_HIGH`, `MDP_SHAP_MAX_ROWS`, `MDP_SHAP_PLOT_PATH`.

## Running

Configuration is environment-driven (see `config/pipeline_config.py`). On
Dataproc:

```bash
spark-submit --py-files config,src src/phases/phase1_clustering.py
```

Key environment overrides: `MDP_INPUT_PATH`, `MDP_INPUT_FORMAT`,
`MDP_SPECIES_COLUMNS`, `MDP_OUTPUT_PATH`, `MDP_K_CANDIDATES`, `MDP_FIXED_K`.

## Layout

```
config/pipeline_config.py        # all tunables (12-factor, env-overridable)
src/spark_utils.py               # shared SparkSession builder
src/phases/phase1_clustering.py  # Phase 1: ingestion + K-means
src/phases/phase2_predictive.py  # Phase 2a: distributed XGBoost baseline
src/phases/phase2_causal.py      # Phase 2b: DirectLiNGAM causal discovery
src/phases/phase3_optimization.py# Phase 3a: Optuna NSGA-II (SQLite-backed)
src/phases/phase3_xai.py         # Phase 3b: SHAP explainability
```
