# Significance — How This Project Is Useful to the Field

This answers the Review 1 point directly: *the thing we are making should be
helpful / come in use to the research area that the papers we read are on.* Below,
for each research area those papers belong to, is **what our project contributes to
that area** and **who it helps**. Everything here is backed by the committed code
and the audit (`audit/reports/`), so each claim of usefulness is itself evidenced.

The honest headline: our strongest contributions are a **reusable dataset +
pipeline**, a **leakage-safe evaluation recipe**, and a **cautionary map of the
traps** in this kind of study. A negative/methodological result that stops other
researchers from overclaiming is a real contribution to the area — not a gap.

---

## Area 1 — Air-quality prediction & forecasting with ML

**Papers in this area ask:** can we predict pollutant levels from other pollutants
and weather, and how well?

**What we add / who it helps:**
- A **reproducible benchmark** on a real 204-station Indian dataset (≈1.18M
  station-hours) that anyone in the area can reuse, with fixed seeds and splits.
- An **honest skill ceiling**: contemporaneous ozone R² ≈ 0.25–0.30 held-out, and
  pollutants add only ≈ +0.12 beyond weather. This tells other groups *what good
  actually looks like* on this data, so they don't chase inflated random-split
  numbers (Phase C / C2).
- A practical note for **monitoring-network operators**: persistence is a hard
  baseline for temporal gap-filling (R² ≈ 0.8), so model value lies in *spatial*
  gap-filling and multi-step forecasting, not next-hour nowcasting.

## Area 2 — Causal inference / causal discovery in environmental science

**Papers in this area ask:** can we recover *directional* relationships (not just
correlations) among pollutants from observational data?

**What we add / who it helps:**
- A **worked, honest template** for applying DirectLiNGAM with the diagnostics most
  applied papers skip: bootstrap edge stability **and** a meteorology-confounding
  test. Other researchers can lift this protocol directly.
- A concrete, **testable hypothesis** for atmospheric chemists: a stable negative
  NO → O₃ association consistent with local titration (survives weather) — a lead
  worth following with a designed study.
- A clear **requirements list** for anyone wanting a *causal* claim here: an
  identification strategy (natural experiment / policy discontinuity) and measured
  confounders. This saves the field effort by naming what's missing (Phase D).

## Area 3 — Source apportionment / receptor modelling

**Papers in this area ask:** which sources contribute how much to measured
pollution (e.g. PMF, CMB)?

**What we add / who it helps:**
- A **precise statement of data requirements** — chemical speciation,
  per-measurement uncertainties, and VOCs — that regulatory ML datasets like ours
  lack. This is directly useful to **data providers and monitoring agencies**
  deciding what to measure so their data *can* support apportionment.
- Evidence that **K-means grouping is not apportionment**, with the silhouette /
  co-assignment numbers to prove it (Phase E) — a caution that stops the common
  misread of clustering as source attribution.

## Area 4 — Multi-objective optimization for environmental policy

**Papers in this area ask:** how to trade off reductions across pollutants/costs
(often with NSGA-II or similar metaheuristics)?

**What we add / who it helps:**
- A reusable **sanity check**: when the response model is linear, the exact Pareto
  front is closed-form — and in our case it **dominated all 19 metaheuristic
  "optimal" policies** (Phase B/F). The lesson for the area: *always compare your
  metaheuristic against an exact or analytic baseline when one exists.*
- A caution for **policy modellers**: optimizing over *ambient concentrations* is
  not the same as optimizing *emissions*; the mapping must be validated first.

## Area 5 — Explainable AI (XAI) in environmental applications

**Papers in this area ask:** can SHAP/feature attributions explain and even
"validate" model behaviour?

**What we add / who it helps:**
- A clear demonstration that **SHAP agreeing with a causal-discovery result is
  internal consistency, not independent validation** — a precise caveat the XAI
  community can cite when reviewing such claims.

## Area 6 — Reproducibility & open data in environmental monitoring

**Papers in this area ask:** are results reproducible, and is the data/code open?

**What we add / who it helps:**
- A fully **open, versioned pipeline + dataset + audit** (branch
  `review/scientific-audit`, `RUNBOOK.md`) that runs offline with one command set —
  a ready template for **students and reviewers** to reproduce and extend.
- A documented **leakage-safe evaluation recipe** (blocked-temporal,
  leave-stations-out, station-block bootstrap) reusable by any air-quality ML study.

---

## One-paragraph version (for the review)

Our project is useful to the air-quality / environmental-AI research area in three
concrete ways: (1) it contributes a **real, open, reproducible dataset and
pipeline** others can build on; (2) it provides a **leakage-safe evaluation recipe
and a set of diagnostics** (bootstrap edge stability, meteorology-confounding
tests, exact-vs-metaheuristic checks) that this field often omits; and (3) it
delivers an **honest, evidence-backed account of what these data can and cannot
support**, including a testable NO–O₃ hypothesis and a clear list of what causal
source-apportionment would require. In a field prone to overclaiming from imperfect
regulatory data, a careful cautionary study is a genuine service to the area.
