# Publication-Readiness Assessment

**One-line verdict:** the project is **not publication-ready** as a causal
source-apportionment / control-optimization paper. Reframed as an honest
exploratory + methodological-cautionary study, it is a plausible short paper or
workshop contribution after the prioritized work below.

## Readiness by dimension

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Software correctness** | Good | Key bugs fixed (sampler, phantom VOC, scalers) with tests; audit scripts reproducible. |
| **Predictive validity** | Partial | Honest held-out R² ≈ 0.25–0.30 established; modest, and beaten by persistence for gap-filling. |
| **Causal identification** | Not met | No identification strategy; confounding and pooling; explicitly reframed as exploratory. |
| **Atmospheric plausibility** | Partial | NO–ozone titration association is plausible and stable; no mechanism proven; apportionment unsupported. |
| **Policy applicability** | Not met | Scenarios are standardized concentrations, not emissions; no benefit interpretation. |
| **Novelty / journal suitability** | Low–moderate | Methodologically careful negative result; not a novel atmospheric or causal finding. |
| **Reproducibility** | Good | Code, data, seeds, manifests, audit scripts committed. |

## What each stronger claim would require (prioritized)

1. **Unit harmonization (blocking).** Re-collect OpenAQ v3 retaining per-sensor
   units, detection limits, provider, and QA flags; convert to common units;
   re-run everything. Until then cross-station magnitudes (esp. CO) are unreliable.
   *(Free but a large re-download; flagged, not performed — needs approval.)*
2. **Prediction, done right.** Keep the leakage-safe protocol; add a meteorology-
   normalized target, hour-of-day/station fixed effects, and a proper forecasting
   variant if forecasting is the goal; report against persistence honestly.
3. **If a causal question is desired.** Identify a documented intervention / natural
   experiment (policy, fuel-standard change, lockdown) with pre/post and controls,
   use emissions/activity data as the treatment, normalize for meteorology, and
   pre-register an estimand with overlap and unmeasured-confounding sensitivity.
   Without this, keep structure discovery exploratory.
4. **If apportionment is desired.** Obtain speciated composition (PM species,
   VOCs) with measurement uncertainties and run a validated receptor model (PMF)
   with factor stability and external source interpretation. Not possible with the
   current variables.
5. **Scenario analysis.** Keep it in standardized space with full uncertainty
   (measurement + imputation + structural), or drop it; never translate to emission
   percentages or benefits without a validated emissions→concentration model.

## Recommended path to *a* defensible paper

Write the **exploratory + cautionary** version (see `MANUSCRIPT.md`): a careful
case study of what pooled regulatory air-quality data can and cannot support,
with the leakage, confounding, unit and optimization-dominance results as the
contribution. This is honest, reproducible, and achievable now; the causal /
apportionment / policy paper is not, and should not be attempted on these data.

## Title recommendation

Drop *causal*, *source apportionment*, and *control optimization*. Use one of the
options in `MANUSCRIPT.md`.
