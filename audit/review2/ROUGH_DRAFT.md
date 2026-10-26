# Rough Draft — Research Paper

> **Status:** rough draft for Review 2. Every number is produced by the committed
> code on the real dataset (see `audit/reports/`). Framing is deliberately honest
> and narrowed — see §VIII Limitations and the claim-to-evidence table. Citations
> are real, foundational works (see `audit/manuscript/BIBLIOGRAPHY.md`); DOIs are
> to be confirmed against publisher records before any submission.

---

## Title

**An Open, Leakage-Safe Benchmark for Multi-Pollutant Air-Quality Machine Learning over 204 Indian Monitoring Stations**

*Alternative title: What Can and Cannot Be Learned from Pooled Regulatory Air-Quality Data — A Leakage-Safe Machine-Learning Case Study over 204 Indian Monitoring Stations.*

> We moved away from the original title *"Causal Machine Learning for Multi-Pollutant
> Source Apportionment and Control Optimization"* because our own evaluation could
> not support the words *causal*, *source apportionment*, or *control optimization*
> (§VIII). We reframe the work as a **benchmark and resource contribution**: an open
> dataset, a leakage-safe evaluation protocol, and honest baselines others can build
> on. Narrowing the claim rather than overstating it is itself the contribution.

**Keywords:** air quality; open benchmark; machine learning; data leakage;
causal discovery; DirectLiNGAM; XGBoost; multi-objective optimization;
reproducibility; India.

---

## Abstract

We release an **open benchmark** for multi-pollutant air-quality machine learning:
one year (2025) of hourly observations from 204 Indian monitoring stations (OpenAQ)
merged with co-located modelled meteorology (Open-Meteo) — about 1.18 million
station-hours — together with a **leakage-safe evaluation protocol** and honest
baselines. Measurement units are **verified against the authoritative OpenAQ sensor
metadata**: NO, ozone, PM2.5 and PM10 are unit-consistent, while CO, NO₂ and SO₂
carry duplicate ppb/µg/m³ sensors and are treated as unit-indeterminate. Under
leakage-safe evaluation, a gradient-boosted model estimates contemporaneous ozone
with held-out R² ≈ 0.25 (blocked-temporal) to 0.30 (unseen stations), well below the
0.41–0.43 from a leaky random split; pollutants add only ≈ +0.12 R² *beyond weather*,
and a one-hour-ahead forecast beats a persistence baseline by only +0.05. Exploratory
causal-structure discovery (DirectLiNGAM) recovers a single bootstrap-stable
association consistent with local NO–O₃ titration, but the wider graph is confounded
by omitted meteorology and is not causally identified. K-means groups co-varying
species only weakly (silhouette 0.26–0.39) and is not source apportionment. A linear
response model admits a closed-form scenario frontier; a published metaheuristic
"optimization" returned only dominated points. We conclude that the engineering is
sound and reproducible, but that causal, apportionment and policy claims are
unsupported by these data, and we specify the additional evidence each would require.

---

## I. Introduction

Urban air quality in India is a major public-health problem, and open monitoring
data invite machine-learning analysis. A tempting narrative runs *prediction →
causal structure → policy optimization*. Many applied papers present each link as
established. We instead **test** that narrative critically on a large but imperfect
regulatory dataset and report, with uncertainty, where it holds and where it breaks.

**Contributions.** (1) An **open, reproducible dataset + PySpark/Dataproc pipeline**
over 204 stations, with units verified against authoritative sensor metadata.
(2) A **leakage-safe evaluation protocol** and honest baselines others must beat,
showing how random splitting inflates apparent skill. (3) One stable,
chemically-plausible association (NO–O₃) reported as a hypothesis, not an identified
effect. (4) A demonstration that a published metaheuristic "optimizer" was dominated
by a closed-form solution. (5) An explicit account of the evidence each stronger
claim would need.

**Significance — who this helps.** The work is useful to the air-quality and
environmental-AI community in three concrete ways: a real, open, reproducible
**dataset and pipeline** others can build on; a reusable **leakage-safe evaluation
recipe and diagnostic set** (bootstrap edge stability, meteorology-confounding
tests, exact-vs-metaheuristic checks) that this field often omits; and an honest,
evidence-backed **account of what imperfect regulatory data can and cannot support**,
including a testable NO–O₃ hypothesis and a requirements list for causal source
apportionment. A full area-by-area breakdown is in `audit/review2/SIGNIFICANCE.md`.

