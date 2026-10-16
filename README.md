# MDP — Causal AI for Air Pollution

A multi-disciplinary **causal-AI and optimization pipeline** for air-quality
telemetry, built to run distributed on **Google Cloud Dataproc (Apache
Spark)**. It objectively groups chemical species, learns a predictive baseline,
discovers the causal structure linking primary and secondary pollutants, and
then searches for emission-reduction policies that minimise PM2.5 and Ozone
together. See [`CLAUDE.md`](CLAUDE.md) for the architectural brief.

## Pipeline phases

| Phase | Purpose | Key tech |
|-------|---------|----------|
| **1** | Data ingestion & K-means clustering to objectively group chemical species | PySpark MLlib |
| **2a** | Distributed predictive baseline for a secondary pollutant | `xgboost.spark.SparkXGBRegressor` |
| **2b** | Causal discovery of the pollutant DAG + structural equations | `lingam.DirectLiNGAM` |
| **3a** | Multi-objective policy optimization (minimise PM2.5 **and** Ozone) | `optuna` `NSGAIISampler` (relational-DB backend) |
| **3b** | Explainability of the baseline (feature drivers) | `shap` |

Every phase keeps the heavy, data-parallel work in Spark and pulls only tiny,
bounded summaries to the driver — the memory discipline required by `CLAUDE.md`.

## Quickstart — run the whole pipeline with one `spark-submit`

[`main.py`](main.py) chains all phases in dependency order inside a **single
Spark application** (one shared `SparkSession`).

```bash
# 1) Package the importable modules for Spark's executors.
zip -r mdp_modules.zip src config

# 2) Submit the driver. Phase 3 reads Phase 2's artefacts, so order matters —
#    the driver enforces it.
spark-submit --py-files mdp_modules.zip main.py --phases all
```

On Dataproc the files typically live in GCS:

```bash
gcloud dataproc jobs submit pyspark gs://<bucket>/main.py \
  --cluster=<cluster> --region=<region> \
  --py-files=gs://<bucket>/mdp_modules.zip
```

Run a subset of phases (canonical order is always enforced), and optionally keep
going if one fails:

```bash
spark-submit --py-files mdp_modules.zip main.py --phases phase1 phase2a phase2b
spark-submit --py-files mdp_modules.zip main.py --phases all --continue-on-error
```

Valid `--phases` values: `phase1 phase2a phase2b phase3a phase3b` or `all`
(default). The driver prints a JSON run-summary to stdout and exits non-zero if
any phase failed, so it drops cleanly into CI or an orchestrator.

## Requirements

Python 3.10/3.11 (matching recent Dataproc images). Install with:

```bash
pip install -r requirements.txt
```

Core dependencies: `pyspark`, `xgboost`, `lingam`, `optuna`, `shap`,
`matplotlib`, `numpy`, `pandas`, `pyarrow`, `scikit-learn`. All versions are
pinned in [`requirements.txt`](requirements.txt). For a cluster, install them at
creation time (see the header of that file).

## Configuration

Configuration is fully **environment-driven** (12-factor) and centralised in
[`config/pipeline_config.py`](config/pipeline_config.py) — no code edits are
needed to move between local, CI and Dataproc. Common overrides:

| Scope | Variable | Meaning |
|-------|----------|---------|
| I/O | `MDP_INPUT_PATH`, `MDP_INPUT_FORMAT` | Telemetry location (`gs://…`) and `parquet`/`csv` |
| I/O | `MDP_OUTPUT_PATH` | Root for all written artefacts (`gs://…`) |
| I/O | `MDP_ID_COLUMNS`, `MDP_SPECIES_COLUMNS` | Non-feature id columns; explicit species list |
| Phase 1 | `MDP_K_CANDIDATES`, `MDP_FIXED_K` | K sweep, or a fixed `k` |
| Phase 2a | `MDP_TARGET_COLUMN`, `MDP_XGB_NUM_WORKERS` | Regression target; XGBoost worker count (0 = auto) |
| Phase 2b | `MDP_PRIMARY_POLLUTANTS`, `MDP_SECONDARY_POLLUTANTS` | Causes vs. effects |
| Phase 2b | `MDP_LINGAM_MAX_ROWS`, `MDP_LINGAM_PRIOR`, `MDP_LINGAM_EDGE_THRESHOLD` | Driver sample cap; prior knowledge; edge pruning |
| Phase 3a | `MDP_OPTUNA_STORAGE`, `MDP_OPTUNA_STUDY` | RDBMS backend URL; study name |
| Phase 3a | `MDP_OPTUNA_TRIALS`, `MDP_OPTUNA_WORKERS`, `MDP_OPTUNA_OBJECTIVES` | Total trials; parallel workers (0 = auto); objectives |
| Phase 3a | `MDP_INTERVENTION_LOW`, `MDP_INTERVENTION_HIGH` | Intervention search bounds (std units) |
| Phase 3b | `MDP_SHAP_MAX_ROWS`, `MDP_SHAP_PLOT_PATH` | Driver sample cap; summary-plot path |

