# Claim-to-Evidence Table

Status: **Supported** (evidence holds) · **Conditional** (defensible only when
narrowed/caveated) · **Unsupported** (not justified by available evidence).

| # | Claim | Status | Evidence / basis |
|---|-------|--------|------------------|
| 1 | Pipeline runs end-to-end on real data | Supported | Verified Cloud Shell run; all phases `all_ok`. |
| 2 | 204-station Indian dataset, ~1.18M station-hours | Supported | `audit/data_audit.py`. |
| 3 | Dataset is nationally representative | Unsupported | Urban, Delhi-NCR-heavy OpenAQ network (audit §A §8). |
| 4 | Reported pollutant completeness (90%+) | Conditional | True only *within existing rows*; ~66% of full grid; 37 stations <50% (audit §A). |
| 5 | Measurements are comparable across stations | Conditional | **Units now verified against authoritative OpenAQ sensor metadata.** NO (ppb), ozone, PM2.5, PM10 (µg/m³) are unit-consistent; **CO, NO2, SO2 carry duplicate ppb + µg/m³ sensors at ~all stations** with no per-row provenance, so their stored unit is indeterminate (corrects the earlier value-based "CO uniform" inference). 35 non-physical outliers flagged (Phase A2). See `units_verification.md`. |
| 6 | Ozone is predictable from pollutants+weather, R²≈0.43 | Conditional | Leaky split; honest held-out R²≈0.25–0.30 (Phase C); the apparent 0.41 is recovered only by a train-only station-mean feature, which is site memorisation, not generalisation (Phase C2). |
| 7 | Model is practically useful for ozone estimation | Conditional | Beats spatial baselines (R²≈0 → 0.30) but barely beats persistence: 1h-ahead forecast R²=0.865 vs persistence 0.812, a +0.05 gain (Phase C/C2). |
| 8 | Weather and pollutants both inform ozone | Supported | Ablations 0.14 / 0.13 / 0.25 (Phase C); pollutants add only +0.12 R² *beyond* weather on the held-out set (Phase C2). |
| 9 | A causal DAG among pollutants was discovered | Conditional | Exploratory structure; only NO→ozone is bootstrap-stable & survives weather (Phase D). |
| 10 | The graph gives chemical *mechanisms* | Unsupported | Pooled linear contemporaneous; confounded by meteorology; assumptions unmet (Phase D). |
| 11 | NO→ozone titration | Conditional | Stable negative association (−0.138±0.007); reported as hypothesis, not identified effect. |
| 12 | SHAP validates the causal finding | Unsupported | Internal consistency of two models on the same data, not independent validation. |
| 13 | Species cluster into meaningful source groups | Conditional | Weak silhouette (0.26–0.39); core stable, CO unstable; grouping only (Phase E). |
| 14 | Source apportionment achieved | Unsupported | No speciation/uncertainty/VOC; no receptor model (Phase E). |
| 15 | NSGA-II found Pareto-optimal policies | Unsupported | All 19 dominated by the exact closed-form frontier; workers ran TPE not NSGA-II (Phase B/F). |
| 16 | Policies are emission-reduction recommendations | Unsupported | Act on standardized ambient concentrations, not emissions; no policy-benefit meaning (Phase D/F). |
| 17 | Multi-pollutant joint analysis | Supported | Several pollutants modelled jointly. |
| 18 | Results are reproducible | Supported | Code, data, seeds, manifests, audit scripts committed. |
