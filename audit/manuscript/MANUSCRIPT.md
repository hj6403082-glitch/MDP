# Exploratory Machine Learning on Urban Air-Quality Monitoring Data: Predictive Baselines, Associational Structure, and Model-Based Concentration Scenarios

*Working manuscript draft (post-audit). Every number below was produced by the
scripts in `audit/` on the committed dataset. Claims are deliberately bounded;
see §Limitations and the claim-to-evidence table.*

### Recommended title options (the original title is not supported — see §7)
1. *Exploratory Machine Learning on Urban Air-Quality Monitoring Data: Predictive
   Baselines, Associational Structure, and Model-Based Concentration Scenarios.*
2. *What Can and Cannot Be Learned from Pooled Regulatory Air-Quality Data: A
   Critical ML Case Study over 204 Indian Monitoring Stations.*

The original *"…Causal Machine Learning … for Multi-Pollutant Source
Apportionment and Control Optimization"* is **not** justified: the words
*causal*, *source apportionment* and *control optimization* each fail (see §7).

---

## Abstract

We assemble one year (2025) of hourly observations from 204 Indian air-quality
monitoring stations (OpenAQ) merged with co-located modelled meteorology
(Open-Meteo) — about 1.18 million station-hours — and evaluate what a machine-
learning pipeline can and cannot defensibly conclude from it. Under leakage-safe
evaluation, a gradient-boosted model estimates contemporaneous ozone with
held-out R² ≈ 0.25 (blocked temporal) to 0.30 (unseen stations), substantially
below the 0.41–0.43 obtained from a leaky random split; a naive previous-hour
persistence baseline (R² ≈ 0.79) dominates for temporal gap-filling but does not
apply to unsensored sites. Exploratory causal-structure discovery (DirectLiNGAM)
recovers one bootstrap-stable association consistent with local NO–ozone
titration, but the broader graph is confounded by omitted meteorology and is not
causally identified. K-means groups co-varying species only weakly (silhouette
0.26–0.39) and does not constitute source apportionment. A linear response model
admits a closed-form concentration-scenario frontier; a published metaheuristic
"optimization" returned only dominated points. We conclude that the engineering
is sound and reproducible, but that causal, apportionment and policy claims are
unsupported by these data, and we specify what additional evidence each would
require.

## 1. Introduction

Urban air quality in India is a major public-health problem, and open monitoring
data invite machine-learning analysis. A tempting narrative runs *prediction →
causal structure → policy optimization*. We test that narrative critically on a
large but imperfect regulatory dataset and report, with uncertainty, where it
holds and where it breaks.

## 2. Data

**Sources.** Hourly air-quality measurements for CO, NO, NO₂, O₃, PM10, PM2.5 and
SO₂ were collected from the OpenAQ v3 API for 204 Indian stations with data in
2025; each station was merged with hourly Open-Meteo reanalysis weather
(temperature, relative humidity, wind speed, surface pressure) at the nearest
~0.1° grid cell.

**Scale and completeness (audit §A).** 1,180,551 station-hours — ~66% of a full
204 × 8,760 grid; 37 stations have <50% within-year coverage. Completeness is
*conditional on existing rows*; missingness is a mix of structural (no sensor),
intermittent (sensor gaps) and below-detection (indistinguishable — no
detection-limit metadata).

**Quality caveats (audit §A, §A2, units verification).** Measurement units were
**verified against the authoritative OpenAQ per-sensor metadata**. NO (ppb), ozone,
PM2.5 and PM10 (µg/m³) are unit-consistent across the network. CO, NO₂ and SO₂,
however, carry **duplicate sensors reporting in both ppb and µg/m³ at almost every
station** (e.g. CO at 183/198 stations), and the stored dataset keeps a single value
per pollutant per station-hour with no record of which sensor produced it — so for
these three the unit is **indeterminate** and cannot be harmonized post hoc. (This
corrects an earlier value-based inference that CO was uniform; the authoritative
metadata governs.) We therefore restrict quantitative cross-station claims to the
unit-consistent pollutants; our two headline results (ozone prediction, NO–O₃)
depend only on those. A small number of non-physical outliers (35 flagged) and round
saturation caps (NO/NO₂/O₃ ≈ 500, PM2.5 = 1000) are present. Weather is **modelled**,
not observed. The network is urban and Delhi-NCR-heavy — **not** nationally
representative. VOCs are **structurally absent**.

## 3. Methods

All code is in the repository; the audit scripts (`audit/*.py`) reproduce every
result. We define three analyses and their evaluation.

**3.1 Predictive baseline (contemporaneous estimation).** Gradient-boosted trees
(XGBoost) estimate same-hour ozone from the other pollutants and weather. This is
association, not forecasting or causation. We evaluate with: a leaky random split
(for contrast only); a **blocked temporal** split (train months 1–9, test 10–12);
**leave-stations-out** (unseen stations); and the strict intersection. All
preprocessing is fit on the training fold only; hyper-parameters are fixed a
priori. Baselines: global mean, per-station climatology, previous-hour
persistence. Uncertainty via station-block bootstrap.

