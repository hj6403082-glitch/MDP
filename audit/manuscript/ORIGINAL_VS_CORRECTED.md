# Original vs Corrected Conclusions

| Topic | Original project stated | Corrected (post-audit) |
|-------|-------------------------|------------------------|
| **Framing** | Causal ML for source apportionment & control optimization | Exploratory ML: predictive baseline, associational structure, concentration scenarios |
| **Ozone prediction** | R² = 0.43 (good baseline) | R² ≈ 0.25–0.30 held-out; 0.41 was leakage-inflated; persistence (0.79) wins for gap-filling |
| **Evaluation** | Random 80/20 split | Blocked-temporal + leave-stations-out + strict; train-fold-only preprocessing |
| **Causal graph** | Discovered causal DAG + SEMs; mechanisms | Exploratory structure; only NO→ozone stable & weather-robust; rest confounded/unstable |
| **NO→ozone** | Causal titration mechanism | Stable negative *association* consistent with local titration; a hypothesis |
| **SHAP** | Independent validation of causality | Internal consistency of two models on the same data |
| **Clustering** | Objective source groups / apportionment | Weak exploratory grouping (silhouette 0.26–0.39); CO unstable; not apportionment |
| **Optimization** | NSGA-II Pareto-optimal emission policies | All 19 points dominated by the exact closed-form frontier; workers ran TPE, not NSGA-II |
| **Interventions** | Emission-reduction policies with benefits | Standardized ambient-concentration what-ifs; not emissions, no benefit units |
| **VOC** | A decision variable in optimization | Structurally absent from data; phantom variable (now rejected in code) |
| **Units** | (Not discussed) | Not stored; CO mixed mg/m³ vs µg/m³ — a demonstrated cross-station error |
| **Weather** | (Treated as data) | Modelled Open-Meteo reanalysis, not station observations |
| **Representativeness** | National (India-wide) | Urban, Delhi-NCR-heavy; not nationally representative |
| **Software bugs** | — | NSGA-II worker sampler, phantom VOC var, unpersisted scalers — fixed in Phase B with tests |
