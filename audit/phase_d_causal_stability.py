"""
Phase D - stability and sensitivity of the DirectLiNGAM structure.

The pipeline fits a single pooled, contemporaneous DirectLiNGAM on standardized
pollutants and presents the resulting graph as a finding. Phase D tests how much
to trust it:

  1. BOOTSTRAP STABILITY - refit on many resamples; report how often each edge
     appears and the sign/size spread of its coefficient.
  2. PRIOR-KNOWLEDGE SENSITIVITY - with vs without the secondary->primary ban.
  3. CONFOUNDER SENSITIVITY - add the (modelled) meteorology as exogenous nodes
     and check whether the key pollutant edges (esp. NO->ozone) survive. If an
     edge vanishes once weather is included, the pooled contemporaneous estimate
     was confounded - direct evidence for prior-review finding 9.

Everything is standardized ambient concentration z-space; edges are associational
structure under strong assumptions, NOT identified causal effects.

    python audit/phase_d_causal_stability.py [--boot 100] [--sample 30000]
"""

from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd
from lingam import DirectLiNGAM

OUT_DIR = "audit/reports"
PRIMARY = ["no", "no2", "co", "so2"]
SECONDARY = ["ozone", "pm25"]
WEATHER = ["temperature", "relative_humidity", "wind_speed", "pressure"]
THR = 0.05
SEED = 42


def load(cols):
    frames = []
    for f in sorted(glob.glob("data/raw/telemetry/*.parquet")):
        d = pd.read_parquet(f)
        for c in cols:
            if c not in d.columns:
                d[c] = np.nan
        frames.append(d[cols])
    return pd.concat(frames, ignore_index=True).dropna()


def prior_knowledge(columns, exogenous, effects):
    """pk[i,j] encodes j->i: 0 = forbidden, -1 = unknown.
    Forbid effects -> anything, and anything -> exogenous (exogenous are roots)."""
    idx = {c: i for i, c in enumerate(columns)}
    n = len(columns)
    pk = -np.ones((n, n), dtype=int)
    for e in effects:                       # effects cause nothing upstream
        for c in columns:
            if c != e:
                pk[idx[c], idx[e]] = 0       # no edge e -> c
    for x in exogenous:                     # nothing causes an exogenous node
        for c in columns:
            if c != x:
                pk[idx[x], idx[c]] = 0       # no edge c -> x
    return pk


def fit_adj(X, columns, exogenous, effects, use_prior=True):
    Z = (X - X.mean(0)) / np.where(X.std(0) == 0, 1, X.std(0))
    pk = prior_knowledge(columns, exogenous, effects) if use_prior else None
    m = DirectLiNGAM(prior_knowledge=pk, random_state=SEED)
    m.fit(Z)
    return np.asarray(m.adjacency_matrix_), [columns[i] for i in m.causal_order_]


