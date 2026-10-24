# Publication Plan — From Here to a Real Paper

Honest, prioritized roadmap. Status markers: [x] done · [~] in progress · [ ] to do
· [YOU] needs the team (can't be automated). Based on
`audit/manuscript/READINESS.md`.

---

## Step 0 — Decide which paper (do this first, with mam)

| | **Path A — Open benchmark + honest analysis (RECOMMENDED)** | Path B — Original causal/apportionment paper |
|---|---|---|
| Claim | Open dataset + leakage-safe evaluation + honest baselines + cautionary findings | Causal source-apportionment + policy optimization |
| Feasible on our data? | **Yes** | **No** — needs speciation, VOCs, an intervention, emissions data we don't have |
| Effort | ~1–2 focused weeks (science mostly done) | Months + new data collection; may be infeasible as a student project |
| Venue fit | Workshop / conference / benchmark track | Atmospheric-science journal (very high bar) |

**Recommendation: Path A.** It makes our honesty a strength and is achievable now.
Everything below assumes Path A.

## The contribution, in one sentence

> An open, reproducible, **leakage-safe benchmark** for multi-pollutant air-quality
> ML over 204 Indian stations — with honest baselines others must beat, one stable
> NO–O₃ hypothesis, and a clear account of what these data can and cannot support.

---

## Checklist to submission

### A. Data & correctness
- [x] Pipeline runs end-to-end on real data (execution evidence)
- [x] Leakage-safe evaluation protocol (blocked-temporal, leave-stations-out, strict)
- [x] Honest baselines (mean, climatology, persistence) + bootstrap CIs
- [x] Code correctness guards (pytest), fixed seeds, reproducibility guide
- [ ] **[YOU] Verify measurement units** — the one *blocking* data gap. Needs your
      OpenAQ key: `export OPENAQ_API_KEY=...; python audit/fetch_units.py`, then
      reconcile against `audit/reports/unit_inference.csv`. Until done, cross-station
      CO magnitudes are not publication-grade.

### B. Analysis strengthening
- [x] Meteorology-normalized / incremental-value analysis (Phase C2)
- [x] Forecasting vs persistence, reported honestly (Phase C2)
- [x] Bootstrap edge stability + meteorology-confounding test (Phase D)
- [x] Exact-vs-metaheuristic Pareto dominance check (Phase B/F)
- [ ] (Optional) multi-step forecasting if forecasting becomes the headline

### C. Figures  — [x] drafted (`audit/reports/figures/`, via `audit/make_figures.py`)
- [x] Fig 1 — data coverage (per-station + per-pollutant)
- [x] Fig 2 — leakage: R² by evaluation protocol
- [x] Fig 3 — incremental value (weather vs pollutants vs time vs station-mean)
- [x] Fig 4 — bootstrap edge stability (NO→ozone highlighted)
- [x] Fig 5 — Pareto dominance (19 policies vs exact front)
- [ ] Polish to the chosen venue's figure style / sizing on submission

### D. Writing
- [x] Rough draft (`audit/review2/ROUGH_DRAFT.md`) — honest, narrowed
- [x] Related Work positioning the paper in the field
- [x] Significance / usefulness-to-the-field section
- [ ] Reframe title/abstract around the **benchmark** contribution (small edit)
- [ ] Tighten Limitations after units are verified
- [ ] **[YOU + me] Verify every citation's DOI/pages** (currently flagged
      "confirm before submission" in `BIBLIOGRAPHY.md`)

### E. Venue & formatting
- [ ] **[YOU + mam] Pick a venue.** Realistic options for a first paper:
  - Climate Change AI workshop (NeurIPS / ICLR) — fits honest applied work
  - A regional IEEE conference (indexed proceedings) — common for college projects
  - A datasets/benchmarks track — fits the resource framing
- [ ] Reformat the draft into that venue's LaTeX template (IEEE / Springer / etc.)
- [ ] Internal critical review pass (overclaim hunt, limitations, reproducibility)

### F. Submission
- [ ] **[YOU] Author list, affiliations, acknowledgements** (mam's call)
- [ ] Final proofread → submit → (then months of peer review, out of our hands)

---

## What's blocking vs. what's done

- **Done:** execution, evaluation, analysis, figures, full rough draft, pseudocode,
  tool justification, reproducibility. The *scientific* work is largely complete.
- **Only real blocker we can't do for you:** verifying units (needs your API key).
- **Team decisions:** which paper (Path A), which venue, author list.

## Realistic timeline
- Units + reframe + citations + venue formatting: **~1–2 focused weeks.**
- Peer review + revisions after that: **months**, and outside our control.

## For mam's next review, you can show
Execution ✅ · rough draft ✅ · pseudocode ✅ · tool justification ✅ · figures ✅ ·
significance ✅ · **and this concrete publication plan** with a single, clearly-named
blocking item (units) — which demonstrates you know exactly what "proper
publication" requires and how close you are.
