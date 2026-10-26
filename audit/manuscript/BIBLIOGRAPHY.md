# Bibliography (methods & data)

Primary references for the methods and data used — all canonical, real
publications. **Every identifier below (DOI / arXiv / URL / ISBN) was verified
against authoritative records (Crossref/publisher pages, JMLR, arXiv, DBLP) on
2026-10-26.** None are fabricated. JMLR and NeurIPS proceedings are open-access and
carry no DOI, so a stable URL / arXiv id is given instead. Re-confirm at final
submission in case a publisher reassigns a record.

## Causal discovery
- Shimizu, S., Hoyer, P. O., Hyvärinen, A., & Kerminen, A. (2006). A linear
  non-Gaussian acyclic model for causal discovery. *Journal of Machine Learning
  Research*, 7, 2003–2030. — URL: https://jmlr.org/papers/v7/shimizu06a.html
- Shimizu, S., Inazumi, T., Sogawa, Y., Hyvärinen, A., Kawahara, Y., Washio, T.,
  Hoyer, P. O., & Bollen, K. (2011). DirectLiNGAM: A direct method for learning a
  linear non-Gaussian structural equation model. *Journal of Machine Learning
  Research*, 12, 1225–1248. — URL: https://jmlr.org/papers/v12/shimizu11a.html
- Pearl, J. (2009). *Causality: Models, Reasoning, and Inference* (2nd ed.).
  Cambridge University Press. — DOI: 10.1017/CBO9780511803161

## Prediction, explanation, optimization
- Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system.
  *Proc. 22nd ACM SIGKDD (KDD '16)*, 785–794. — DOI: 10.1145/2939672.2939785
- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model
  predictions. *Advances in Neural Information Processing Systems*, 30 (NIPS 2017).
  — arXiv: 1705.07874
- Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist
  multiobjective genetic algorithm: NSGA-II. *IEEE Transactions on Evolutionary
  Computation*, 6(2), 182–197. — DOI: 10.1109/4235.996017
- Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M. (2019). Optuna: A
  next-generation hyperparameter optimization framework. *Proc. 25th ACM SIGKDD
  (KDD '19)*, 2623–2631. — DOI: 10.1145/3292500.3330701
- Zaharia, M., et al. (2016). Apache Spark: A unified engine for big data
  processing. *Communications of the ACM*, 59(11), 56–65. — DOI: 10.1145/2934664

## Evaluation methodology
- Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data
  mining: Formulation, detection, and avoidance. *ACM Transactions on Knowledge
  Discovery from Data*, 6(4), Article 15, pp. 15:1–15:21. — DOI: 10.1145/2382577.2382579
  *(Note: 10.1145/2020408.2020496 is the earlier 3-author KDD '11 version — do not use it for this TKDD article.)*

## Atmospheric chemistry & receptor modelling
- Seinfeld, J. H., & Pandis, S. N. (2016). *Atmospheric Chemistry and Physics:
  From Air Pollution to Climate Change* (3rd ed.). Wiley. — ISBN:
  978-1-118-94740-1. *(NO–O₃ titration; NOx–VOC-limited ozone regimes.)*
- Paatero, P., & Tapper, U. (1994). Positive matrix factorization: A non-negative
  factor model with optimal utilization of error estimates of data values.
  *Environmetrics*, 5(2), 111–126. — DOI: 10.1002/env.3170050203
  *(Why apportionment needs speciation + uncertainties.)*
- Grange, S. K., & Carslaw, D. C. (2019). Using meteorological normalisation to
  detect interventions in air quality time series. *Science of the Total
  Environment*, 653, 578–588. — DOI: 10.1016/j.scitotenv.2018.10.344
  *(Meteorological confounding of air-quality trends.)*

## Data sources
- OpenAQ air-quality data platform — https://openaq.org (API v3). *(Per-sensor unit
  metadata used for the units verification.)*
- Open-Meteo historical reanalysis — https://open-meteo.com .

---

### Verification status
All 12 identifiers were checked on 2026-10-26 and resolve to the stated papers:
each DOI via https://doi.org/<DOI>, the two JMLR URLs and the arXiv id directly,
the Kaufman record cross-checked against DBLP (TKDD 6(4), Article 15), and the
Seinfeld & Pandis ISBN against library catalogues. To re-verify at submission,
paste each DOI into https://doi.org/<DOI> and confirm title + authors + year.