def summarize(rep, title, columns, adj, order):
    rep.append(f"### {title}")
    rep.append(f"- recovered order: {' -> '.join(order)}")
    n = len(columns)
    edges = [(columns[j], columns[i], adj[i][j]) for i in range(n) for j in range(n)
             if i != j and abs(adj[i][j]) >= THR]
    edges.sort(key=lambda e: -abs(e[2]))
    for s, t, c in edges:
        rep.append(f"  - {s} -> {t}: {c:+.3f}")
    if not edges:
        rep.append("  - (no edges above threshold)")
    rep.append("")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=100)
    ap.add_argument("--sample", type=int, default=30000)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.RandomState(SEED)
    rep = ["# Phase D - DirectLiNGAM Stability & Sensitivity\n"]

    # ---- pollutant-only model (mirrors the pipeline) -----------------------
    cols = PRIMARY + SECONDARY
    data = load(cols)
    rep.append(f"Pollutant-only model on {len(data):,} complete-case rows "
               f"(columns {cols}).\n")
    Xfull = data.to_numpy(float)
    adj0, order0 = fit_adj(Xfull, cols, exogenous=[], effects=SECONDARY, use_prior=True)
    summarize(rep, "Point estimate (full data, with prior knowledge)", cols, adj0, order0)

    # ---- bootstrap stability ----------------------------------------------
    rep.append("## 1. Bootstrap stability (pollutant model)\n")
    n = len(cols)
    freq = np.zeros((n, n)); csum = np.zeros((n, n)); csq = np.zeros((n, n))
    for b in range(args.boot):
        idx = rng.randint(0, len(Xfull), min(args.sample, len(Xfull)))
        adj, _ = fit_adj(Xfull[idx], cols, [], SECONDARY, use_prior=True)
        sig = np.abs(adj) >= THR
        freq += sig; csum += adj; csq += adj * adj
    freq /= args.boot
    mean = csum / args.boot
    sd = np.sqrt(np.maximum(csq / args.boot - mean ** 2, 0))
    rows = []
    for i in range(n):
        for j in range(n):
            if i != j and (freq[i][j] > 0.05 or abs(mean[i][j]) >= THR):
                rows.append({"source": cols[j], "target": cols[i],
                             "edge_freq": round(float(freq[i][j]), 3),
                             "coef_mean": round(float(mean[i][j]), 3),
                             "coef_sd": round(float(sd[i][j]), 3)})
    bd = pd.DataFrame(rows).sort_values("edge_freq", ascending=False)
    bd.to_csv(f"{OUT_DIR}/phase_d_bootstrap_edges.csv", index=False)
    rep.append(bd.to_markdown(index=False))
    rep.append("\n> `edge_freq` = fraction of bootstraps where |coef| >= "
               f"{THR}. Edges with low frequency or sign-unstable coefficients "
               "should not be read as mechanisms.\n")

    # ---- prior-knowledge sensitivity --------------------------------------
    rep.append("## 2. Prior-knowledge sensitivity\n")
    adjN, orderN = fit_adj(Xfull, cols, [], SECONDARY, use_prior=False)
    summarize(rep, "Without the secondary->primary ban", cols, adjN, orderN)

    # ---- confounder (meteorology) sensitivity -----------------------------
    rep.append("## 3. Confounder sensitivity: add modelled meteorology as exogenous\n")
    cols2 = PRIMARY + WEATHER + SECONDARY
    data2 = load(cols2)
    X2 = data2.to_numpy(float)
    adjW, orderW = fit_adj(X2, cols2, exogenous=WEATHER, effects=SECONDARY, use_prior=True)
    summarize(rep, f"With weather included ({len(data2):,} rows)", cols2, adjW, orderW)
    # did NO->ozone survive?
    iO, jN = cols2.index("ozone"), cols2.index("no")
    no_oz = adjW[iO][jN]
    rep.append(f"> NO->ozone coefficient with weather included: **{no_oz:+.3f}** "
               f"(pollutant-only point estimate was {adj0[cols.index('ozone')][cols.index('no')]:+.3f}). "
               "Change under confounder inclusion indicates the pooled contemporaneous "
               "estimate is sensitive to omitted meteorology.\n")

    rep.append("## Interpretation\n")
    rep.append("- The graph is a **hypothesis generator**, not an identified causal "
               "model. Edges that are bootstrap-stable AND survive meteorology "
               "inclusion are the only ones worth discussing, and only as "
               "associational structure under DirectLiNGAM's (strong) linearity, "
               "non-Gaussianity, acyclicity and no-hidden-confounding assumptions.")
    rep.append("- Pooling across stations, seasons and hours ignores spatial/temporal "
               "dependence and regime switching (e.g. VOC- vs NOx-limited ozone), so "
               "coefficients are population-averaged associations, not local "
               "mechanisms.\n")

    with open(f"{OUT_DIR}/phase_d_causal_stability.md", "w") as fh:
        fh.write("\n".join(rep))
    print("\n".join(rep))
    print(f"\nWrote {OUT_DIR}/phase_d_causal_stability.md and phase_d_bootstrap_edges.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
