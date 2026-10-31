"""
Two literature-timeline figures for the Review-2 package (Timeline A: predictive &
causal ML for air quality; Timeline B: source apportionment & multi-objective
optimization). Writes to audit/reports/figures/.

    python audit/make_timeline_figures.py
"""
from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG = "audit/reports/figures"
os.makedirs(FIG, exist_ok=True)
NAVY = "#1b3a5b"; ACCENT = "#2a7ae2"; VERM = "#D55E00"; GREY = "#555555"
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "font.family": "DejaVu Sans"})


def timeline(events, title, outfile, span=None):
    # events: list of (_, year_label, text); drawn at EVEN horizontal spacing.
    n = len(events)
    fig, ax = plt.subplots(figsize=(12, 4.4))
    xs = list(range(n))
    ax.annotate("", xy=(n - 0.4, 0), xytext=(-0.6, 0),
                arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2.5), zorder=1)
    for i, (_, ylab, txt) in enumerate(events):
        last = (i == n - 1)
        col = VERM if last else ACCENT
        ax.scatter([i], [0], s=100 if last else 62, color=col, zorder=3,
                   edgecolor="white", linewidth=1.2)
        up = (i % 2 == 0)
        yoff = 0.6 if up else -0.6
        va = "bottom" if up else "top"
        ax.plot([i, i], [0, yoff * 0.7], color=GREY, lw=0.8, zorder=2)
        ax.text(i, yoff, f"{ylab}\n{txt}", ha="center", va=va,
                fontsize=8.3, color=(VERM if last else NAVY),
                fontweight="bold" if last else "normal", linespacing=1.3,
                bbox=dict(boxstyle="round,pad=0.32",
                          fc=("#fdece0" if last else "#eef3f8"),
                          ec=(VERM if last else "#c5d4e6"), lw=0.9))
    ax.set_xlim(-0.9, n - 0.3); ax.set_ylim(-1.3, 1.3)
    ax.axis("off")
    ax.set_title(title, fontsize=12.5, fontweight="bold", color=NAVY, pad=12)
    fig.tight_layout()
    fig.savefig(f"{FIG}/{outfile}", bbox_inches="tight"); plt.close(fig)
    print("wrote", outfile)


A = [
    (2001, "2001", "Random Forests\n(Breiman)"),
    (2011, "2006/11", "DirectLiNGAM\n(Shimizu)"),
    (2016, "2016", "XGBoost\n(Chen & Guestrin)"),
    (2018, "2018", "Blocked eval\n(Oliveira)"),
    (2020, "2020", "Spatial-CV leakage\n(Just et al.)"),
    (2024, "2024", "Causal CCM\n(Qi et al.)"),
    (2025, "2025", "XAI + causal\n(Wang et al.)"),
    (2026, "2026", "This work:\nleakage-safe audit"),
]
B = [
    (1994, "1994", "PMF receptor model\n(Paatero & Tapper)"),
    (2002, "2002", "NSGA-II\n(Deb et al.)"),
    (2013, "2013", "Delhi inventory\n(Guttikunda)"),
    (2015, "2015", "PM2.5 PMF Delhi\n(Pant et al.)"),
    (2020, "2020", "Organic-aerosol PMF\n(Tobler et al.)"),
    (2021, "2021", "NSGA-II emissions\n(Xu et al.)"),
    (2025, "2025", "RF+SHAP regimes\n(Lin et al.)"),
    (2026, "2026", "This work:\nanalytic Pareto proof"),
]

if __name__ == "__main__":
    timeline(A, "Timeline A - Predictive & Causal ML for Air Quality",
             "fig_timeline_A.png")
    timeline(B, "Timeline B - Source Apportionment & Multi-Objective Optimization",
             "fig_timeline_B.png")
    print("done")
