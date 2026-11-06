# Cover Letter (template — fill in the brackets before submission)

[Date]

To the Editor,
[Journal name]

Dear Editor,

We submit our manuscript, **"Observational Response Surfaces versus Interventional
Policy: A Critical Audit of Causal Discovery and Multi-Objective Optimization Across
Indian Urban Air Quality Networks,"** for consideration as a [research article /
methods article / data \& benchmark paper] in [Journal name].

Data-driven "prediction → causal structure → policy optimization" pipelines are
increasingly applied to regulatory air-quality telemetry, often with strong causal and
policy claims. Our contribution is a rigorous, reproducible audit of one such complete
pipeline, built and run on a national-scale Indian dataset (204 continuous monitoring
stations; 1,180,551 station-hours; calendar year 2025). Rather than add another
optimistic result, we test what these data can and cannot support, and we report three
findings we believe are of broad methodological value:

1. **Spatio-temporal leakage is large and routinely hidden.** Held-out ozone skill
   falls from R² ≈ 0.41 under conventional random splitting to R² ≈ 0.22–0.30 under
   blocked-temporal and leave-stations-out protocols; pollutants add only ≈ +0.12 R²
   beyond meteorology. We show (sensitivity analysis) the conclusion is unchanged when
   the unit-indeterminate species are removed entirely.

2. **Linear structural discovery recovers one robust, chemically interpretable edge**
   (NO → O₃ titration) that survives bootstrap resampling and meteorological
   de-confounding, rather than a regional photochemical mechanism — a ceiling imposed
   by the structural absence of VOCs.

3. **We prove analytically that the fitted linear surrogate's Pareto frontier collapses
   to a one-dimensional segment**, against which 100% of the heuristic NSGA-II policies
   are dominated — a closed-form optimality check for a class of data-driven policy
   optimizers.

We also report an authoritative measurement-unit audit revealing a genuine ppb/µg·m⁻³
provenance defect in CO, NO₂ and SO₂, and we formalize a four-part "scientific
identification gate" for observational environmental AI. All code, the dataset, fixed
seeds, and the scripts that regenerate every number and figure are released for review.

We believe this work is a good fit for [Journal name] because [one sentence: honest
methods/benchmark contribution; reproducibility; relevance to the Indian air-quality and
environmental-informatics community]. The manuscript is original, is not under
consideration elsewhere, and all authors approve the submission. We declare no competing
interests.

Suggested reviewers (optional): [names / areas: air-quality ML, causal inference,
atmospheric chemistry].

Thank you for considering our submission.

Sincerely,
S. Krishiykeishav, Pratyush Amit Sharma, Shreerag Venugopalan Nair,
Jayshil Vinodbhai Prajapati, and Ryan Vinod
Vellore Institute of Technology (VIT), Vellore, India
[corresponding author e-mail]
