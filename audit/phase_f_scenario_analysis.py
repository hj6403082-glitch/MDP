"""
Phase F - defensible model-based scenario analysis (replaces 'policy optimization').

The fitted response model is linear in standardized AMBIENT CONCENTRATIONS, so
its exact Pareto frontier is closed-form; no metaheuristic is needed (Phase B
showed the NSGA-II/TPE set was dominated). Here we:

  1. Compute the EXACT frontier of the point-estimate model.
  2. Propagate UNCERTAINTY by bootstrapping the DirectLiNGAM fit (same procedure
     as Phase D) and recomputing the frontier each time -> a band.
  3. Compare against the saved metaheuristic policies and simple corner baselines.
  4. Render a labelled figure and write the frontier table.

HARD LABELLING RULE: axes and scenarios are in standardized ambient-concentration
space. These are model-based what-ifs, NOT emission reductions and NOT policy
benefits. so2 and voc have no effect (voc is not even fitted).

    python audit/phase_f_scenario_analysis.py [--boot 100] [--sample 30000]
"""

from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lingam import DirectLiNGAM

OUT_DIR = "audit/reports"
PRIMARY = ["no", "no2", "co", "so2"]
SECONDARY = ["ozone", "pm25"]
LO, HI = -2.0, 0.0
SEED = 42
# Coefficients of the model that ACTUALLY produced the saved policies
# (results/out/phase2/causal_sem). The point-estimate frontier must use these so
# the saved policies are compared against their own model (consistent with
# Phase B). Bootstrap refits below use complete-case data and therefore move the
# frontier - that movement is itself a reported uncertainty.
SAVED = dict(a_no=-0.12425503320772578, b_no=0.09245019676597313,
             b_no2=0.21936470406571956, b_co=0.22793944920433312)


def load():
    cols = PRIMARY + SECONDARY
    frames = []
    for f in sorted(glob.glob("data/raw/telemetry/*.parquet")):
        d = pd.read_parquet(f)
        for c in cols:
            if c not in d.columns:
                d[c] = np.nan
        frames.append(d[cols])
    return pd.concat(frames, ignore_index=True).dropna(), cols


def prior(cols):
    idx = {c: i for i, c in enumerate(cols)}
    n = len(cols); pk = -np.ones((n, n), int)
    for s in SECONDARY:
        for c in cols:
            if c != s:
                pk[idx[c], idx[s]] = 0
    return pk


def coeffs(X, cols):
    Z = (X - X.mean(0)) / np.where(X.std(0) == 0, 1, X.std(0))
    m = DirectLiNGAM(prior_knowledge=prior(cols), random_state=SEED)
    m.fit(Z)
    A = np.asarray(m.adjacency_matrix_); idx = {c: i for i, c in enumerate(cols)}
    return (A[idx["ozone"]][idx["no"]],                       # a_no
            A[idx["pm25"]][idx["no"]], A[idx["pm25"]][idx["no2"]], A[idx["pm25"]][idx["co"]])


