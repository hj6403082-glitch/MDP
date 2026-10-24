# Phase D — Scientific Identification Gate

Purpose: decide, *before* any policy-effect claim, whether the data and design
support an **identifiable causal question**. Conclusion first, then the checklist.

## Verdict

**A credible causal identification of pollution-control effects is NOT available
from this dataset and design.** The project should therefore:
- retain DirectLiNGAM as **exploratory structure discovery** (hypothesis
  generation under stated assumptions), with the stability/sensitivity evidence
  from `phase_d_causal_stability.py`; and
- reframe the optimization as **model-based scenario analysis in standardized
  ambient-concentration space** (Phase F), not emissions policy.

## The causal checklist

| Element | What a causal policy claim needs | What the project has |
|---------|----------------------------------|----------------------|
| **Treatment** | A manipulable intervention (e.g. a dated emission-control policy, a sectoral activity change) | A *do*-operation that **sets standardized ambient concentrations** of NO/NO₂/CO — not a real, manipulable intervention and not emissions |
| **Outcome & averaging period** | Defined (e.g. seasonal mean MDA8 ozone) | Hourly standardized ozone/PM2.5; averaging period undefined |
| **Unit of analysis / target population** | Stated (stations? people? grid cells? which population?) | Undefined; pooled station-hours in the urban OpenAQ network |
| **Intervention horizon** | Short vs long run specified | None |
| **Estimand** | e.g. ATE / dose-response of an emissions change | None; the model returns a conditional association propagated through a linear SEM |
| **Confounders** | Meteorology, emissions, transport, chemistry, time, space adjusted for | **Meteorology, station, season and time are excluded** from the fitted graph; Phase D shows weather materially changes the structure |
| **Mediators / colliders** | Identified to avoid mis-adjustment | Not analysed; pooled contemporaneous fit risks conditioning on mediators |
| **Overlap / support** | Treatment varies with common support across confounder strata | Not assessed; −2σ scenarios extrapolate beyond observed support and can imply negative concentrations |
| **Spatial spillovers / interference** | Addressed (pollution transports across units) | Ignored; SUTVA is implausible for air quality |
| **Identification assumptions** | Stated and defended | DirectLiNGAM assumes linearity, non-Gaussian independent errors, acyclicity and **no hidden common causes** — none defended; the last is violated by omitted weather/emissions |

## Why the specific design fails

1. **Concentrations, not emissions.** The *do*-operator sets ambient
   concentrations. Ambient concentration is itself an outcome of emissions +
   meteorology + chemistry + transport. Intervening on it is not a policy lever,
   and the scalers needed even to express it in physical units were not persisted
   (now fixed in Phase B, but the interpretation gap remains).
2. **Omitted common causes.** Temperature, humidity, wind, boundary-layer height
   and emissions drive several pollutants jointly. Phase D confirms the structure
   shifts when weather is added (e.g. temperature→PM2.5 becomes the dominant edge;
   NO→ozone weakens from −0.138 to −0.108). Hidden-confounding is present, so the
   no-hidden-common-cause assumption fails.
3. **Pooling destroys regime structure.** Ozone chemistry is non-linear and
   regime-dependent (VOC- vs NOx-limited). A single pooled *linear* model cannot
   represent this; its coefficients are population-averaged associations.
4. **No overlap / extrapolation.** Blanket −2σ bounds reach concentration regions
   that may be unobserved or physically impossible.

## What *is* defensible

- **One stable associational signal:** NO↔ozone is negatively associated and the
  edge is bootstrap-stable (frequency 1.0, coef −0.138±0.007) and survives weather
  inclusion. This is **consistent with local ozone titration by NO**, reported as
  an association/hypothesis, not an identified effect, and explicitly distinct
  from photochemical ozone *production* sensitivity (which needs speciated VOCs,
  photolysis/radiation and transport information to assess).
- **Scenario analysis:** propagating hypothetical standardized concentration
  settings through the fitted linear model, clearly labelled as model-based
  what-ifs with uncertainty (Phase F), is a legitimate exploratory exercise.

## What a future causal study would require

- A documented, dated intervention or natural experiment (policy, lockdown,
  fuel/standard change) with pre/post and control units.
- Emissions or activity data (the actual treatment), not ambient concentrations.
- Meteorological normalisation / adjustment and explicit spatial-transport
  modelling.
- A pre-registered estimand, overlap diagnostics, and sensitivity analysis for
  unmeasured confounding. Cross-fitting (e.g. EconML) would not remove the
  hidden-confounding or interference problems here.