**3.2 Exploratory structure discovery.** DirectLiNGAM is fit on standardized
pollutants with a prior forbidding secondary→primary edges. We assess bootstrap
edge stability, prior-knowledge sensitivity, and — critically — sensitivity to
including meteorology as exogenous nodes.

**3.3 Species grouping.** K-means on inter-species correlation profiles, with the
silhouette criterion and bootstrap co-assignment stability.

**3.4 Concentration-scenario analysis.** The linear response model's exact Pareto
frontier (standardized concentrations) is derived in closed form and compared to
the previously-published metaheuristic result; uncertainty by bootstrap refit.

## 4. Results

**4.1 Prediction (audit §C).** Leakage inflates skill: the random split gives
R² ≈ 0.41, but honest evaluation gives R² ≈ 0.25 (blocked temporal; 90% CI
0.22–0.28) and 0.30 (unseen stations; CI 0.19–0.40), falling to 0.22 under the
strict split. Previous-hour persistence reaches R² ≈ 0.79 but applies only to
temporal gap-filling. Weather-only and pollutant-only ablations give R² ≈ 0.14
and 0.13, versus 0.25 together — complementary and individually weak.

**4.2 Structure (audit §D).** One edge is bootstrap-stable and survives
meteorology inclusion: **NO → ozone, negative** (frequency 1.0, −0.138 ± 0.007;
−0.108 with weather), consistent with local titration. PM2.5 edges are stable in
the pollutant-only model but, once weather is included, temperature → PM2.5 and
humidity → ozone dominate — the pollutant-only graph was **confounded**. SO₂ edges
are unstable (frequency ≤ 0.5). The recovered order depends on the prior.

**4.3 Grouping (audit §E, §A2).** Silhouette is weak (0.26 raw; 0.39 in the
pipeline's imputed run). Core groups {NO, NO₂, PM10, PM2.5} and {O₃, SO₂} are
bootstrap-stable; on raw data CO flipped between clusters (co-assignment
0.72/0.28). This instability was an **outlier artefact**: after flagging 35
non-physical values, CO's correlations with the combustion family rise sharply
(e.g. CO–NO 0.14→0.42) and CO joins {CO, NO, NO₂, PM10, PM2.5} at co-assignment
1.0 (silhouette 0.36). The grouping is still a weak convenience partition, but a
physically coherent and now-stable one. (Caveat: CO and NO₂ are unit-indeterminate
per the units verification, so their grouping behaviour may partly reflect the
ppb/µg/m³ mix rather than chemistry; the stable {O₃, SO₂} vs combustion split does
not depend on CO.)

**4.4 Scenarios (audit §F).** The frontier is a short near-linear trade-off driven
almost entirely by NO; SO₂ and VOC are inert (VOC is not even fitted). The
published metaheuristic's 19 "optimal" policies are **all dominated** by the exact
frontier (mean PM2.5 gap 0.046, max 0.298 standardized). The frontier shifts under
refitting (CO coefficient especially), so its location is itself uncertain.

## 5. Discussion

The honest contribution is modest and methodological: (i) a correctly-evaluated
predictive baseline that beats trivial spatial baselines but not temporal
persistence; (ii) one stable, chemically-plausible association (NO–ozone
titration) reported as a hypothesis; (iii) a demonstration that a published
metaheuristic "optimization" was dominated by a closed-form solution; and (iv) a
cautionary account of how leakage, omitted confounders, unharmonised units and
pooling inflate apparent findings. Agreement between SHAP and DirectLiNGAM on the
NO sign is internal consistency, not independent validation.

## 6. Limitations

Units unharmonised (CO); weather modelled not observed; urban, non-representative
network; ~66% completeness with mixed missingness; VOC absent; a single pooled
*linear* contemporaneous model cannot represent regime-dependent (VOC- vs
NOx-limited) ozone chemistry; "interventions" act on standardized ambient
concentrations, not emissions; −2σ scenarios may be physically infeasible. None
of the analyses identify causal effects.

## 7. On the original title's claims

- **"Source apportionment"** — unsupported: no speciation, no uncertainties, no
  VOC, unharmonised units; K-means is exploratory grouping (audit §E).
- **"Causal … control optimization"** — unsupported: no identification strategy,
  hidden meteorological confounding, pooling destroys regimes, interventions act
  on concentrations not emissions, and the optimizer was dominated (audit §D, §F).
- **"Multi-pollutant"** — supported.

## 8. Conclusion

The pipeline runs, is reproducible, and the dataset is real; but its headline
scientific claims do not survive scrutiny. Reframed as an exploratory study with
leakage-safe evaluation, explicit uncertainty, and honest limitations, it is a
useful negative/cautionary contribution. As a causal source-apportionment and
control-optimization result, it is not.
