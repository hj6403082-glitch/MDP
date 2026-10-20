# Results

Outputs of the MDP Causal-AI-for-Air-Pollution pipeline, run on **204 Indian
air-quality monitoring stations (OpenAQ v3) + co-located Open-Meteo weather for
2025** (~1.18M station-hours).

## Contents

| Path | What it is |
|------|------------|
| `results_section.md` | Narrative + tables write-up of all five phases (paper-ready draft) |
| `figures/pareto_front.png` | Phase 3a — PM2.5 vs Ozone Pareto front (NSGA-II), coloured by NO cut |
| `figures/shap_summary.png` | Phase 3b — SHAP summary of ozone drivers |
| `tables/*.csv`, `tables/*.json` | Readable exports of every result table and metric |
| `out/` | Raw pipeline output exactly as written by Spark (Parquet + the saved XGBoost model) |

## Headline findings

- **Phase 1:** species cluster into a combustion/traffic family (CO, NO, NO₂,
  PM10, PM2.5) vs. {Ozone, SO₂} (k=2, silhouette 0.39).
- **Phase 2a:** XGBoost ozone baseline R² = 0.43, RMSE = 23.2 µg/m³.
- **Phase 2b:** DirectLiNGAM recovers NO → NO₂ → CO → SO₂ → Ozone → PM2.5, with a
  **negative NO → Ozone edge (−0.12)** = ozone titration.
- **Phase 3a:** 19-policy Pareto front showing PM2.5 and Ozone **cannot** be
  minimised together by cutting NOₓ (deep NO cuts lower PM2.5 but raise ozone).
- **Phase 3b:** SHAP ranks temperature, humidity and NO as top ozone drivers;
  high NO lowers ozone, **agreeing with the causal DAG**.

Regenerate with `python main.py --phases all` (see the repo root `README.md`).
