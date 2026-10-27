"""
Phase B regression tests for the consequential correctness fixes.

These exercise pure-Python logic only (no Spark/Java), so they run anywhere:

    python -m pytest tests/test_phaseB_guards.py -q
    # or: python tests/test_phaseB_guards.py
"""

from __future__ import annotations

import numpy as np

from src.phases.phase3_optimization import (
    CausalPolicyModel,
    supported_decision_variables,
    _topological_order,
)


# ---- F4: unsupported optimization variables are rejected --------------------
def test_voc_is_rejected_when_absent_from_graph():
    configured = ["no", "no2", "co", "so2", "voc"]
    graph_vars = ["no", "no2", "co", "ozone", "pm25"]  # as actually fitted (no voc/so2)
    supported, rejected = supported_decision_variables(configured, graph_vars)
    assert "voc" in rejected and "voc" not in supported
    assert "so2" in rejected          # so2 had no edges either -> not a graph var
    assert supported == ["no", "no2", "co"]


def test_supported_preserves_order_and_is_exhaustive():
    supported, rejected = supported_decision_variables(["a", "b", "c"], ["c", "a"])
    assert supported == ["a", "c"] and rejected == ["b"]


# ---- Response model only uses fitted variables -----------------------------
def _toy_model():
    # z_ozone = -0.12*z_no ; z_pm25 = 0.09*z_no + 0.22*z_no2 + 0.23*z_co
    cols = ["no", "no2", "co", "ozone", "pm25"]
    idx = {c: i for i, c in enumerate(cols)}
    B = np.zeros((5, 5))
    B[idx["ozone"]][idx["no"]] = -0.12
    B[idx["pm25"]][idx["no"]] = 0.09
    B[idx["pm25"]][idx["no2"]] = 0.22
    B[idx["pm25"]][idx["co"]] = 0.23
    order = _topological_order(5, B)
    return CausalPolicyModel(cols, B, order, ["no", "no2", "co"], ["ozone", "pm25"])


def test_evaluate_matches_closed_form_and_ignores_unfitted():
    m = _toy_model()
    out = m.evaluate({"no": -2.0, "no2": -2.0, "co": -2.0})
    assert abs(out["ozone"] - (-0.12 * -2.0)) < 1e-12
    assert abs(out["pm25"] - (0.09 * -2 + 0.22 * -2 + 0.23 * -2)) < 1e-12
    # Passing a variable not in the model is rejected explicitly (not ignored).
    try:
        m.evaluate({"no": -2.0, "no2": -2.0, "co": -2.0, "voc": -2.0})
        raise AssertionError("expected ValueError for unfitted variable 'voc'")
    except ValueError as e:
        assert "voc" in str(e)


# ---- Exact Pareto front dominates the saved metaheuristic set ---------------
def test_exact_front_dominates_saved_if_present():
    import glob, os, pandas as pd
    saved = glob.glob("results/out/phase3/pareto_front/*.parquet")
    if not saved:                       # results optional in some checkouts
        return
    pf = pd.read_parquet(saved[0])
    A_NO = -0.12425503320772578
    B_NO, B_NO2, B_CO = 0.09245019676597313, 0.21936470406571956, 0.22793944920433312
    dominated = 0
    for _, r in pf.iterrows():
        z_no = r["ozone"] / A_NO
        pm_exact = B_NO * z_no + B_NO2 * (-2.0) + B_CO * (-2.0)
        if pm_exact < r["pm25"] - 1e-9:
            dominated += 1
    # Every saved 'optimal' policy is beaten by the closed-form corner solution.
    assert dominated == len(pf)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
    print("all Phase B guard tests passed")
