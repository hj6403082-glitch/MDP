# Manuscript — LaTeX source

**Observational Response Surfaces versus Interventional Policy: A Critical Audit of
Causal Discovery and Multi-Objective Optimization Across Indian Urban Air Quality
Networks**
Authors: Keishav, Pratyush, Shreerag, Jayshil, Ryan.

## Build
```bash
bash compile.sh      # or: make
```
Requires a TeX distribution (TeX Live / MiKTeX) with `latexmk` or `pdflatex`+`bibtex`.
No local TeX? Upload this folder to Overleaf and compile there (`main.tex` is the root).
Output: `main.pdf` (16 pp).

## Layout
```
main.tex              preamble, package loading, \input of sections, bibliography
references.bib        29 BibTeX entries (core 12 DOIs verified 2026-10-26)
sections/             00_abstract .. 06_conclusion
figures/              fig1_network_coverage, fig2_leakage_benchmark, fig3_causal_dag,
                      fig4_analytic_pareto, fig5_shap_importance, fig6_units_verification
Makefile, compile.sh  automated builds
```

## Where the numbers come from (all real, all reproducible)
Every figure in the manuscript is generated from the committed audit outputs; every
table value is produced by a script on the committed dataset:
- `audit/paper_support.py` — summary statistics, the Ridge and diurnal-seasonal
  baselines, and the Pareto generational-distance / hypervolume-error metrics.
- `audit/make_figures.py`, `audit/make_paper_figures.py` — all six figures.
- `audit/reports/*.csv`, `*.json` — the per-phase audit metrics cited in the text.

## Two honesty notes (deliberate deviations from the drafting brief)
1. **Predictive numbers are the audited ones.** The manuscript reports the project's
   real leakage-safe results: contemporaneous ozone R² ≈ 0.41 (leaky random split)
   → 0.25 (blocked temporal) / 0.30 (leave-stations-out), persistence ≈ 0.79. The
   placeholder figures in the original brief (0.88 → 0.54) are **not** our data and
   were not used.
2. **The CO unit issue is ppb vs µg/m³**, verified against the authoritative OpenAQ
   sensor metadata — not mg/m³ (an earlier value-based guess that the audit overturned).

## Figure note
`fig1_network_coverage` shows the coverage distribution, not a geographic map:
individual monitor coordinates are not retained in the public telemetry export, so a
spatial map cannot be produced honestly from these data (a documented limitation).
`fig5_shap_importance` is a global importance ranking; per-sample SHAP values were not
retained, so a beeswarm is not shown.