def front(a_no, b_no, b_no2, b_co, grid):
    # exact frontier: no2 = co = LO, sweep no in [LO, HI]
    oz = a_no * grid
    pm = b_no * grid + (b_no2 + b_co) * LO
    return oz, pm


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=100)
    ap.add_argument("--sample", type=int, default=30000)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.RandomState(SEED)
    data, cols = load()
    X = data.to_numpy(float)
    grid = np.linspace(LO, HI, 60)

    # point estimate = the SAVED model (the one the policies were generated under)
    a0, bn0, b20, bc0 = SAVED["a_no"], SAVED["b_no"], SAVED["b_no2"], SAVED["b_co"]
    oz0, pm0 = front(a0, bn0, b20, bc0, grid)

    # bootstrap band
    ozs, pms = [], []
    for _ in range(args.boot):
        idx = rng.randint(0, len(X), min(args.sample, len(X)))
        a, bn, b2, bc = coeffs(X[idx], cols)
        o, p = front(a, bn, b2, bc, grid)
        ozs.append(o); pms.append(p)
    ozs, pms = np.array(ozs), np.array(pms)
    oz_lo, oz_hi = np.percentile(ozs, 5, 0), np.percentile(ozs, 95, 0)
    pm_lo, pm_hi = np.percentile(pms, 5, 0), np.percentile(pms, 95, 0)

    # figure
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    ax.fill_betweenx(oz0, pm_lo, pm_hi, color="#1b7f3b", alpha=0.12,
                     label="frontier under refit (5–95%, PM2.5)")
    ax.plot(pm0, oz0, "-", color="#1b3a5b", lw=2,
            label="exact frontier (saved model)")
    try:
        saved = pd.read_parquet(glob.glob("results/out/phase3/pareto_front/*.parquet")[0])
        ax.scatter(saved["pm25"], saved["ozone"], c="#b00020", s=28, zorder=5,
                   label="saved NSGA-II/TPE (all dominated)")
    except Exception:
        pass
    ax.set_xlabel("PM2.5  (standardized concentration scenario, lower = better)")
    ax.set_ylabel("Ozone  (standardized concentration scenario, lower = better)")
    ax.set_title("Phase F: exact concentration-scenario frontier with uncertainty")
    ax.grid(True, alpha=0.3); ax.legend(fontsize=7, loc="upper right")
    ax.text(0.02, 0.02, "Standardized ambient concentrations — NOT emissions or policy benefits",
            transform=ax.transAxes, fontsize=7, color="#b00020")
    fig.tight_layout(); fig.savefig(f"{OUT_DIR}/phase_f_scenario_front.png", bbox_inches="tight")

    # table + report
    tbl = pd.DataFrame({"z_no": grid, "ozone": oz0, "pm25": pm0,
                        "ozone_lo": oz_lo, "ozone_hi": oz_hi,
                        "pm25_lo": pm_lo, "pm25_hi": pm_hi})
    tbl.to_csv(f"{OUT_DIR}/phase_f_scenario_front.csv", index=False)

    summary = {
        "point_estimate_coeffs": {"a_no(ozone)": a0, "b_no(pm25)": bn0,
                                  "b_no2(pm25)": b20, "b_co(pm25)": bc0},
        "frontier_endpoints": {
            "min_ozone_scenario": {"z_no": 0.0, "ozone": float(oz0[-1]),
                                   "pm25": float(pm0[-1])},
            "min_pm25_scenario": {"z_no": -2.0, "ozone": float(oz0[0]),
                                  "pm25": float(pm0[0])}},
        "note": "so2 and voc have zero effect; voc not fitted; -2 sigma scenarios "
                "may extrapolate beyond observed support / imply negative "
                "concentrations and are flagged as unsupported.",
    }
    with open(f"{OUT_DIR}/phase_f_scenario_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    ar, bnr, b2r, bcr = coeffs(X, cols)   # full complete-case refit, for sensitivity
    rep = ["# Phase F - Model-Based Concentration-Scenario Analysis\n",
           "The response model is linear in standardized ambient concentrations; "
           "its Pareto frontier is closed-form (no optimizer needed).\n",
           "## Point-estimate coefficients (the SAVED model)\n",
           f"- ozone = {a0:+.3f}·z_no", f"- pm25 = {bn0:+.3f}·z_no {b20:+.3f}·z_no2 {bc0:+.3f}·z_co\n",
           "## Refit sensitivity (complete-case vs the saved bounded/imputed fit)\n",
           f"- A full complete-case refit gives pm25 = {bnr:+.3f}·z_no {b2r:+.3f}·z_no2 "
           f"{bcr:+.3f}·z_co — notably different (esp. the CO coefficient). The response "
           "coefficients are **sensitive to sampling and imputation choices**, so the "
           "frontier location is itself uncertain beyond the plotted band.\n",
           "## Exact frontier endpoints (with bootstrap)\n",
           f"- Min-ozone scenario (z_no=0, z_no2=z_co=-2): ozone={oz0[-1]:+.3f}, "
           f"pm25={pm0[-1]:+.3f}",
           f"- Min-pm25 scenario (z_no=z_no2=z_co=-2): ozone={oz0[0]:+.3f} "
           f"(90% CI {oz_lo[0]:+.3f}..{oz_hi[0]:+.3f}), pm25={pm0[0]:+.3f} "
           f"(90% CI {pm_lo[0]:+.3f}..{pm_hi[0]:+.3f})\n",
           "## Findings\n",
           "- The frontier is a short, nearly-linear trade-off governed almost "
           "entirely by **z_no** (ozone falls as NO rises via titration; PM2.5 "
           "falls as NO/NO2/CO fall). so2 and voc are inert.",
           "- Every saved NSGA-II/TPE policy lies **inside** (dominated by) this "
           "exact frontier (Phase B): the metaheuristic added nothing.",
           "- The bootstrap band is the model/sampling uncertainty only; it does "
           "**not** include measurement-unit error (CO), imputation, or structural "
           "(linearity/confounding) uncertainty, which are larger.",
           "- **Interpretation guard:** these are standardized ambient-concentration "
           "what-ifs. They are NOT emission reductions, NOT percentages, and carry "
           "NO policy-benefit interpretation. The -2σ corner may be physically "
           "infeasible (negative concentrations) and is flagged as extrapolation.\n",
           "![frontier](phase_f_scenario_front.png)\n"]
    with open(f"{OUT_DIR}/phase_f_scenario_analysis.md", "w") as fh:
        fh.write("\n".join(rep))
    print("\n".join(rep))
    print(f"Wrote {OUT_DIR}/phase_f_scenario_front.png, .csv, summary.json, .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
