"""
Generate publication figures for the paper from the committed audit outputs.
No new data: reads only audit/reports/*.csv/json and results/out/. Figures go to
audit/reports/figures/. Colourblind-safe (Okabe-Ito) palette.

    python audit/make_figures.py
"""
from __future__ import annotations
import glob, json, os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = "audit/reports"
FIG = f"{R}/figures"
os.makedirs(FIG, exist_ok=True)

# Okabe-Ito colourblind-safe palette
OI = dict(orange="#E69F00", sky="#56B4E9", green="#009E73", yellow="#F0E442",
          blue="#0072B2", verm="#D55E00", purple="#CC79A7", grey="#999999",
          black="#222222")

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 10,
    "axes.titlesize": 11.5, "axes.titleweight": "bold", "axes.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
    "figure.autolayout": True, "font.family": "DejaVu Sans",
})

def save(fig, name):
    p = f"{FIG}/{name}"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    print("wrote", p)


# ---- Fig 1: data coverage -------------------------------------------------
def fig_coverage():
    s = pd.read_csv(f"{R}/station_operating_periods.csv")
    av = pd.read_csv(f"{R}/pollutant_availability.csv")
    poll = av[av.variable.isin(["co","no","no2","ozone","pm10","pm25","so2"])].copy()
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4))
    # (a) per-station within-year coverage
    a.hist(s.within_year_coverage, bins=24, color=OI["sky"], edgecolor="white")
    mean = s.within_year_coverage.mean()
    a.axvline(mean, color=OI["verm"], lw=2, ls="--",
              label=f"mean = {mean:.0%}")
    a.axvspan(0, 0.5, color=OI["verm"], alpha=0.07)
    n_low = int((s.within_year_coverage < 0.5).sum())
    a.text(0.25, a.get_ylim()[1]*0.9, f"{n_low} stations\n< 50%",
           ha="center", va="top", color=OI["verm"], fontsize=9)
    a.set_xlabel("within-year coverage"); a.set_ylabel("stations")
    a.set_title(f"(a) Per-station coverage (n={len(s)})"); a.legend(frameon=False)
    # (b) per-pollutant availability
    poll = poll.sort_values("nonnull_frac_of_present_rows")
    b.barh(poll.variable.str.upper(), poll.nonnull_frac_of_present_rows,
           color=OI["green"], edgecolor="white")
    for y,(v,f) in enumerate(zip(poll.variable, poll.nonnull_frac_of_present_rows)):
        b.text(f-0.02, y, f"{f:.0%}", va="center", ha="right", color="white", fontsize=8)
    b.set_xlim(0, 1); b.set_xlabel("non-null fraction (within present rows)")
    b.set_title("(b) Pollutant availability")
    fig.suptitle("Data coverage: 204 stations, ~1.18M station-hours, ~66% of full grid",
                 fontsize=11.5, fontweight="bold")
    save(fig, "fig1_data_coverage.png")