## How each phase works

### Phase 1 — species clustering
Groups chemical *species* by how they co-vary across the whole dataset: Spark
computes the full inter-species correlation matrix (distributed); each species'
row of that matrix is its feature vector; K-means groups them with
silhouette-based selection of `k`. Only the tiny `n_species × n_species` matrix
reaches the driver. **Outputs:** `phase1/species_clusters`,
`phase1/species_correlation`, `phase1/clustering_metrics`.

### Phase 2a — predictive baseline
Trains `SparkXGBRegressor` **distributed** (one XGBoost worker per Spark task,
auto-detected from cluster parallelism) to predict a secondary pollutant from
the other species. Null predictors flow through as XGBoost-native missing
values; only null *targets* are dropped. **Outputs:** `phase2/xgb_baseline_model`,
`phase2/xgb_baseline_metrics` (RMSE / MAE / R²).

### Phase 2b — causal discovery
Runs `DirectLiNGAM` to recover the causal **DAG** and linear **SEMs** linking
primary pollutants (NO, NO₂, CO, SO₂, VOCs) to secondary pollutants (Ozone,
PM2.5). DirectLiNGAM is single-node, so Spark does the column-pruning,
mean-imputation and a **bounded random sample** first; only the capped sample
reaches the driver. Prior knowledge forbids physically impossible
*secondary → primary* edges. **Outputs:** `phase2/causal_dag` (edge list),
`phase2/causal_sem` (equations in causal order).

### Phase 3a — multi-objective optimization
Optuna's **`NSGAIISampler`** minimises PM2.5 and Ozone **simultaneously** over
emission-reduction interventions. Each candidate is scored by a causal
*do*-operation on the Phase 2b SEM, so the sign-sensitive ozone chemistry makes
this a genuine Pareto trade-off, not "reduce everything to zero". The study
lives in a **relational database** (`sqlite:///db.sqlite3` by default); every
Spark worker attaches to the same study via `optuna.load_study(...)` and runs
its share of trials, so trials evaluate **in parallel across the cluster** with
the RDBMS as the coordination point. Point `MDP_OPTUNA_STORAGE` at Cloud SQL
(MySQL/Postgres) for high parallelism. **Outputs:** `phase3/pareto_front`.

### Phase 3b — explainability (XAI)
`shap.TreeExplainer` on the Phase 2a booster produces a **summary (beeswarm)
plot** of each species' effect magnitude and direction, plus a mean(|SHAP|)
importance table. Spark bound-samples the rows before only that capped sample
reaches the driver (headless Agg rendering). **Outputs:** the summary PNG
(`MDP_SHAP_PLOT_PATH`) and `phase3/shap_importance`.

## Project layout

```
main.py                            # single-command driver (chains all phases)
requirements.txt                   # pinned dependencies
config/pipeline_config.py          # all tunables (12-factor, env-overridable)
src/spark_utils.py                 # shared SparkSession builder
src/phases/phase1_clustering.py    # Phase 1: ingestion + K-means
src/phases/phase2_predictive.py    # Phase 2a: distributed XGBoost baseline
src/phases/phase2_causal.py        # Phase 2b: DirectLiNGAM causal discovery
src/phases/phase3_optimization.py  # Phase 3a: Optuna NSGA-II (RDBMS-backed)
src/phases/phase3_xai.py           # Phase 3b: SHAP explainability
```

Each phase module is independently runnable (`python -m src.phases.<module>`)
and also exposes a `run_*()` function that accepts an injected `SparkSession`,
which is how `main.py` shares one session across the whole pipeline.

## Citing this work

This pipeline accompanies our academic research paper. If you use it, please
cite the paper — fill in the entry below once published:

```bibtex
@article{mdp_causal_air_pollution,
  title   = {TODO: paper title},
  author  = {TODO: authors},
  journal = {TODO: venue},
  year    = {TODO},
  url     = {TODO}
}
```

## License

Released under the [MIT License](LICENSE). Update the copyright line in
`LICENSE` to your preferred attribution before publishing.
