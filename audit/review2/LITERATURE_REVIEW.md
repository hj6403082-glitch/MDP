# Literature Review, Timelines, Gaps, Contributions & Novelty

Prepared against the Review-2 checklist: *introduction gaps, research paper on a
timeline (two timelines), the gaps we are solving, and our contributions & novelty*,
grounded in SCI / Q1 literature.

> **Scope of the timelines:** per mam's instruction, the two timelines below show only
> the **latest work (past ~2 years, 2024–2026)** — not the older foundational papers.
> The field has two parallel recent threads: **Timeline A** = predictive & causal
> machine learning for air quality; **Timeline B** = source apportionment &
> multi-objective policy optimization. Our work sits at the end of both. (Foundational
> method papers are listed separately under §5 as background.)

---

## 1. Timeline A — Predictive & Causal ML for Air Quality (2024–2026)

| Year | Work (author, venue) | Contribution | Limitation it leaves |
|------|----------------------|--------------|----------------------|
| 2024 | Rautela & Goyal, *Scientific Reports* (Q1) | Convolutional autoencoder deriving PM2.5 across India | Accuracy-first; no causal/leakage analysis |
| 2024 | Malhotra et al., *Journal of Big Data* (Q1) | Systematic review of AI for air-pollution prediction | Confirms interpretability/evaluation gaps |
| 2024 | Qi et al., *Environ. Research Letters* (Q1) | Convergent cross-mapping for PM2.5 <-> O3 causality (China) | City/season-specific; not identification |
| 2025 | Wang et al., *Environ. Science & Ecotechnology* (Q1) | Causal forest + XAI for the 2022 ozone rebound (meteorology ~57%) | Observational; confounding only partly handled |
| 2025 | Utku et al., *Atmosphere* (Q2) | CNN-RNN hybrid PM2.5 forecasting (India + EU cities) | Random-style evaluation; no spatial transfer test |
| 2026 | Ye et al., *Atmos. Chem. Phys.* (Q1) | SHAP de-weathering of ozone trends (E. China) | Flags SHAP instability under multicollinearity |
| **2026** | **This work** | **Leakage-safe India benchmark + causal-stability audit + identification gate** | — |

## 2. Timeline B — Source Apportionment & Multi-Objective Optimization (2024–2026)

| Year | Work (author, venue) | Contribution | Limitation it leaves |
|------|----------------------|--------------|----------------------|
| 2024 | Faisal (IIT Delhi, thesis) | Double-PMF / tracer-conjugate PMF of PM2.5, Delhi | Needs organic+elemental speciation |
| 2024 | Lakra et al., *Atmos. Environ.* | PMF on composite PM2.5 (Lucknow 8, Kanpur 7 factors) | Site/season specific; heavy data needs |
| 2024 | Nationwide airshed study, *Air* (MDPI) | Residential cooking/power/industry ~60% of India PM2.5 | Inventory-based, not receptor at scale |
| 2025 | Pullokaran et al., *EGU25* (abstract) | Dispersion-normalised PMF across India | Conference abstract; speciation required |
| 2025 | Lin et al., *EGUsphere* (preprint) | RF + SHAP ozone-regime mapping via HCHO/NO2 | Needs satellite/VOC proxies; associative |
| **2026** | **This work** | **Analytic Pareto proof: 100% NSGA-II dominance; concentration–emission fallacy** | — |