# ---- Fig 2: leakage / R2 by protocol --------------------------------------
def fig_leakage():
    m = pd.read_csv(f"{R}/phase_c_metrics.csv")
    def g(proto, model):
        r = m[(m.protocol==proto)&(m.model==model)]
        return float(r.r2.iloc[0]) if len(r) else np.nan
    bars = [
        ("Random split\n(LEAKY)",        g("random-split(LEAKY)","xgboost"), OI["verm"]),
        ("Blocked\ntemporal",            g("blocked-temporal","xgboost"),    OI["blue"]),
        ("Leave-\nstations-out",         g("leave-stations-out","xgboost"),  OI["blue"]),
        ("Temporal x\nspatial (strict)", g("temporal x spatial","xgboost"),  OI["blue"]),
        ("Per-station\nclimatology",     g("blocked-temporal","per-station-climatology"), OI["grey"]),
        ("Persistence\n(prev hour)",     g("blocked-temporal","persistence(prev-hour)"),  OI["green"]),
    ]
    labels=[x[0] for x in bars]; vals=[x[1] for x in bars]; cols=[x[2] for x in bars]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    bb = ax.bar(labels, vals, color=cols, edgecolor="white")
    for rect,v in zip(bb, vals):
        ax.text(rect.get_x()+rect.get_width()/2, v+0.012, f"{v:.2f}",
                ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_ylabel("held-out $R^2$"); ax.set_ylim(0, 0.9)
    ax.set_title("Leakage inflates apparent skill: honest XGBoost $R^2$ is 0.22–0.30, not 0.41")
    ax.annotate("random splitting of\nautocorrelated data\n= optimistic",
                xy=(0, vals[0]), xytext=(0.7, 0.62), fontsize=8.5, color=OI["verm"],
                arrowprops=dict(arrowstyle="->", color=OI["verm"], lw=1.2))
    import matplotlib.patches as mp
    leg=[mp.Patch(color=OI["verm"],label="leaky (contrast only)"),
         mp.Patch(color=OI["blue"],label="honest XGBoost"),
         mp.Patch(color=OI["green"],label="persistence baseline"),
         mp.Patch(color=OI["grey"],label="climatology baseline")]
    ax.legend(handles=leg, frameon=False, fontsize=8.5, ncol=2, loc="upper right")
    save(fig, "fig2_leakage_r2.png")


# ---- Fig 3: incremental value (Phase C2) ----------------------------------
def fig_incremental():
    c2 = pd.read_csv(f"{R}/phase_c2_metrics.csv")
    con = c2[c2.block=="contemporaneous"].set_index("model")["r2"]
    steps = [("weather\nonly", con.get("weather only"), OI["sky"]),
             ("+ pollutants", con.get("weather + pollutants"), OI["blue"]),
             ("+ time\nharmonics", con.get("+ time harmonics"), OI["green"]),
             ("+ station mean\n(memorisation)", con.get("+ station mean (train-only)"), OI["grey"])]
    labels=[s[0] for s in steps]; vals=[s[1] for s in steps]; cols=[s[2] for s in steps]
    fig, ax = plt.subplots(figsize=(8, 4.3))
    bb=ax.bar(labels, vals, color=cols, edgecolor="white")
    # hatch the memorisation bar
    bb[-1].set_hatch("////"); bb[-1].set_edgecolor("white")
    prev=0
    for i,(rect,v) in enumerate(zip(bb,vals)):
        ax.text(rect.get_x()+rect.get_width()/2, v+0.008, f"{v:.2f}",
                ha="center", va="bottom", fontsize=9, fontweight="bold")
        if i>0:
            ax.text(rect.get_x()+rect.get_width()/2, prev/2 if False else 0.02,
                    f"+{v-prev:.2f}", ha="center", va="bottom", fontsize=8, color=OI["black"])
        prev=v
    ax.set_ylabel("held-out $R^2$"); ax.set_ylim(0, 0.52)
    ax.set_title("What explains ozone: pollutants add only +0.12 beyond weather")
    ax.annotate("station-mean gain is\nsite memorisation —\ndoes NOT generalise to\nunsensored sites",
                xy=(3, 0.413), xytext=(1.35, 0.50), fontsize=8, color=OI["verm"],
                va="top", ha="left",
                arrowprops=dict(arrowstyle="->", color=OI["verm"], lw=1.1))
    save(fig, "fig3_incremental_r2.png")


# ---- Fig 4: bootstrap edge stability --------------------------------------
def fig_edges():
    e = pd.read_csv(f"{R}/phase_d_bootstrap_edges.csv").sort_values("edge_freq")
    e = e.tail(10)
    labels = [f"{s.upper()} -> {t.upper()}" for s,t in zip(e.source, e.target)]
    cols = [OI["blue"] if c < 0 else OI["orange"] for c in e.coef_mean]
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.barh(labels, e.edge_freq, color=cols, edgecolor="white")
    for y,(f,c) in enumerate(zip(e.edge_freq, e.coef_mean)):
        ax.text(f-0.02, y, f"{f:.2f} ({c:+.2f})", va="center", ha="right",
                color="white", fontsize=8)
    ax.axvline(0.8, color=OI["grey"], ls="--", lw=1, label="stability threshold 0.8")
    # highlight NO->ozone
    for y,lab in enumerate(labels):
        if lab=="NO -> OZONE":
            ax.get_yticklabels()[y].set_color(OI["verm"])
            ax.get_yticklabels()[y].set_fontweight("bold")
            ax.text(0.5, y, "survives weather", color=OI["verm"], fontsize=8,
                    va="center", ha="center")
    ax.set_xlim(0,1.02); ax.set_xlabel("bootstrap edge frequency  (mean standardized coef.)")
    ax.set_title("Edge stability: only NO -> ozone (negative) is both stable AND survives meteorology")
    import matplotlib.patches as mp
    ax.legend(handles=[mp.Patch(color=OI["blue"],label="negative coef."),
                       mp.Patch(color=OI["orange"],label="positive coef.")],
              frameon=False, fontsize=8.5, loc="lower right")
    save(fig, "fig4_edge_stability.png")


# ---- Fig 5: Pareto dominance ----------------------------------------------
def fig_pareto():
    front = pd.read_csv(f"{R}/exact_pareto_front.csv")
    saved = pd.read_parquet(glob.glob("results/out/phase3/pareto_front/*.parquet")[0])
    comp = json.load(open(f"{R}/pareto_comparison.json"))
    fig, ax = plt.subplots(figsize=(7.2, 5))
    front = front.sort_values("pm25")
    ax.plot(front.pm25, front.ozone, color=OI["green"], lw=2.4,
            label="exact closed-form front", zorder=2)
    ax.scatter(saved.pm25, saved.ozone, color=OI["verm"], s=42, zorder=3,
               edgecolor="white", label=f"{len(saved)} metaheuristic policies (all dominated)")
    ax.set_xlabel("PM2.5 objective (standardized, lower = better)")
    ax.set_ylabel("ozone objective (standardized, lower = better)")
    ax.set_title("All 19 'optimal' policies are dominated by the exact front")
    ax.annotate(f"mean gap to front = {comp['pm25_gap_to_exact_front_mean']:.3f}\n"
                f"max gap = {comp['pm25_gap_to_exact_front_max']:.3f}",
                xy=(0.02,0.02), xycoords="axes fraction", fontsize=8.5,
                va="bottom", ha="left",
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=OI["grey"]))
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "fig5_pareto_dominance.png")


if __name__ == "__main__":
    fig_coverage(); fig_leakage(); fig_incremental(); fig_edges(); fig_pareto()
    print("\nAll figures in", FIG)
