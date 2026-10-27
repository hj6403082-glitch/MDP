# MDP Project Report

**Multi-Pollutant Air-Quality Machine Learning over 204 Indian Monitoring Stations**
*Build → Audit → Verify → Reframe. Progress report.*

---

## 1. Executive summary

The MDP project set out to build a cloud-scale machine-learning pipeline that goes
from *prediction* of air-pollutant levels, to *causal structure* among pollutants,
to *policy optimization* — "Causal AI for Air Pollution." We **built the full
pipeline, ran it on real data, and then subjected it to a rigorous independent
audit**. The engineering is sound and reproducible, and the dataset is real; but the
audit found that the strongest scientific claims (causal mechanisms, source
apportionment, Pareto-optimal policy) are **not supported** by the available data.

We therefore **reframed the work honestly** as an *open, leakage-safe benchmark* for
multi-pollutant air-quality ML — a dataset, an evaluation protocol, and honest
baselines others can build on — plus a set of cautionary methodological findings.
Measurement units were verified against the authoritative source, and all citations
were verified. The project is, for review purposes, **complete**; what remains are
decisions (venue, authorship) and a final reformat before submission.

## 2. Original objective

A three-phase PySpark pipeline on Google Cloud Dataproc:
- **Phase 1** — species clustering (K-means) to group co-varying pollutants.
- **Phase 2** — predictive baseline (XGBoost) + causal discovery (DirectLiNGAM).
- **Phase 3** — multi-objective policy optimization (Optuna/NSGA-II) + explainability (SHAP).

Intended framing: *"Causal Machine Learning for Multi-Pollutant Source Apportionment
and Control Optimization."*

## 3. What we built

- A complete **PySpark pipeline** (`src/phases/`, driven by `main.py`) implementing
  all three phases, packaged for **Google Cloud Dataproc** with a custom Docker
  runtime (`Dockerfile`, `submit.sh`, `cloudbuild.yaml`).
- An automated **data-collection tool** (`data_collection.py`) pulling real
  measurements from the OpenAQ v3 API and co-located weather from Open-Meteo.
- The pipeline **runs end-to-end** on the real 204-station dataset — every phase
  completes successfully on Dataproc and in Cloud Shell.
- Full **engineering hygiene**: MIT licence, README, requirements, fixed seeds,
  reproducible manifests, and a correctness test suite.

(Tool-by-tool justification is in `SOFTWARE_STACK.md`; algorithm pseudocode in
`PSEUDOCODE.md`.)

## 4. The dataset

- **204 Indian monitoring stations**, hourly, calendar year 2025.
- Pollutants: CO, NO, NO₂, O₃, PM10, PM2.5, SO₂; merged with modelled weather
  (temperature, humidity, wind, pressure).
- **~1.18 million station-hours** (~66% of a full 204 × 8,760 grid); 37 stations
  below 50% within-year coverage.
- Real, open, and reproducible — committed alongside the code.

## 5. The scientific audit

Acting as a critical reviewer, we independently re-examined every major claim on a
dedicated branch (`review/scientific-audit`), writing self-contained scripts that
regenerate every number offline with a fixed seed. The audit added the diagnostics
the original pipeline lacked: **leakage-safe evaluation**, bootstrap stability,
meteorology-confounding tests, and an exact-optimality cross-check.

## 6. Key findings

**6.1 Prediction.** Random-split evaluation gave an optimistic R² ≈ 0.41, but that is
**data leakage** on autocorrelated data. Under honest, leakage-safe evaluation the
held-out R² is **0.25** (blocked-temporal) to **0.30** (unseen stations). Pollutants
add only **+0.12 R² beyond weather**; a 1-hour-ahead forecast beats a persistence
baseline by only **+0.05**. The model beats trivial spatial baselines but not
temporal persistence.

**6.2 Causal structure.** Of all discovered edges, exactly **one** is both
bootstrap-stable and survives the inclusion of meteorology: **NO → ozone (negative)**,
consistent with local titration chemistry — reported as a *hypothesis*, not an
identified effect. The wider graph is confounded by weather.

**6.3 Grouping.** K-means produces only weak clusters (silhouette 0.26–0.39); it is
*grouping*, not source apportionment (which needs speciation, uncertainties and VOCs
the data lack).

**6.4 Optimization.** The published metaheuristic returned **19 "optimal" policies —
all of which are dominated** by the exact closed-form frontier we derived. A worker
bug (wrong sampler) and a phantom decision variable were also found and fixed.

**6.5 Units (major finding).** Verified against the **authoritative OpenAQ sensor
metadata**: NO (ppb), ozone, PM2.5, PM10 (µg/m³) are unit-consistent, but **CO, NO₂
and SO₂ carry duplicate ppb + µg/m³ sensors at almost every station** with no per-row
provenance, so their stored unit is indeterminate. Crucially, both headline results
(ozone prediction, NO→ozone) rest only on **unit-consistent** variables, so they
stand.

## 7. The honest reframe

Because the words *causal*, *source apportionment* and *control optimization* could
not be supported, we narrowed the claim rather than conceal the limitation. The work
is now presented as:

> **An open, leakage-safe benchmark for multi-pollutant air-quality machine learning
> over 204 Indian monitoring stations** — contributing an open dataset, a
> leakage-safe evaluation protocol, honest baselines, one testable NO–O₃ hypothesis,
> and a clear account of what stronger claims would require.

This is a genuine, defensible contribution to the air-quality / environmental-AI
field (see `SIGNIFICANCE.md`).

## 8. Deliverables produced

- Full pipeline + deployment (code, Docker, scripts)
- Real 204-station dataset
- Audit scripts reproducing every result (`audit/*.py`)
- Rough research-paper draft (`ROUGH_DRAFT.md`), honest and narrowed
- Pseudocode, software justification, significance, publication plan
- **6 publication figures** (regenerable; appended here)
- **All 12 references verified** against authoritative records
- Units verification against authoritative metadata
- Secondary-dataset evaluation (a modelled dataset, assessed and set aside)
- A shareable PDF package of all of the above

## 9. Current status & remaining work

**Status: complete for review purposes.** All *work* is done, committed and pushed.

Remaining items are decisions/formalities, not engineering:
1. Confirm the benchmark framing and choose a target venue (with the supervisor).
2. Finalize author list and affiliations.
3. Reformat the draft into the chosen venue's template; final proofread; submit.

## 10. One-paragraph conclusion

We built a working, reproducible, cloud-scale air-quality ML pipeline on real Indian
data, then held it to a high evidentiary standard. Rather than overstate what the
data support, we corrected course: a verified dataset, a leakage-safe evaluation, one
stable scientific hypothesis, and an honest map of the limits — released as an open
benchmark. The result is a smaller but **defensible** contribution, and a project
that demonstrates not just building a pipeline, but knowing what it does and does not
prove.
