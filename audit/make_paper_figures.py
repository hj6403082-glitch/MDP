"""
Two additional figures for the manuscript: the recovered causal DAG (from the
bootstrap-stable DirectLiNGAM edges) and the SHAP global importance ranking.
Reads only committed audit outputs. Writes to audit/reports/figures/.

    python audit/make_paper_figures.py
"""
from __future__ import annotations
import glob, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle

R = "audit/reports"; FIG = f"{R}/figures"
os.makedirs(FIG, exist_ok=True)
OI = dict(orange="#E69F00", sky="#56B4E9", green="#009E73", blue="#0072B2",
          verm="#D55E00", purple="#CC79A7", grey="#999999", black="#222222")
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "font.size": 10,
    "font.family": "DejaVu Sans", "axes.titlesize": 11.5, "axes.titleweight": "bold"})


def fig_dag(min_freq=0.9):
    e = pd.read_csv(f"{R}/phase_d_bootstrap_edges.csv")
    e = e[e.edge_freq >= min_freq].copy()
    nodes = ["no", "no2", "co", "pm10", "pm25", "so2", "ozone"]
    ang = {n: 2*np.pi*i/len(nodes) + np.pi/2 for i, n in enumerate(nodes)}
    pos = {n: (np.cos(a), np.sin(a)) for n, a in ang.items()}
    fig, ax = plt.subplots(figsize=(7.2, 7.2))
    for n, (x, y) in pos.items():
        hi = (n == "ozone" or n == "no")
        ax.add_patch(Circle((x, y), 0.17, fc=(OI["sky"] if hi else "white"),
                     ec=OI["blue"], lw=2, zorder=3))
        ax.text(x, y, n.upper(), ha="center", va="center", fontsize=9.5,
                fontweight="bold", zorder=4)
    for _, r in e.iterrows():
        if r.source not in pos or r.target not in pos:
            continue
        x0, y0 = pos[r.source]; x1, y1 = pos[r.target]
        dx, dy = x1 - x0, y1 - y0; L = np.hypot(dx, dy)
        x0 += dx/L*0.17; y0 += dy/L*0.17; x1 -= dx/L*0.19; y1 -= dy/L*0.19
        neg = r.coef_mean < 0
        col = OI["blue"] if neg else OI["orange"]
        w = 1.2 + 3.5*abs(r.coef_mean)
        key = (r.source == "no" and r.target == "ozone")
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                     arrowstyle="-|>", mutation_scale=16,
                     lw=(w+1.5 if key else w), color=(OI["verm"] if key else col),
                     connectionstyle="arc3,rad=0.08", zorder=2, alpha=0.95))
        mx, my = (x0+x1)/2, (y0+y1)/2
        ax.text(mx, my, f"{r.coef_mean:+.2f}", fontsize=7.3,
                color=(OI["verm"] if key else col), ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.8), zorder=5)
    ax.text(0, -1.55, "Red: NO -> ozone (titration), the only edge that also survives meteorology.\n"
            "Blue = negative, orange = positive standardized coefficient; width ~ |coef|. "
            f"Edges with bootstrap frequency >= {min_freq}.",
            ha="center", va="top", fontsize=8.2, color=OI["grey"])
    ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.75, 1.5); ax.axis("off")
    ax.set_title("Recovered DirectLiNGAM structure among criteria pollutants")
    fig.savefig(f"{FIG}/fig3_causal_dag.png", bbox_inches="tight"); plt.close(fig)
    print("wrote fig3_causal_dag.png")


def fig_shap():
    f = glob.glob("results/out/phase3/shap_importance/*.parquet")
    if not f:
        print("no shap importance"); return
    d = pd.read_parquet(f[0]).sort_values("mean_abs_shap")
    col = [OI["green"] if v in ("temperature", "relative_humidity", "wind_speed", "pressure")
           else (OI["verm"] if v == "no" else OI["blue"]) for v in d.feature]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.barh(d.feature.str.upper(), d.mean_abs_shap, color=col, edgecolor="white")
    for y, v in enumerate(d.mean_abs_shap):
        ax.text(v + 0.05, y, f"{v:.2f}", va="center", fontsize=8)
    ax.set_xlabel("mean |SHAP value|  (contribution to ozone prediction)")
    ax.set_title("SHAP global importance for ozone (meteorology dominates; NO leads pollutants)")
    import matplotlib.patches as mp
    ax.legend(handles=[mp.Patch(color=OI["green"], label="meteorology"),
                       mp.Patch(color=OI["verm"], label="NO"),
                       mp.Patch(color=OI["blue"], label="other pollutant")],
              frameon=False, fontsize=8.5, loc="lower right")
    fig.savefig(f"{FIG}/fig5_shap_importance.png", bbox_inches="tight"); plt.close(fig)
    print("wrote fig5_shap_importance.png")


if __name__ == "__main__":
    fig_dag(); fig_shap()
    print("done")
