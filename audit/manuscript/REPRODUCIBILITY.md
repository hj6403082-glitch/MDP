# Reproducibility Guide

All audit analyses are plain Python (pandas / scikit-learn / xgboost / lingam /
matplotlib) and run **without Spark** on the committed dataset. They were executed
on Python 3.13; the pipeline itself targets Python 3.12 + Spark 3.5 (see root
`README.md`).

## 1. Environment

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install numpy pandas pyarrow scikit-learn xgboost scipy statsmodels matplotlib tabulate
# DirectLiNGAM without its heavy optional deps (Phase D/E/F):
pip install --no-deps lingam networkx graphviz autograd factor_analyzer
#   (lingam pulls optional packages needing a Fortran compiler; only DirectLiNGAM
#    is used here. If import fails on an optional sub-module, install or stub it.)
```

Data lives in `data/raw/telemetry/*.parquet` (204 files). Original pipeline
outputs are in `results/out/`. All audit outputs go to `audit/reports/`.

## 2. Reproduce each phase

```bash
python audit/data_audit.py                 # Phase A: QC report + data dictionary tables
python audit/phase_a2_units.py             # Phase A2: unit inference, cleaning, CO sensitivity
# export OPENAQ_API_KEY=... ; python audit/fetch_units.py   # authoritative per-sensor units (optional)
python audit/analytic_pareto.py            # Phase B: exact front vs saved policies
python -m pytest tests/test_phaseB_guards.py -q   # Phase B: correctness tests
python audit/phase_c_predictive_eval.py    # Phase C: leakage-safe evaluation  (~min)
python audit/phase_c2_prediction_plus.py   # Phase C2: incremental value, harmonics, t+1h forecast
python audit/phase_d_causal_stability.py --boot 80    # Phase D: LiNGAM stability (~min)
python audit/phase_e_grouping.py --boot 150           # Phase E: grouping stability
python audit/phase_f_scenario_analysis.py --boot 80   # Phase F: scenario frontier + figure
python audit/make_figures.py                          # publication figures -> audit/reports/figures/
```

Determinism: every script fixes `SEED = 42`. Bootstrap counts are CLI flags;
larger values tighten intervals. XGBoost hyper-parameters are fixed a priori and
never tuned on any test set.

## 3. Key output artefacts

| Phase | Script | Outputs in `audit/reports/` |
|-------|--------|-----------------------------|
| A | data_audit.py | data_quality_report.md, audit_summary.json, *.csv |
| B | analytic_pareto.py | pareto_comparison.json, exact_pareto_front.csv |
| C | phase_c_predictive_eval.py | phase_c_predictive_eval.md, phase_c_metrics.csv |
| C2 | phase_c2_prediction_plus.py | phase_c2_prediction_plus.md, phase_c2_metrics.csv, phase_c2_summary.json |
| D | phase_d_causal_stability.py | phase_d_causal_stability.md, phase_d_bootstrap_edges.csv, phase_d_identification_gate.md |
| E | phase_e_grouping.py | phase_e_grouping.md, phase_e_coassignment.csv, phase_e_apportionment_assessment.md |
| F | phase_f_scenario_analysis.py | phase_f_scenario_analysis.md, phase_f_scenario_front.png/.csv, phase_f_scenario_summary.json |

## 4. Provenance

- Raw data and original results are preserved unmodified; all audit work is on
  branch `review/scientific-audit` under `audit/`.
- The Phase 2b pipeline now persists a manifest (`phase2/causal_manifest`) with the
  fitted variables, per-variable scalers, standardized adjacency, seed and library
  versions, so the response model is reproducible and interpretable.
- Known non-reproducibility to disclose: pollutant **units** are not recoverable
  from the stored data; exact silhouette/coefficients depend on imputation and
  sampling choices (documented in Phases E/F).