## II. Related Work (positioning)

Our methods are standard; our contribution is their *honest application and
evaluation*. We position against five strands:

- **Tabular prediction / boosting.** XGBoost [Chen & Guestrin, 2016] is the
  canonical tabular regressor; we use it but subject it to leakage-safe evaluation
  rather than reporting a single random-split R².
- **Data leakage.** [Kaufman et al., 2012] formalizes leakage; air-quality ML
  frequently random-splits autocorrelated time series. Our blocked-temporal and
  leave-stations-out protocol is the direct remedy.
- **Causal discovery.** DirectLiNGAM [Shimizu et al., 2006; 2011] and Pearl's
  identification framework [Pearl, 2009] let us *orient* edges; we add bootstrap
  stability and a meteorology-confounding test, which most applied uses omit.
- **Source apportionment.** Receptor models, esp. PMF [Paatero & Tapper, 1994],
  require chemical speciation and per-measurement uncertainties. Our data have
  neither, so we explicitly decline the apportionment claim.
- **Meteorological normalization.** [Grange & Carslaw, 2019] show weather must be
  removed before attributing air-quality changes — motivating our weather-vs-
  pollutant decomposition and our refusal to read the raw graph as mechanism.

**How our paper "matches" the literature.** It uses the same methods as published
causal-ML air-quality studies, but reports the diagnostics those studies usually
skip (leakage-safe splits, bootstrap edge stability, confounding tests, an exact
optimality check). The comparison table in `audit/manuscript/ORIGINAL_VS_CORRECTED.md`
maps each original claim to its corrected, evidence-backed version.

## III. Data

Hourly CO, NO, NO₂, O₃, PM10, PM2.5 and SO₂ for 204 Indian stations with 2025 data
(OpenAQ v3), each merged with hourly Open-Meteo reanalysis (temperature, relative
humidity, wind speed, surface pressure) at the nearest ~0.1° grid cell. Scale:
**1,180,551 station-hours**, ≈ 66% of a full 204 × 8,760 grid; 37 stations < 50%
within-year coverage. **Units were verified against the authoritative OpenAQ
per-sensor metadata:** NO (ppb), O₃, PM2.5 and PM10 (µg/m³) are unit-consistent,
whereas CO, NO₂ and SO₂ carry duplicate ppb *and* µg/m³ sensors at almost every
station (e.g. CO at 183/198) with no per-row provenance, so their stored unit is
**indeterminate**; we therefore restrict quantitative cross-station use to the
unit-consistent pollutants (Fig. 6). Further caveats: 35 non-physical outliers and
saturation caps exist; weather is modelled; the network is urban and Delhi-NCR-heavy
(not nationally representative); VOCs are structurally absent.

## IV. Methodology

Full algorithmic detail is in `audit/review2/PSEUDOCODE.md`; the tool rationale is
in `SOFTWARE_STACK.md`. Four analyses:

1. **Predictive baseline** — XGBoost estimates same-hour ozone from pollutants +
   weather. Evaluated with leaky random (contrast only), blocked-temporal,
   leave-stations-out, and strict splits; preprocessing fit on train only;
   hyper-parameters fixed a priori; baselines = mean, climatology, persistence;
   uncertainty via station-block bootstrap.
2. **Structure discovery** — DirectLiNGAM on standardized pollutants with a prior
   forbidding secondary→primary edges; bootstrap stability + meteorology-inclusion
   sensitivity.
3. **Species grouping** — K-means on inter-species correlation profiles; silhouette
   model-selection + bootstrap co-assignment.
4. **Scenario analysis** — the linear model's exact Pareto frontier derived in
   closed form and compared to the published metaheuristic result.

## V. Experimental Setup & Execution

- **Pipeline execution.** The full three-phase pipeline runs end-to-end on Google
  Cloud Dataproc (custom Docker runtime) and in Cloud Shell; `main.py --phases all`
  completes with every phase reporting `all_ok` on the real 204-station data.
- **Audit execution.** Eight self-contained scripts (`audit/*.py`) regenerate every
  number offline with `SEED=42` (Track A of `RUNBOOK.md`); `pytest` guards pass.
- **Compute.** Prediction and causal-stability scripts run in ≈ 2 min each on a
  single machine; bootstrap counts are CLI flags.

## VI. Results

