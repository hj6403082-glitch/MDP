# Scientific Audit — Index

Independent re-examination of the MDP project (branch `review/scientific-audit`).
Raw data and original results are preserved unmodified; all audit work lives here.

Start with **`EVIDENCE_LEDGER.md`** (verification of all prior findings + framing
verdict) and **`manuscript/READINESS.md`** (publication-readiness).

## Executable analyses (`audit/*.py` → `audit/reports/`)
| Phase | Script | What it establishes |
|-------|--------|---------------------|
| A | `data_audit.py` | Data QC: 66% grid completeness, no units (CO mg/µg mix), weak coverage, geography |
| B | `analytic_pareto.py` + `tests/test_phaseB_guards.py` | All 19 "optimal" policies dominated by the exact front; code guards tested |
| C | `phase_c_predictive_eval.py` | Leakage-safe R²≈0.25–0.30 (vs 0.41 leaky); persistence 0.79; ablations |
| D | `phase_d_causal_stability.py` | NO→ozone stable; PM2.5 edges confounded by weather; order prior-sensitive |
| E | `phase_e_grouping.py` | Weak clustering (silhouette 0.26–0.39); CO unstable; not apportionment |
| F | `phase_f_scenario_analysis.py` | Closed-form concentration-scenario frontier + uncertainty (not emissions) |

## Written assessments (`audit/reports/`, `audit/manuscript/`)
- `reports/phase_d_identification_gate.md` — causal checklist; identification not met.
- `reports/phase_e_apportionment_assessment.md` — why PMF is unsupportable.
- `manuscript/MANUSCRIPT.md` — defensible draft (Methods/Results/Discussion/Limitations) + title options.
- `manuscript/CLAIM_TO_EVIDENCE.md` — every claim: supported / conditional / unsupported.
- `manuscript/ORIGINAL_VS_CORRECTED.md` — side-by-side of original vs corrected conclusions.
- `manuscript/BIBLIOGRAPHY.md` — method/data references (verify DOIs before submission).
- `manuscript/REPRODUCIBILITY.md` — environment + commands to regenerate everything.
- `manuscript/READINESS.md` — honest readiness, prioritized work, title recommendation.

## Headline verdict
Software is sound and reproducible; the dataset is real. But **causal**,
**source-apportionment**, and **control-optimization** claims are **unsupported**.
Reframe as an exploratory + methodological-cautionary study (leakage-safe
evaluation, one stable NO–ozone association, a dominated "optimizer", honest
limitations).
