# Results

## Dataset

Hourly air-quality observations were collected from **204 monitoring stations
across India** (OpenAQ v3) for 2025, covering the primary pollutants CO, NO,
NO₂, SO₂, PM10 and PM2.5 and the secondary pollutant Ozone, and merged with
co-located hourly meteorology (temperature, relative humidity, wind speed,
surface pressure) from the Open-Meteo reanalysis. After quality filtering
(per-species coverage 91–98%), the integrated dataset comprised **≈1.18 million
station-hours**. All processing was performed with the distributed PySpark
pipeline described in Section [Methods].

## Phase 1 — Objective grouping of chemical species

K-means clustering of the species, using each species' inter-species Pearson
correlation profile as its feature vector, selected **k = 2** by silhouette
score (0.39; monotonically decreasing for k = 3–5), yielding:

| Cluster | Species |
|---------|---------|
| 1 — combustion/traffic family | CO, NO, NO₂, PM10, PM2.5 |
| 0 — secondary / industrial     | Ozone, SO₂ |

The primary traffic-emission gases and particulates co-vary as a single family,
reflecting shared combustion sources, whereas **ozone separates out** — a
secondary pollutant that frequently anti-correlates with fresh NO — and **SO₂**
forms a distinct, largely point-source signal.

## Phase 2a — Predictive baseline

A distributed `xgboost.spark` regressor trained to predict hourly Ozone from the
remaining species and meteorology achieved:

| Metric | Value |
|--------|-------|
| R²   | 0.43 |
| RMSE | 23.2 µg/m³ |
| MAE  | 14.5 µg/m³ |

The model explains ~43% of hourly ozone variance — a reasonable baseline given
ozone's strongly non-linear photochemistry — and serves as the surrogate for the
explainability analysis (Phase 3b).

## Phase 2b — Causal discovery (DirectLiNGAM)

DirectLiNGAM, constrained by the physical prior that secondary pollutants cannot
cause primary emissions, recovered the causal order
**NO → NO₂ → CO → SO₂ → Ozone → PM2.5** with the following structural
coefficients (standardized):

| Cause → Effect | Coef. | Mechanism |
|----------------|------:|-----------|
| NO → NO₂       | +0.38 | oxidation of NO |
| NO → CO        | +0.33 | shared combustion origin |
| NO₂ → CO       | +0.26 | shared combustion origin |
| **NO → Ozone** | **−0.12** | **ozone titration (NO consumes O₃)** |
| CO → PM2.5     | +0.23 | precursor to secondary aerosol |
| NO₂ → PM2.5    | +0.22 | precursor to secondary aerosol |
| NO → PM2.5     | +0.09 | precursor to secondary aerosol |

The recovered structure is chemically coherent: ozone and PM2.5 are terminal
*effect* nodes, and the **negative NO → Ozone edge** reproduces the well-known
titration effect, by which freshly emitted NO destroys ozone.

## Phase 3a — Multi-objective policy optimization

An Optuna NSGA-II study searched emission-reduction interventions on the primary
pollutants to minimise Ozone and PM2.5 simultaneously, evaluating each candidate
by propagating it through the Phase 2b structural-equation model. The resulting
**Pareto front (19 non-dominated policies; Figure X)** exposes a fundamental
trade-off:

| Strategy | NO level | Ozone | PM2.5 |
|----------|---------:|------:|------:|
| Spare NO (protect ozone)   | ≈ 0.00 (unchanged) | ~0.00 | −0.87 |
| Deep NO cut (protect PM2.5)| ≈ −1.90 (strong cut)| +0.24 | −1.04 |

*(Objectives and interventions are in standardized units: 0 = historical mean
emission, −2 = two standard deviations below it.)*

PM2.5 and Ozone **cannot be minimised jointly by reducing NOₓ**: aggressive NO
abatement lowers particulates but *raises* ozone, because less NO is available
to titrate it. The Pareto front therefore defines the admissible set of
trade-offs available to policymakers rather than a single optimum.

## Phase 3b — Explainability (SHAP)

SHAP attribution on the Phase 2a model ranked the drivers of ozone (mean |SHAP|)
as:

| Rank | Feature | mean \|SHAP\| |
|-----:|---------|-------------:|
| 1 | relative_humidity | 6.66 |
| 2 | temperature       | 3.87 |
| 3 | NO                | 3.46 |
| 4 | pressure          | 2.81 |
| 5 | SO₂               | 2.30 |

The beeswarm summary (Figure Y) shows **high temperature strongly raises ozone**
(heat-driven photochemistry), **high humidity lowers it**, and **high NO lowers
it** — the latter in agreement with the sign of the causal NO → Ozone edge.
Meteorology thus dominates ozone variability, with NO titration as the principal
chemical lever.

## Cross-method consistency

A notable validation is that two independent methods converge on the same
mechanism: DirectLiNGAM assigns a **negative causal coefficient** to NO → Ozone,
and SHAP independently shows **high NO reducing predicted ozone**. This
agreement between a causal-discovery model and a post-hoc explanation of a
separate predictive model strengthens confidence in the titration finding and in
the NOₓ-vs-ozone trade-off that drives the Phase 3 optimization.

## Limitations

The structural model is linear, so non-linear regime dependence (e.g.
VOC-limited vs NOₓ-limited ozone chemistry) is only partially captured; VOC
coverage was sparse in the public network; and the baseline R² (0.43) indicates
substantial unexplained ozone variance. Objectives in Phase 3 are expressed in
standardized units and should be mapped back to concentration units before
operational use.

---

*Figure X — Pareto front of PM2.5 vs Ozone (file: `pareto_front.png`).*
*Figure Y — SHAP summary of ozone drivers (file: `shap_summary.png`).*