*Figures (in `audit/reports/figures/`, regenerable via `audit/make_figures.py`):
Fig. 1 data coverage; Fig. 2 R² by evaluation protocol (leakage); Fig. 3 incremental
value of pollutants beyond weather; Fig. 4 bootstrap edge stability; Fig. 5 Pareto
dominance of the 19 saved policies; Fig. 6 authoritative units verification.*

**A. Prediction.** Leakage inflates skill: random split R² ≈ 0.41, but honest
evaluation gives R² ≈ 0.25 (blocked-temporal; 90% CI 0.22–0.28) and 0.30 (unseen
stations; CI 0.19–0.40), down to 0.22 strict. Decomposition (Phase C2): weather
alone R² = 0.14, pollutants add **+0.12** (to 0.26), time harmonics → 0.34; the
0.41 is only recovered by a train-only per-station mean, which is **site
memorisation**, not generalisation. Persistence reaches R² ≈ 0.79–0.81 for
gap-filling; a true t+1h forecast beats persistence by only **+0.05** (0.81 → 0.87).

**B. Structure.** One edge is bootstrap-stable and survives meteorology: **NO → O₃,
negative** (frequency 1.0, −0.138 ± 0.007; −0.108 with weather) — local titration.
PM2.5 edges collapse once weather enters (temp → PM2.5, humidity → O₃ dominate):
the pollutant-only graph was **confounded**. SO₂ edges are unstable (freq ≤ 0.5).

**C. Grouping.** Silhouette weak (0.26 raw, 0.39 imputed). Core groups {NO, NO₂,
PM10, PM2.5} and {O₃, SO₂} are stable; CO's instability was an **outlier artefact** —
after flagging 35 values, CO–NO rises 0.14 → 0.42 and CO joins the combustion group
at co-assignment 1.0. Still a weak convenience partition, now physically coherent
(caveat: CO and NO₂ are unit-indeterminate, so their grouping may partly reflect the
ppb/µg/m³ mix; the stable {O₃, SO₂} vs combustion split does not depend on CO).

**D. Scenarios.** The frontier is a short near-linear trade-off driven almost
entirely by NO. The published metaheuristic's **19 "optimal" policies are all
dominated** by the exact frontier (mean PM2.5 gap 0.046, max 0.298 standardized).

## VII. Discussion

The honest contribution is modest and methodological: a correctly-evaluated
predictive baseline that beats spatial baselines but not temporal persistence; one
stable, plausible association reported as a hypothesis; a demonstration that a
published "optimization" was dominated by a closed-form solution; and a cautionary
account of how leakage, omitted confounders, unharmonised units and pooling inflate
apparent findings. SHAP–DirectLiNGAM agreement on the NO sign is internal
consistency, **not** independent validation.

## VIII. Limitations

Units unharmonised (CO); weather modelled not observed; urban non-representative
network; ≈ 66% completeness with mixed missingness; VOC absent; a single pooled
*linear* contemporaneous model cannot represent regime-dependent (VOC- vs
NOx-limited) ozone chemistry; "interventions" act on standardized ambient
concentrations, not emissions. **None of the analyses identify causal effects.**

What each stronger claim would require: *causal* → an identification strategy
(natural experiment / policy discontinuity) and measured confounders; *source
apportionment* → chemical speciation + per-measurement uncertainties + VOCs and a
receptor model (PMF); *control optimization* → a validated emissions→concentration
model, not a fit to ambient levels.

## IX. Conclusion & Future Work

The pipeline runs, is reproducible, and the dataset is real; but its original
headline claims do not survive scrutiny. Reframed as an exploratory study with
leakage-safe evaluation, explicit uncertainty, and honest limitations, it is a
useful cautionary contribution. Future work: verify units against OpenAQ sensor
metadata; obtain speciated data for apportionment; seek a genuine intervention for
causal identification; and extend the predictive model to multi-step forecasting.

## References

See `audit/manuscript/BIBLIOGRAPHY.md` (Shimizu et al. 2006/2011; Pearl 2009; Chen &
Guestrin 2016; Lundberg & Lee 2017; Deb et al. 2002; Akiba et al. 2019; Zaharia et
al. 2016; Kaufman et al. 2012; Seinfeld & Pandis 2016; Paatero & Tapper 1994; Grange
& Carslaw 2019; OpenAQ; Open-Meteo). **DOIs/identifiers are drafted there** (resolve
each at doi.org); confirm every one before submission.
