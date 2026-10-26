# Bibliography (methods & data)

Primary references for the methods and data used — all canonical, real
publications. **Every identifier below (DOI / arXiv / URL) is a draft to be
confirmed against the publisher record before submission.** They are given from
memory and are not machine-verified here; none are fabricated. Any that cannot be
confirmed should be corrected or removed, not guessed. JMLR and NeurIPS proceedings
are open-access and often carry no DOI, so a stable URL / arXiv id is given instead.

## Causal discovery
- Shimizu, S., Hoyer, P. O., Hyvärinen, A., & Kerminen, A. (2006). A linear
  non-Gaussian acyclic model for causal discovery. *Journal of Machine Learning
  Research*, 7, 2003–2030. — URL (confirm): https://jmlr.org/papers/v7/shimizu06a.html
- Shimizu, S., Inazumi, T., Sogawa, Y., Hyvärinen, A., Kawahara, Y., Washio, T.,
  Hoyer, P. O., & Bollen, K. (2011). DirectLiNGAM: A direct method for learning a
  linear non-Gaussian structural equation model. *Journal of Machine Learning
  Research*, 12, 1225–1248. — URL (confirm): https://jmlr.org/papers/v12/shimizu11a.html
- Pearl, J. (2009). *Causality: Models, Reasoning, and Inference* (2nd ed.).
  Cambridge University Press. — DOI (confirm): 10.1017/CBO9780511803161

## Prediction, explanation, optimization
- Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system.
  *Proc. 22nd ACM SIGKDD (KDD '16)*, 785–794. — DOI (confirm): 10.1145/2939672.2939785
- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model
  predictions. *Advances in Neural Information Processing Systems*, 30. — arXiv
  (confirm): 1705.07874
- Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist
  multiobjective genetic algorithm: NSGA-II. *IEEE Transactions on Evolutionary
  Computation*, 6(2), 182–197. — DOI (confirm): 10.1109/4235.996017
- Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M. (2019). Optuna: A
  next-generation hyperparameter optimization framework. *Proc. 25th ACM SIGKDD
  (KDD '19)*, 2623–2631. — DOI (confirm): 10.1145/3292500.3330701
- Zaharia, M., et al. (2016). Apache Spark: A unified engine for big data
  processing. *Communications of the ACM*, 59(11), 56–65. — DOI (confirm): 10.1145/2934664

## Evaluation methodology
- Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data
  mining: Formulation, detection, and avoidance. *ACM Transactions on Knowledge
  Discovery from Data*, 6(4), Article 15. — DOI (confirm): 10.1145/2382577.2382579

## Atmospheric chemistry & receptor modelling
- Seinfeld, J. H., & Pandis, S. N. (2016). *Atmospheric Chemistry and Physics:
  From Air Pollution to Climate Change* (3rd ed.). Wiley. — ISBN (confirm):
  978-1-118-94740-1. *(NO–O₃ titration; NOx–VOC-limited ozone regimes.)*
- Paatero, P., & Tapper, U. (1994). Positive matrix factorization: A non-negative
  factor model with optimal utilization of error estimates of data values.
  *Environmetrics*, 5(2), 111–126. — DOI (confirm): 10.1002/env.3170050203
  *(Why apportionment needs speciation + uncertainties.)*
- Grange, S. K., & Carslaw, D. C. (2019). Using meteorological normalisation to
  detect interventions in air quality time series. *Science of the Total
  Environment*, 653, 578–588. — DOI (confirm): 10.1016/j.scitotenv.2018.10.344
  *(Meteorological confounding of air-quality trends.)*

## Data sources
- OpenAQ air-quality data platform — https://openaq.org (API v3). *(Per-sensor unit
  metadata used for the units verification.)*
- Open-Meteo historical reanalysis — https://open-meteo.com .

---

### How to verify the DOIs quickly
Paste each DOI into https://doi.org/<DOI> — it should resolve to the exact paper.
For the JMLR/NeurIPS URLs, open the link and confirm title + authors + year. If any
link does not resolve to the stated paper, correct it from the publisher page or
Google Scholar before submission. Do not submit a reference you could not open.