> **Note on the optimization half of Timeline B:** rigorous, recent (2024–2025)
> *multi-objective optimization for air-quality policy* is scarce — the nearest applied
> work (e.g. a 2023 CNN-LSTM + multi-objective emission model over Xi'an stations) is
> already outside the two-year window and does not benchmark against an exact frontier.
> That scarcity is itself part of the gap our analytical Pareto result addresses.

---

## 3. Research Gaps (what the recent literature leaves open — and we address)

- **G1 — Leakage-unaware evaluation.** Recent AQ-ML (e.g. forecasting papers in §1)
  still report random-style skill on autocorrelated data, overstating generalisation.
- **G2 — Correlation read as mechanism.** SHAP/importance and discovered graphs are
  read causally; even 2026 work (Ye et al.) flags SHAP instability under
  multicollinearity, yet attribution is still treated as explanation.
- **G3 — Untested meteorological / boundary-layer confounding.** Causal graphs among
  pollutants rarely test whether edges survive meteorology (the dominant confounder);
  recent causal work (Wang et al. 2025) targets this but only partially.
- **G4 — Clustering mislabelled as source apportionment.** Correlation clustering is
  presented as apportionment despite lacking the speciation and uncertainties that PMF
  (and its 2024–25 dispersion-normalised variants) require.
- **G5 — Concentration–emission conflation.** "Policy optimisation" acts on ambient
  concentrations, not emissions, and metaheuristics are not benchmarked against exact /
  analytic Pareto fronts — a near-absent practice in the recent literature.
- **G6 — Weak provenance QC and no open India benchmark.** Measurement-unit provenance
  is seldom audited, and there is no open, leakage-safe, reproducible multi-pollutant
  benchmark for the Indian network.

## 4. Our Contributions & Novelty (mapped to the gaps)

| # | Contribution | Addresses | Novelty |
|---|--------------|-----------|---------|
| C1 | Leakage-safe, multi-protocol evaluation (random vs blocked-temporal vs leave-stations-out) with a full baseline ladder, on 204 Indian stations / 1.18M station-hours | G1 | First India-scale, leakage-safe multi-pollutant benchmark |
| C2 | Causal-discovery with bootstrap edge stability **and** an explicit meteorology-confounding test; only NO -> O3 survives | G2, G3 | Couples stability + confounding testing rather than reporting a raw graph |
| C3 | Formal distinction (and proof) that k-means correlation clustering is **not** PMF source apportionment | G4 | Makes the clustering/apportionment boundary explicit and testable |
| C4 | Analytical proof that the linear surrogate's Pareto front collapses to a 1-D segment; 100% of NSGA-II policies dominated (GD = 0.084, HVE = 6.6%) | G5 | First closed-form optimality audit of a heuristic AQ optimiser |
| C5 | Formalised **concentration–emission fallacy** (negative-mass reductio) | G5 | Names a common category error in data-driven AQ policy |
| C6 | Authoritative unit-provenance audit (ppb/µg·m⁻³ mix) + open reproducible benchmark + a 4-part **scientific identification gate** | G2–G6 | A reusable gate for observational environmental AI |

**One-sentence novelty statement.** To our knowledge this is the first India-scale,
reproducibility-first audit that (i) proves analytically that the heuristic optimiser
is dominated on the fitted surrogate, (ii) couples causal-discovery stability with
meteorological-confounding tests, and (iii) formalises a scientific identification gate
for observational environmental AI.

---

## 5. SCI / Q1 Reading List

**Confirm the current quartile on Scimago (SJR) or JCR before citing** — rankings
change yearly and by subject category.

### A. Recent, peer-reviewed SCI/Q1 (read these first — past ~2 years)
*DOIs verified 2026-10-31 (resolve each at https://doi.org/<DOI>); quartiles are
indicative — confirm on Scimago for the exact subject category.*
1. Rautela, K. S. & Goyal, M. K. (2024). *Transforming air pollution management in
   India with AI and machine learning technologies.* **Scientific Reports** 14, 20412.
   DOI 10.1038/s41598-024-71269-7. (Q1)
2. Malhotra, M., Walia, S., Lin, C.-C., Aulakh, I. K. & Agarwal, S. (2024).
   *A systematic scrutiny of artificial intelligence-based air pollution prediction
   techniques, challenges, and viable solutions.* **Journal of Big Data** 11, 142.
   DOI 10.1186/s40537-024-01002-8. (Q1)
3. Qi, L., Yin, J., Li, J. & Duan, X. (2024). *Detecting causal relationships between
   fine particles and ozone based on observations in four typical cities of China.*
   **Environmental Research Letters** 19 (Jan 2024). **DOI: confirm on IOPscience**
   (could not be auto-resolved here; paper confirmed to exist). (Q1) **Read for G2/G3.**
4. Wang, L., Chen, B. et al. (2025). *Causal-inference machine learning reveals the
   drivers of China's 2022 ozone rebound.* **Environmental Science and Ecotechnology**
   24, 100524. DOI 10.1016/j.ese.2025.100524. (Q1) **Read for G2/G3.**
5. Utku, A. et al. (2025). *Advancing Air Quality Monitoring: Deep Learning-Based
   CNN-RNN Hybrid Model for PM2.5 Forecasting.* **Atmosphere** 16(9), 1003.
   DOI 10.3390/atmos16091003. (Q2)
6. Ye, X., Zhang, L., Wang, X., Lu, N., Hickman, S., Luo, G. & Archibald, A. T. (2026).
   *Deciphering the impacts of meteorology on surface ozone variability in eastern
   China using explainable machine learning models.* **Atmospheric Chemistry and
   Physics** 26(9), 6377. DOI 10.5194/acp-26-6377-2026. (Q1) **Read for G2.**
7. Lakra, K., Shukla, T., Bhowmik, H. S. et al. (2024). *Comparative analysis of winter
   composite-PM2.5 in Central Indo-Gangetic Plain cities.* **Atmospheric Environment**
   338, 120827. DOI 10.1016/j.atmosenv.2024.120827. (Q1)

### B. Recent grey literature (very current; not yet peer-reviewed — cite with care)
8. Lin et al. (2025), *EGUsphere* preprint — RF+SHAP ozone-regime mapping (HCHO/NO2).
9. Pullokaran et al. (2025), *EGU25* abstract — dispersion-normalised PMF across India.
10. Faisal (2024), IIT Delhi thesis — double-PMF / tracer-conjugate PMF, Delhi.

### C. Foundational methods (background — cite for method definitions, not as "recent")
11. Paatero & Tapper (1994), *Environmetrics* (Q1) — PMF. DOI 10.1002/env.3170050203
12. Deb et al. (2002), *IEEE Trans. Evolutionary Computation* (Q1) — NSGA-II. DOI 10.1109/4235.996017
13. Shimizu et al. (2011), *J. Machine Learning Research* (Q1) — DirectLiNGAM.
14. Lundberg & Lee (2017), *NeurIPS*; Lundberg et al. (2020), *Nature Machine Intelligence* (Q1) — SHAP.
15. Just et al. (2020), *Remote Sensing* (Q1) — spatial CV vs leakage in PM2.5 ML. **Read for G1.**
16. Grange & Carslaw (2019), *Sci. Total Environment* (Q1) — meteorological normalisation.
17. Sillman (1999), *Atmospheric Environment* (Q1) — VOC- vs NOx-limited ozone.
18. Seinfeld & Pandis (2016), textbook (Wiley) — reference atmospheric chemistry.

### How to split the reading (5 students)
- **Member 1 — recent prediction/DL:** #1, #2, #5
- **Member 2 — recent causal & XAI:** #3, #4, #6, #8
- **Member 3 — recent apportionment/PMF:** #7, #9, #10, #11
- **Member 4 — leakage & evaluation:** #15, #16
- **Member 5 — optimization & chemistry:** #12, #17, and one recent applied optimization paper

Each reader: note the paper's method, its **evaluation protocol**, and which of our
gaps (G1–G6) it supports or challenges — that mapping is exactly what strengthens our
Introduction.
