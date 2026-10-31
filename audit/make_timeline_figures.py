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


# Recent work only (past ~2 years, 2024-2026) per the Review-2 instruction.
A = [
    (0, "2024", "Autoencoder PM2.5\nIndia (Rautela &\nGoyal, Sci. Rep.)"),
    (0, "2024", "AI review\n(Malhotra,\nJ. Big Data)"),
    (0, "2024", "Causal CCM\n(Qi et al., ERL)"),
    (0, "2025", "Causal forest+XAI\n(Wang et al., ESE)"),
    (0, "2025", "CNN-RNN hybrid\n(Utku, Atmosphere)"),
    (0, "2026", "SHAP de-weathering\n(Ye et al., ACP)"),
    (0, "2026", "This work:\nleakage-safe audit"),
]
B = [
    (0, "2024", "Double-PMF PM2.5\nDelhi (Faisal, IITD)"),
    (0, "2024", "PMF Lucknow/Kanpur\n(IGP winter)"),
    (0, "2024", "Airshed ~60% PM2.5\n(India, Air/MDPI)"),
    (0, "2025", "Dispersion-norm. PMF\n(Pullokaran, EGU25)"),
    (0, "2025", "RF+SHAP O3 regimes\n(Lin et al.)"),
    (0, "2026", "This work: analytic\nPareto proof"),
]

if __name__ == "__main__":
    timeline(A, "Timeline A - Predictive & Causal ML for Air Quality (2024-2026)",
             "fig_timeline_A.png")
    timeline(B, "Timeline B - Source Apportionment & Optimization (2024-2026)",
             "fig_timeline_B.png")
    print("done")
