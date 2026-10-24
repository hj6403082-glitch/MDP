# Software & Tools — What We Use and Why It Matters

For each component: **what it is**, **why we chose it over alternatives**, and
**where it is used** in the pipeline. This answers the review requirement to
"explain the importance of each code and software, and why we are using it."

---

## Infrastructure / Big-data engine

### Apache Spark (PySpark)
- **What:** distributed in-memory data-processing engine with a Python API.
- **Why it matters:** the dataset is ~1.18M station-hours across 204 files; Spark
  lets the same code run on a laptop and scale out on a cluster without rewriting.
  Its DataFrame API and lazy execution plan avoid loading everything into RAM.
- **Why not pandas alone:** pandas is single-machine and would not scale to the
  full multi-city/multi-year target; Spark is the standard for this scale.
- **Used in:** all three pipeline phases (`src/phases/`), driven by `main.py`.

### Google Cloud Dataproc
- **What:** managed Spark/Hadoop clusters on Google Cloud.
- **Why it matters:** gives a reproducible, disposable cluster so a reviewer can
  re-run the exact pipeline; billed per-second, so experiments are cheap and
  nothing persists accidentally.
- **Why not a static VM/Hadoop install:** no cluster to maintain; the custom
  runtime image (`Dockerfile`) pins every dependency version for reproducibility.
- **Used in:** `submit.sh`, `cloudbuild.yaml`, `Dockerfile` (deployment).

### Parquet (via PyArrow)
- **What:** columnar, compressed, typed on-disk format.
- **Why it matters:** column pruning + compression make reading a few pollutants
  out of 204 files fast; the embedded schema prevents silent type drift.
- **Why not CSV:** CSV loses types and is far larger/slower; a real bug we hit
  (int-vs-float humidity) is exactly what a typed format guards against.

---

## Machine-learning methods

### K-means clustering (Spark MLlib)
- **What:** partitions items into `k` groups by minimizing within-cluster variance.
- **Why it matters:** a transparent, fast first pass at "which species behave
  alike"; the silhouette score gives an objective number of groups.
- **Why not DBSCAN/hierarchical here:** we cluster a handful of species on
  correlation profiles — K-means with silhouette model-selection is simple,
  deterministic (seeded) and defensible; it is **grouping, not apportionment**.
- **Used in:** Phase 1 (`phase1_clustering.py`).

### XGBoost (SparkXGBRegressor)
- **What:** gradient-boosted decision trees — a strong tabular regressor.
- **Why it matters:** air-quality relationships are nonlinear and interacting;
  boosted trees capture these without manual feature engineering and are the
  consistent top performer on tabular benchmarks.
- **Why not linear regression / deep nets:** linear underfits the chemistry; deep
  nets need far more data and tuning and rarely beat boosting on tabular data.
- **Used in:** Phase 2a predictive baseline, and the SHAP explanation.

### DirectLiNGAM (`lingam`)
- **What:** learns a linear, non-Gaussian acyclic causal structure (a DAG) from
  observational data.
- **Why it matters:** it is one of the few methods that can *orient* edges (not
  just correlate) under its assumptions, letting us pose directional hypotheses
  such as NO → ozone.
- **Why we are cautious:** it assumes linearity, non-Gaussianity, acyclicity and
  **no hidden confounders** — we explicitly test the last by adding meteorology,
  which is why we report only the one edge that survives.
- **Used in:** Phase 2b causal discovery.

### Optuna + NSGA-II sampler
- **What:** Optuna is an optimization framework; NSGA-II is a multi-objective
  evolutionary algorithm that returns a Pareto front, not one answer.
- **Why it matters:** policy involves trade-offs (lower ozone vs lower PM2.5);
  NSGA-II surfaces the whole trade-off surface instead of a single compromise.
- **Why the sampler choice is critical:** Optuna defaults to TPE, which is
  single-objective; we must pass `NSGAIISampler` explicitly (a bug the audit
  fixed). For our *linear* model we also derived the exact front in closed form to
  check the metaheuristic — and it was dominated.
- **Used in:** Phase 3a optimization + `analytic_pareto.py` cross-check.

### SHAP (TreeExplainer)
- **What:** Shapley-value feature attributions; exact and fast for tree models.
- **Why it matters:** turns the black-box XGBoost into per-feature, per-prediction
  explanations with a sound game-theoretic basis — needed for any "XAI" claim.
- **Why not plain feature importance:** gain/weight importances are inconsistent
  and global; SHAP is locally accurate and additive.
- **Used in:** Phase 3b explainability.

---

## Data sources

### OpenAQ v3 API
- **What:** open aggregator of government/reference air-quality monitors.
- **Why it matters:** real, citable regulatory measurements for India at hourly
  resolution — no fabrication, and reproducible by any reviewer with a free key.
- **Caveat we surface:** per-sensor units must be captured to compare stations.

### Open-Meteo reanalysis
- **What:** free historical/reanalysis weather API.
- **Why it matters:** ozone is weather-driven; we need co-located temperature,
  humidity, wind and pressure. Reanalysis gives complete, gap-free coverage.
- **Caveat we surface:** weather is **modelled**, not measured on-site.

---

## Engineering & reproducibility

| Tool | Why it matters |
|------|----------------|
| **Git + feature branch** | Raw data and original results preserved; all audit work isolated on `review/scientific-audit`. |
| **Docker (custom image)** | Pins every library version so the cluster run is byte-for-byte reproducible. |
| **Fixed seeds (`SEED=42`)** | Every clustering/boosting/bootstrap run is deterministic and re-checkable. |
| **scikit-learn / SciPy / statsmodels** | Standard, audited implementations of metrics, splits, bootstrap and stats used throughout the audit. |
| **Matplotlib** | Publication figures (e.g. the scenario frontier) generated from the same data. |
| **pytest** | Encodes correctness guards (e.g. "optimizer front truly dominates") as tests that must pass. |

**One-line summary of the stack choice:** every tool is the *standard, citable,
reproducible* option for its job — Spark/Dataproc for scale, Parquet for typed
storage, XGBoost for tabular prediction, DirectLiNGAM for directional hypotheses,
NSGA-II for trade-offs, SHAP for explanations — and each is paired with an honest
caveat about what it can and cannot establish on this dataset.
