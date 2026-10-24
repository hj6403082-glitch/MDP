"""
Phase B/F check — the exact Pareto front of the fitted linear response model,
compared against the 19 saved optimizer policies.

The saved structural model (standardized, from results/out/phase2/causal_sem) is
purely linear:

    z_ozone = a_no * z_no
    z_pm25  = b_no * z_no + b_no2 * z_no2 + b_co * z_co

with decision variables in the box [-2, 0]. so2 and voc do not appear, so they
have no effect on either objective (voc is not even a fitted variable).

Because a_no < 0 and b_* > 0:
  * ozone is minimised by z_no as HIGH as allowed; it depends on nothing else.
  * pm25 is minimised by pushing every coefficiented variable to the lower bound.
So the exact Pareto set is {z_no2 = z_co = -2, z_no = t : t in [-2, 0]}, and the
objective-space front is the straight segment between the two endpoints. This is
solved in closed form; no metaheuristic is needed. We quantify how far the saved
'Pareto front' sits from this exact front.

    python audit/analytic_pareto.py
"""

from __future__ import annotations

import glob
import json

import numpy as np
import pandas as pd

# Coefficients read from the saved SEM (results/out/phase2/causal_sem).
A_NO = -0.12425503320772578           # z_ozone = A_NO * z_no
B_NO, B_NO2, B_CO = (0.09245019676597313, 0.21936470406571956, 0.22793944920433312)
LO, HI = -2.0, 0.0


def response(z_no, z_no2, z_co):
    oz = A_NO * z_no
    pm = B_NO * z_no + B_NO2 * z_no2 + B_CO * z_co
    return oz, pm


def exact_front(n=200):
    t = np.linspace(LO, HI, n)            # z_no sweep; z_no2 = z_co = -2
    oz, pm = response(t, LO, LO)
    return pd.DataFrame({"z_no": t, "ozone": oz, "pm25": pm})


def dominates(a_oz, a_pm, b_oz, b_pm, eps=1e-9):
    """a weakly dominates b and is strictly better in at least one objective."""
    return (a_oz <= b_oz + eps and a_pm <= b_pm + eps) and \
           (a_oz < b_oz - eps or a_pm < b_pm - eps)


def main() -> int:
    saved = pd.read_parquet(glob.glob("results/out/phase3/pareto_front/*.parquet")[0])
    ef = exact_front()

    # For each saved policy, the exact front point at the SAME ozone (ozone fixes
    # z_no), then the exact minimal pm25 there.
    gaps = []
    n_dom_by_exact = 0
    for _, r in saved.iterrows():
        oz, pm = float(r["ozone"]), float(r["pm25"])
        z_no = oz / A_NO                      # invert z_ozone = A_NO*z_no
        _, pm_exact = response(z_no, LO, LO)  # minimal pm25 at this ozone
        gaps.append(pm - pm_exact)            # >0 => saved is worse (higher pm25)
        if pm_exact < pm - 1e-9:
            n_dom_by_exact += 1

    gaps = np.array(gaps)
    # Also: are saved policies internally non-dominated? (reviewer's claim)
    objs = saved[["ozone", "pm25"]].to_numpy()
    internal_dominated = 0
    for i in range(len(objs)):
        for j in range(len(objs)):
            if i != j and dominates(objs[j, 0], objs[j, 1], objs[i, 0], objs[i, 1]):
                internal_dominated += 1
                break

    out = {
        "saved_policies": int(len(saved)),
        "dominated_by_exact_front": int(n_dom_by_exact),
        "internally_dominated_among_saved": int(internal_dominated),
        "pm25_gap_to_exact_front_mean": float(gaps.mean()),
        "pm25_gap_to_exact_front_max": float(gaps.max()),
        "pm25_gap_to_exact_front_min": float(gaps.min()),
        "exact_front_endpoints": {
            "ozone_min": {"z_no": 0.0, "ozone": 0.0,
                          "pm25": float(response(0, LO, LO)[1])},
            "pm25_min": {"z_no": LO, "ozone": float(response(LO, LO, LO)[0]),
                         "pm25": float(response(LO, LO, LO)[1])},
        },
        "note_voc_so2": "voc and so2 have zero effect; voc is not a fitted variable",
    }
    ef.to_csv("audit/reports/exact_pareto_front.csv", index=False)
    with open("audit/reports/pareto_comparison.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))
    print("\nWrote audit/reports/exact_pareto_front.csv and pareto_comparison.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
