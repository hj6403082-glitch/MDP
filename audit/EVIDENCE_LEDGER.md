# Evidence Ledger — Scientific Audit of MDP

Branch: `review/scientific-audit`. Audited commit: `9da26a3`.
All items below were **independently re-verified** against the current
repository (code, data, saved artifacts) with executable checks in `audit/`.

## A. Verification of the 16 prior findings

| # | Finding | Verified? | Evidence (this audit) |
|---|---------|-----------|-----------------------|
| 1 | Has K-means/XGBoost/DirectLiNGAM/Optuna/SHAP; no PMF or EconML | **Confirmed** | `grep` of `src/`: no `PMF`/`econml`/`CausalForest`. |
| 2 | Clustering output not consumed by causal discovery | **Confirmed** | `phase2_causal.py` imports only `ingest_telemetry`; never reads `species_clusters`. |
| 3 | 204 stations, 1,180,551 rows, no VOC | **Confirmed** | `data_audit.py`: 204 files, 1,180,551 rows, `voc` absent from all. |
| 4 | Optimizer adds `policy_voc` with no effect (no VOC edges) | **Confirmed** | Saved front has `policy_voc`; SEM targets exclude `voc`; coefficient absent. |
| 5 | SEM reduces to the 4 given equations | **Confirmed** | `causal_sem` parquet matches the quoted equations exactly. |
| 6 | All 19 policies dominated by the same-NO, CO=NO₂=−2 corner | **Confirmed & strengthened** | `analytic_pareto.py`: **19/19 dominated by the exact front**; mean PM2.5 gap 0.046, max 0.298 (standardized). |
| 7 | Interventions set standardized *ambient concentrations*, not emissions; means/SDs not persisted | **Confirmed** | `fit_direct_lingam` standardizes in-memory; no scaler saved; optimizer operates in z-space. |
| 8 | Blanket −2σ bounds can imply negative concentrations | **Confirmed (logical)** | For right-skewed pollutants, mean−2σ < 0; no scaler persisted to check or prevent it. |
| 9 | Causal step drops meteorology/station/time; mean imputation; pooled contemporaneous LiNGAM | **Confirmed** | `columns = primary + secondary` only; `Imputer(strategy="mean")`; single pooled fit. |
| 10 | Predictive eval uses random row split | **Confirmed** | `phase2_predictive.py`: `data.randomSplit(...)`. |
| 11 | Completeness conditional on existing rows; ~66.1% of 204×8760 | **Confirmed** | `data_audit.py`: grid completeness **66.06%**; 37 stations <50% within-year. |
| 12 | Timestamps span 2024-12-31 18:00Z → 2025-12-30 17:00Z | **Confirmed** | Exact span reproduced; IST/UTC boundary effect documented in QC report §1. |
| 13 | Unit metadata discarded, unvalidated | **Confirmed (with a correction)** | No unit columns; units unverified. CO max 1490 vs p99.9 = 7.31 initially read as a mg/µg mix, but Phase A2 (`phase_a2_units.py`) shows CO is a **uniform mg/m³ regime** across stations (the 1490 is 0.003% sporadic spikes, not a unit mix). The over-statement is **withdrawn**; CO is on mg/m³ vs others' µg/m³ scale, and a few non-physical outliers exist. |
| 14 | Workers `load_study` without sampler → defaults to TPE, not NSGA-II | **Confirmed** | `phase3_optimization.py` lines 240/257 call `load_study(study_name, storage)` with no `sampler`. Saved "Pareto" set was produced by the default sampler on workers, not the driver's NSGA-II. |
| 15 | SQLite default despite multi-node intent | **Confirmed** | `MDP_OPTUNA_STORAGE` defaults to `sqlite:///db.sqlite3`. |
| 16 | Narrative overstates apportionment, mechanism, SHAP "validation", optimality | **Confirmed** | See §C claim-to-evidence; all four overstatements present in prior README/results text. |

Additional QC evidence from `audit/reports/`:
- Suspicious round caps (NO/NO₂/O₃ ≈ 500, PM2.5 = 1000, PM10 = 1500) → likely
  instrument saturation/capping; not validated.
- Weather is **Open-Meteo reanalysis (modelled)**, nearest ~0.1° grid, not
  co-located station observations.
- Geographic sample is the urban OpenAQ network (Delhi-NCR heavy) — not
  nationally representative.

## B. Framing assessment (requested: do not assume the title is justified)

The proposed title — *"From Prediction to Policy: A Causal Machine Learning
Architecture for Multi-Pollutant Source Apportionment and Control Optimization"*
— is **not supported** by the evidence, on three of its load-bearing terms:

1. **"Source Apportionment"** — requires speciated composition + measurement
   uncertainties fed to a receptor model (e.g. PMF) with external source
   interpretation. The data have none of this (no speciation, no uncertainties,
   no VOC). K-means on correlation profiles is an **exploratory species
   grouping**, not source apportionment.
2. **"Causal … Control Optimization"** — the fitted object is a linear,
   pooled, contemporaneous association model over **standardized ambient
   concentrations**, with no identification strategy (no treatment, no
   overlap/estimand, meteorology/time/space excluded, hidden common causes
   uncontrolled). Interventions act on ambient concentrations, not emissions or
   sectoral controls, and the optimizer's own output is provably dominated. This
   does not support causal *policy* claims.
3. **"Multi-Pollutant"** — defensible (several pollutants are modelled jointly).

**Recommended revised framing (defensible):**
> *"An Exploratory Machine-Learning Pipeline for Urban Air-Quality Data:
> Species Co-variation, Predictive Baselines, and Model-Based Concentration
> Scenario Analysis — with a Critical Assessment of Causal and Policy Claims."*

i.e. retain clustering as **exploratory grouping**, the XGBoost model as a
**predictive baseline** (properly evaluated), DirectLiNGAM as **exploratory
structure discovery** (assumptions reported, not asserted as truth), and the
optimization as **model-based scenario analysis in standardized space** — not
emissions policy. SHAP↔LiNGAM agreement is **consistency**, not independent
causal validation.

## C. Status of corrective work (live)

| Phase | Status |
|-------|--------|
| A — reproducible data audit | **Done** (`audit/data_audit.py`, `audit/reports/`) |
| B — exact Pareto / optimality | **Done** (`audit/analytic_pareto.py`): optimizer dominated; analytic front closed-form |
| B — code/reproducibility repairs + tests | **Done** (phase3/phase2 fixes; `tests/test_phaseB_guards.py` pass) |
| C — leakage-safe temporal/spatial evaluation | **Done** (`audit/phase_c_predictive_eval.py`): held-out R²≈0.25–0.30 |
| D — identification gate + LiNGAM stability | **Done** (`audit/phase_d_*`): not identifiable; NO→ozone stable, rest confounded |
| E — apportionment reframe + grouping stability | **Done** (`audit/phase_e_*`): PMF unsupportable; weak grouping |
| F — defensible scenario analysis w/ uncertainty | **Done** (`audit/phase_f_scenario_analysis.py`): closed-form front + band |
| G — manuscript + claim-to-evidence + readiness | **Done** (`audit/manuscript/`) |

## D. External requirements / approvals (not yet actioned)

- Re-collecting OpenAQ **with units, detection limits and provider metadata**
  would be needed to harmonize concentrations and validate CO scale. (Free, but
  a large re-download — flagged, not run.)
- Any **causal** claim would require a documented intervention/natural
  experiment + emissions or activity data — not currently in hand.
- No paid cloud jobs or external publication performed.
