# Literature Review, Timelines, Gaps, Contributions & Novelty

Prepared against the Review-2 checklist: *introduction gaps, research paper on a
timeline (two timelines), the gaps we are solving, and our contributions & novelty*,
grounded in SCI / Q1 literature.

> **How to read the "two timelines":** the field our paper sits in has two parallel
> method threads. **Timeline A** traces *predictive & causal machine learning for air
> quality*; **Timeline B** traces *source apportionment & multi-objective policy
> optimization*. Our work sits at the end of both and connects them. Each timeline
> below lists, per milestone, the contribution and the limitation it leaves open; those
> open limitations are synthesized into the research gaps in §3.

---

## 1. Timeline A — Predictive & Causal ML for Air Quality

| Year | Milestone (author, venue) | Contribution | Limitation it leaves |
|------|---------------------------|--------------|----------------------|
| 2001 | Breiman, *Machine Learning* | Random forests: strong non-linear tabular prediction | Associational; no mechanism |
| 2006/11 | Shimizu et al., *JMLR* (LiNGAM / DirectLiNGAM) | Orient causal edges from non-Gaussianity | Assumes no hidden confounders, linearity |
| 2016 | Chen & Guestrin, *KDD* (XGBoost) | De-facto standard for tabular AQ prediction | Accuracy prioritised over interpretability |
| 2017 | Lundberg & Lee, *NeurIPS* (SHAP) | Principled feature attributions | Explains a model, not a mechanism |
| 2018 | Oliveira et al., *ECML-PKDD* | Dependence-aware (blocked) evaluation for spatio-temporal data | Not yet standard practice in AQ-ML |
| 2019 | Grange & Carslaw, *Sci. Total Environ.* | Random-forest meteorological normalisation | Meteorology must be removed before attribution |
| 2020 | Just et al., *Remote Sensing* | Shows random CV inflates PM2.5 skill vs spatial CV (RMSE 2.10 vs 3.11) | Leakage still widespread in practice |
| 2024 | Qi et al., *Environ. Res. Lett.* | Convergent cross-mapping for PM2.5 <-> O3 causality (China) | City/season-specific; not identification |
| 2024 | Rautela & Goyal, *Sci. Reports*; Malhotra et al., *J. Big Data* | Reviews of AI/ML for AQ (incl. India) | Confirm accuracy-first framing; few leakage-safe |
| 2025 | Wang et al., *Environ. Sci. Ecotechnol.* | XAI + causal inference for the 2022 ozone rebound | Correlational drivers, not interventions |
| 2026 | Ye et al., *Atmos. Chem. Phys.* | SHAP ozone-trend attribution; meteorology dominant | Flags SHAP instability under multicollinearity |
| **2026** | **This work** | **Leakage-safe India benchmark + causal-stability audit + identification gate** | — |

## 2. Timeline B — Source Apportionment & Multi-Objective Policy Optimization

| Year | Milestone (author, venue) | Contribution | Limitation it leaves |
|------|---------------------------|--------------|----------------------|
| 1994 | Paatero & Tapper, *Environmetrics* (PMF) | Receptor modelling with error weighting | Needs speciation + per-measurement uncertainties |
| 1999 | Zitzler & Thiele, *IEEE TEC* | Hypervolume for Pareto quality | Metric, not a guarantee of optimality |
| 1999 | Sillman, *Atmos. Environ.* | VOC- vs NOx-limited ozone regimes | Requires VOC observations to resolve |
| 2002 | Deb et al., *IEEE TEC* (NSGA-II) | Standard multi-objective evolutionary search | No guarantee vs exact fronts on simple surfaces |
| 2013 | Guttikunda & Calori, *Atmos. Environ.* | 1 km Delhi emission inventory | Bottom-up inventories incomplete/dated |
| 2015 | Pant et al., *Atmos. Environ.* | PMF PM2.5 source apportionment, Delhi | Site-specific; heavy data requirements |
| 2015 | Monks et al., *Atmos. Chem. Phys.* | Tropospheric ozone precursor review | Confirms VOC/NOx non-linearity |
| 2020 | Tobler et al., *Sci. Total Environ.* | Organic-aerosol PMF (ACSM), Delhi | Needs online speciation instruments |
| 2021 | Xu et al., *E3S Web Conf.* | NSGA-II joint cost–emission optimisation | Optimises a model, not validated interventions |
| 2025 | Lin et al. (EGUsphere); DN-PMF India (EGU25) | RF+SHAP ozone regimes via HCHO/NO2; dispersion-normalised PMF | Still require speciation/satellite proxies |
| **2026** | **This work** | **Analytic Pareto proof: 100% NSGA-II dominance; concentration–emission fallacy** | — |

---

## 3. Research Gaps (what the field leaves open — and we address)

Synthesised from the open limitations in both timelines:

- **G1 — Leakage-unaware evaluation.** Air-quality ML routinely reports random-split
  skill, which overstates generalisation on autocorrelated data
  (Just et al. 2020; Oliveira et al. 2018).
- **G2 — Correlation read as mechanism.** Feature importance / SHAP and discovered
  graphs are interpreted causally without confounding or identifiability tests; SHAP
  itself is unstable under multicollinearity (Ye et al. 2026).
- **G3 — Untested meteorological / boundary-layer confounding.** Causal graphs among
  pollutants rarely test whether edges survive meteorology (the dominant confounder).
- **G4 — Clustering mislabelled as source apportionment.** Correlation clustering is
  presented as apportionment despite lacking the speciation and uncertainties that PMF
  requires (Paatero & Tapper 1994).
