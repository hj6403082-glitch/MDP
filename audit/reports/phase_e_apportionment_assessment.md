# Phase E — Source Apportionment & Chemical Validation Assessment

## Verdict

**The data cannot support physical source apportionment.** The "source
apportionment" claim must be removed. The K-means step is retained and relabelled
as an **exploratory grouping of co-varying species** (see `phase_e_grouping.py`
for its weak, partly-unstable structure).

## Why PMF / receptor modelling is not supportable here

Positive Matrix Factorization and related receptor models require inputs this
dataset does not have:

| Requirement for apportionment | Present in this dataset? |
|-------------------------------|--------------------------|
| **Speciated chemical composition** (e.g. PM2.5 elemental/organic/ionic species, VOC speciation) | **No** — only a handful of regulatory criteria pollutants |
| **Per-measurement uncertainties** (PMF weights residuals by them) | **No** — no uncertainty or detection-limit metadata |
| **VOCs** (essential for combustion/solvent/biogenic factors) | **No** — structurally absent from all 204 stations |
| **Harmonised units** | **No** — CO shows mixed mg/m³ vs µg/m³ (audit §7) |
| **Factor → source interpretation** (external markers, wind-sector/trajectory analysis) | **No** — no tracer species or trajectory data |

K-means on correlation profiles of 7 criteria pollutants groups species that
*co-vary*; co-variation reflects shared sources **and** shared meteorological
modulation (Phase D shows weather drives much of the covariance). It yields no
quantitative source contributions and is not apportionment.

## Local titration vs photochemical production (must be distinguished)

The one stable chemical signal is the **negative NO↔ozone association** (Phase D).
This is consistent with **local titration** (NO + O₃ → NO₂ + O₂), a loss process.
It must **not** be presented as evidence about **ozone production sensitivity**
(whether an airshed is NOx-limited or VOC-limited), which is the policy-relevant
question. Distinguishing them requires evidence this project lacks:

- **Speciated VOCs** (and their reactivity) to characterise the VOC/NOx ratio;
- **Photolysis / solar radiation / actinic flux** and temperature-resolved
  photochemistry;
- **Transport and mixing** (boundary-layer height, advection) to separate local
  chemistry from accumulation;
- or **chemical-transport-model perturbation experiments** (e.g. box/3-D model
  NOx and VOC sensitivity runs).

## On satellite indicators

Formaldehyde/NO₂ column ratios from satellites are sometimes used as a proxy for
NOx- vs VOC-limited regimes. They could be explored **only** with explicit
limitations (column vs surface, overpass-time sampling, cloud screening,
resolution) and would still be supporting evidence, not identification.

## On "validation"

Agreement between SHAP (on the XGBoost model) and DirectLiNGAM on the NO→ozone
sign is **internal consistency between two models fit to the same data**, not
independent causal validation. Agreement with a chemical-transport model, if
later performed, would be *supporting* evidence — still not proof of real-world
causal identification.
