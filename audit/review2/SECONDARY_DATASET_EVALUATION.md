# Secondary Dataset — Evaluation & Decision

A second dataset (`historical_air_quality_100_cities.parquet`, provided by a
collaborator) was evaluated for inclusion. **Decision: not used in this study;
retained as possible future work.** Rationale below.

## What it is

| Property | Value |
|---|---|
| Coverage | 100 cities **worldwide** (many Indian + Amsterdam, Athens, Bangkok, Berlin, Boston, Cairo, Chicago, …) |
| Period | 2021-01-01 → 2025-12-31 (5 years), 3-hourly |
| Rows | 1,460,800 (14,608 per city, perfectly regular, **zero missing**) |
| Variables | PM2.5, PM10 (µg/m³) + temperature, humidity, wind; lat/lon + `cam_lat/lon` |
| Provenance | **Modelled** — CAMS (Copernicus Atmosphere Monitoring Service) reanalysis via the Open-Meteo air-quality API (confirmed with the provider); the `cam_*` grid coordinates and gap-free regularity are the tell. |

## Why it is not used in this paper

1. **Modelled, not measured.** This study's contribution is an analysis of *real
   regulatory measurements* (OpenAQ). Model output cannot be pooled with
   measurements as if comparable, and model-vs-model agreement is not validation.
2. **Only PM2.5/PM10.** The core analyses (ozone prediction, the NO–O₃ association,
   multi-pollutant structure) require the reactive gases, which this file lacks.
3. **Global scope.** 100 mixed world cities do not match the India-focused,
   measurement-based framing.

Using it would weaken, not strengthen, the paper's honesty and scope.

## Why it is worth keeping

It has what the primary dataset lacked — explicit units (µg/m³), coordinates, five
years, and complete coverage. That makes it a clean seed for a **separate** future
study, e.g. a multi-year, multi-city **PM2.5/PM10 spatiotemporal forecasting**
benchmark — provided every use is clearly labelled as modelled CAMS data, never
presented as measurements.

## One-line summary (for the review)

> We evaluated a second 5-year, 100-city dataset but found it is modelled (CAMS
> reanalysis) and PM-only, so it does not fit our measurement-based multi-pollutant
> study; we keep it as a candidate for a separate PM-forecasting follow-up.