- **G5 — Concentration–emission conflation.** "Policy optimisation" acts on ambient
  concentrations, not emissions, and metaheuristics are not benchmarked against exact /
  analytic Pareto fronts.
- **G6 — Weak provenance QC and no open India benchmark.** Measurement-unit provenance
  is seldom audited, and there is no open, leakage-safe, reproducible multi-pollutant
  benchmark for the Indian network.

## 4. Our Contributions & Novelty (mapped to the gaps)

| # | Contribution | Addresses | Novelty |
|---|--------------|-----------|---------|
| C1 | Leakage-safe, multi-protocol evaluation (random vs blocked-temporal vs leave-stations-out) with a full baseline ladder, on 204 Indian stations / 1.18M station-hours | G1 | First India-scale, leakage-safe multi-pollutant benchmark |
| C2 | Causal-discovery with bootstrap edge stability **and** an explicit meteorology-confounding test; only NO -> O3 survives | G2, G3 | Couples stability + confounding testing rather than reporting a raw graph |
| C3 | Formal distinction (and proof) that k-means correlation clustering is **not** PMF source apportionment | G4 | Makes the clustering/apportionment boundary explicit and testable |
| C4 | Analytical proof that the linear surrogate's Pareto front collapses to a 1-D segment; 100% of NSGA-II policies dominated (GD $=0.084$, HVE $=6.6\%$) | G5 | First closed-form optimality audit of a heuristic AQ optimiser |
| C5 | Formalised **concentration–emission fallacy** (negative-mass reductio) | G5 | Names a common category error in data-driven AQ policy |
| C6 | Authoritative unit-provenance audit (ppb/µg·m⁻³ mix) + open reproducible benchmark + a 4-part **scientific identification gate** | G2–G6 | A reusable gate for observational environmental AI |

**One-sentence novelty statement.** To our knowledge this is the first India-scale,
reproducibility-first audit that (i) proves analytically that the heuristic optimiser
is dominated on the fitted surrogate, (ii) couples causal-discovery stability with
meteorological-confounding tests, and (iii) formalises a scientific identification gate
for observational environmental AI.

---

## 5. SCI / Q1 Reading List

Priority papers to read, grouped by thread. Quartiles are indicative of the journal's
standing; **confirm the current quartile on Scimago (SJR) or JCR** before citing, as
rankings change yearly.

### Core methods (SCI / Q1)
1. Paatero & Tapper (1994), *Environmetrics* (Q1) — PMF foundation. DOI 10.1002/env.3170050203
2. Deb et al. (2002), *IEEE Trans. Evolutionary Computation* (Q1) — NSGA-II. DOI 10.1109/4235.996017
3. Shimizu et al. (2011), *J. Machine Learning Research* (Q1) — DirectLiNGAM.
4. Lundberg & Lee (2017), *NeurIPS* (A*; Lundberg et al. 2020, *Nature Machine Intelligence*, Q1) — SHAP.
5. Chen & Guestrin (2016), *KDD* (A*) — XGBoost.

### Leakage & evaluation (SCI / Q1)
6. Just et al. (2020), *Remote Sensing* (Q1) — spatial CV vs leakage in PM2.5 ML. **Read first for G1.**
7. Roberts et al. (2017), *Ecography* (Q1) — blocked CV for spatial/temporal data. DOI 10.1111/ecog.02881
8. Grange & Carslaw (2019), *Science of the Total Environment* (Q1) — meteorological normalisation. DOI 10.1016/j.scitotenv.2018.10.344

### Causal / explainable AQ (SCI / Q1) — recent
9. Qi et al. (2024), *Environmental Research Letters* (Q1) — convergent cross-mapping, PM2.5/ozone causality.
10. Wang et al. (2025), *Environmental Science and Ecotechnology* (Q1) — XAI + causal inference, ozone rebound.
11. Ye et al. (2026), *Atmospheric Chemistry and Physics* (Q1) — SHAP ozone attribution; multicollinearity caveat. **Read for G2.**
12. Rautela & Goyal (2024), *Scientific Reports* (Q1) — AI/ML for air pollution management in India.
13. Chernozhukov et al. (2018), *The Econometrics Journal* (Q1) — double/debiased ML (deconfounding).

### Atmospheric chemistry & India context (SCI / Q1)
14. Monks et al. (2015), *Atmospheric Chemistry and Physics* (Q1) — tropospheric ozone precursors.
15. Sillman (1999), *Atmospheric Environment* (Q1) — VOC- vs NOx-limited ozone. DOI 10.1016/S1352-2310(98)00345-8
16. Pant et al. (2015), *Atmospheric Environment* (Q1) — Delhi PM2.5 PMF apportionment.
17. Guttikunda & Calori (2013), *Atmospheric Environment* (Q1) — Delhi emission inventory. DOI 10.1016/j.atmosenv.2012.10.040
18. Seinfeld & Pandis (2016), *Atmospheric Chemistry and Physics* (Wiley, textbook) — reference chemistry.

### How to split the reading (5 students)
- **G1 / evaluation:** #6, #7, #8
- **Causal & XAI:** #9, #10, #11, #13
- **Apportionment / PMF:** #1, #16, #17
- **Optimisation:** #2, and one applied NSGA-II emission paper (e.g. Xu et al. 2021, *E3S*)
- **Chemistry / India context:** #14, #15, #18

Each reader: note the paper's method, its evaluation protocol, and which of our gaps
(G1–G6) it supports or challenges — that mapping is exactly what strengthens our
Introduction.
