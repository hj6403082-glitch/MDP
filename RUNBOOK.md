# RUNBOOK — what to run, in what order, with which files

Two independent tracks. For the **audit** (the defensible, reproducible science)
you only need plain Python — no Spark. For the **original pipeline** you need
Spark/Java (Cloud Shell or Dataproc). Most people want Track A.

---

## 0. Get the code

```bash
git clone -b review/scientific-audit https://github.com/hj6403082-glitch/MDP.git
cd MDP
```
- Branch `review/scientific-audit` has everything: code + data + results + audit.
- The raw dataset is already in `data/raw/telemetry/` (204 Parquet files).

---

## Track A — Reproduce the audit (recommended; no Spark needed)

### A1. Environment (Python 3.11–3.13)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install numpy pandas pyarrow scikit-learn xgboost scipy statsmodels matplotlib tabulate
# DirectLiNGAM (only needed for Phase D and F):
sudo apt-get install -y gfortran      # Debian/Ubuntu/Cloud Shell; lets lingam build
pip install lingam
```
If `pip install lingam` still fails, you can skip it and run every phase **except
D and F** (they are the only ones that import it).

### A2. Run the phases (each writes to `audit/reports/`)
Run in this order; each is self-contained and fixes `SEED=42`.

| Step | Command | File used | What you get |
|------|---------|-----------|--------------|
| 1 | `python audit/data_audit.py` | `audit/data_audit.py` | Data-quality report + coverage/availability tables |
| 2 | `python audit/phase_a2_units.py` | `audit/phase_a2_units.py` | Unit inference, outlier cleaning, cleaned dataset, CO fix |
| 3 | `python audit/analytic_pareto.py` | `audit/analytic_pareto.py` | Proof the 19 saved policies are all dominated |
| 4 | `python -m pytest tests/test_phaseB_guards.py -q` | `tests/test_phaseB_guards.py` | Code-correctness tests pass |
| 5 | `python audit/phase_c_predictive_eval.py` | `audit/phase_c_predictive_eval.py` | Leakage-safe R² (temporal/spatial), baselines, ablations (~2 min) |
| 6 | `python audit/phase_d_causal_stability.py --boot 80` | `audit/phase_d_causal_stability.py` | DirectLiNGAM stability + meteorology sensitivity (~2 min) |
| 7 | `python audit/phase_e_grouping.py --boot 150` | `audit/phase_e_grouping.py` | Clustering stability (silhouette, co-assignment) |
| 8 | `python audit/phase_f_scenario_analysis.py --boot 80` | `audit/phase_f_scenario_analysis.py` | Scenario frontier figure + uncertainty |

### A3. Read the results (no run needed)
| To understand… | Open this file |
|----------------|----------------|
| The whole audit at a glance | `audit/README.md` |
| Every prior finding verified | `audit/EVIDENCE_LEDGER.md` |
| Each claim: supported/conditional/unsupported | `audit/manuscript/CLAIM_TO_EVIDENCE.md` |
| The paper draft (narrowed, honest) | `audit/manuscript/MANUSCRIPT.md` |
| Is it publishable? what's left? | `audit/manuscript/READINESS.md` |
| Generated metrics/figures/logs | `audit/reports/` |

---

## Track B — Verify the measurement units (needs your OpenAQ key)

This is the **one step that cannot be done offline**. It fetches the authoritative
per-sensor units (~204 light metadata calls — it does NOT re-download measurements).

```bash
export OPENAQ_API_KEY="your-key"          # free: https://explore.openaq.org/account
python audit/fetch_units.py               # writes audit/reports/units_authoritative.csv
```
- File used: `audit/fetch_units.py`.
- Compare its output against `audit/reports/unit_inference.csv` (the inferred units)
  to confirm or correct them. It also flags any pollutant with a true unit mix.

---

## Track C — Run the original pipeline (optional; needs Spark + Java)

Only if you want to regenerate the original phase outputs. Use **Cloud Shell**
(Python 3.12, Java pre-installed) or Dataproc.

```bash
sudo apt-get install -y openjdk-17-jdk-headless
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 PATH=$JAVA_HOME/bin:$PATH
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt           # pyspark, xgboost, lingam, optuna, shap, ...

export MDP_INPUT_PATH=./data/raw/telemetry
export MDP_INPUT_FORMAT=parquet
export MDP_OUTPUT_PATH=./out
export MDP_SPECIES_COLUMNS="co,no,no2,ozone,pm10,pm25,so2"
python main.py --phases all                # file used: main.py
```
- File used: `main.py` (chains all five phases). Outputs land in `./out/`.
- To run on the **cleaned** data instead, first run step A2, then set
  `MDP_INPUT_PATH=./audit/analysis_dataset` and
  `MDP_INPUT_FORMAT=parquet` (single cleaned file).
- To collect fresh data: `python data_collection.py --start 2025-01-01 --end 2025-12-31 --no-upload`
  (now also writes a `telemetry_units.csv` manifest).

---

## TL;DR

- **Just reproduce the real findings:** do Track A (steps 0 → A1 → A2 steps 1–8).
- **Confirm the units:** do Track B with your key.
- **Re-run the pipeline:** do Track C in Cloud Shell.
- **Read, don't run:** start at `audit/README.md`.
