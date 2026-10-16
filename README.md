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
config/pipeline_config.py      # all tunables (12-factor, env-overridable)
src/spark_utils.py             # shared SparkSession builder
src/phases/phase1_clustering.py# Phase 1 implementation
```
