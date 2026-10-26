# Review 2 — Deliverables

Built in response to Review 1 feedback: *be relevant to the research literature,
show execution and a rough draft, add pseudocode, and justify every tool.*

| Deliverable | File | Covers the feedback point |
|-------------|------|---------------------------|
| **Rough draft** (honest, narrowed) | `ROUGH_DRAFT.md` | "next review wants a rough draft" + "match / be relevant to the research paper" (via the Related Work section) |
| **Pseudocode** for every stage | `PSEUDOCODE.md` | "we need to write pseudo code too" |
| **Software & tool justification** | `SOFTWARE_STACK.md` | "explain importance of each code and software, why we are using it" |
| **Execution evidence** | §V of `ROUGH_DRAFT.md` + `audit/reports/` | "next review wants execution" |
| **Usefulness to the field** | `SIGNIFICANCE.md` | "it should be helpful / come in use to the area the research papers are on" |
| **Publication roadmap** | `PUBLICATION_PLAN.md` | the concrete path from here to a submitted paper, with the one blocking item named |
| **Figures** | `../reports/figures/` (via `../make_figures.py`) | 6 publication figures regenerable from the committed data |
| **Secondary-dataset decision** | `SECONDARY_DATASET_EVALUATION.md` | why a 2nd (modelled, PM-only) dataset was evaluated and not used |

Supporting audit artifacts (unchanged): `audit/manuscript/` (full manuscript,
claim-to-evidence, original-vs-corrected, bibliography, readiness), `audit/reports/`
(all generated numbers/figures), `RUNBOOK.md` (how to run everything).

**One honest caveat carried through every document:** our own evaluation found the
original *causal / source-apportionment / control-optimization* claims unsupported,
so the draft narrows them. This is a deliberate, defensible choice, not a gap.
