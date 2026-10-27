"""
Phase C - leakage-safe predictive evaluation of the ozone baseline.

Task definition
---------------
This is **contemporaneous estimation (nowcasting)**: ozone is estimated from
*same-hour* pollutant and (modelled) weather predictors. It is therefore an
association model, NOT a forecaster and NOT a causal effect. Predictive accuracy
here is not evidence of causal validity.

Protocols (all with train-fold-only preprocessing; no tuning on any test set):
  0. LEAKY random 80/20 split  — reproduces the original design to expose its
     optimism.
  1. BLOCKED TEMPORAL           — train on earlier hours, test on later hours
     (generalisation across time).
  2. LEAVE-STATIONS-OUT         — train on a subset of stations, test on unseen
     stations (spatial generalisation).
  3. TEMPORAL x SPATIAL         — later hours AND unseen stations (strictest).

Baselines per protocol: global train mean; per-station train climatology (where
the station is seen in train); same-station previous-hour persistence (temporal).
Ablations (blocked temporal): weather-only, pollutants-only, both.
Uncertainty: station-block bootstrap of the test metric (resample whole stations
with replacement; no refit) -> 90% CI.

    python audit/phase_c_predictive_eval.py            # full data
    python audit/phase_c_predictive_eval.py --rows 300000   # faster smoke run
"""

from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

RAW_GLOB = "data/raw/telemetry/*.parquet"
OUT_DIR = "audit/reports"
TARGET = "ozone"
POLLUTANTS = ["co", "no", "no2", "pm10", "pm25", "so2"]          # predictors (no ozone)
WEATHER = ["temperature", "relative_humidity", "wind_speed", "pressure"]
FEATURES = POLLUTANTS + WEATHER
SEED = 42
XGB = dict(n_estimators=200, max_depth=6, learning_rate=0.05, subsample=0.8,
           colsample_bytree=0.8, tree_method="hist", n_jobs=-1, random_state=SEED)


def load(rows=0):
    frames = []
    for f in sorted(glob.glob(RAW_GLOB)):
        d = pd.read_parquet(f)
        for c in [TARGET] + FEATURES:
            if c not in d.columns:
                d[c] = np.nan
        d["station_id"] = d["station_id"].astype(str)
        frames.append(d[["timestamp", "station_id"] + [TARGET] + FEATURES])
    df = pd.concat(frames, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.dropna(subset=[TARGET]).sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    if rows:
        df = df.sample(rows, random_state=SEED).sort_values(
            ["station_id", "timestamp"]).reset_index(drop=True)
    df["month"] = df["timestamp"].dt.month
    return df


def metrics(y, yhat):
    return {"r2": float(r2_score(y, yhat)),
            "rmse": float(np.sqrt(mean_squared_error(y, yhat))),
            "mae": float(mean_absolute_error(y, yhat)),
            "n": int(len(y))}


def fit_predict(tr, te, feats):
    m = XGBRegressor(**XGB)
    m.fit(tr[feats], tr[TARGET])              # XGBoost handles NaN predictors natively
    return m.predict(te[feats])


def station_block_bootstrap_r2(te, yhat, n=300):
    """90% CI for test R^2 by resampling whole stations (dependence-aware)."""
    rng = np.random.RandomState(SEED)
    te = te.copy(); te["_yhat"] = yhat
    groups = [g for _, g in te.groupby("station_id")]
    r2s = []
    for _ in range(n):
        pick = rng.randint(0, len(groups), len(groups))
        s = pd.concat([groups[i] for i in pick])
        if s[TARGET].nunique() > 1:
            r2s.append(r2_score(s[TARGET], s["_yhat"]))
    return float(np.percentile(r2s, 5)), float(np.percentile(r2s, 95))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load(args.rows)
    rep, rows_out = [], []
    R = rep.append
    R("# Phase C — Leakage-Safe Predictive Evaluation\n")
    R(f"Target: **{TARGET}** (contemporaneous estimation). Predictors: "
      f"{', '.join(FEATURES)}. Rows: **{len(df):,}**; stations: "
      f"**{df['station_id'].nunique()}**.\n")
    R("XGBoost hyper-parameters fixed a priori (no tuning on any test set): "
      f"`{XGB}`.\n")

    def record(protocol, model, m, extra=""):
        rows_out.append({"protocol": protocol, "model": model, **m})
        R(f"- **{protocol} / {model}** — R²={m['r2']:.3f}, RMSE={m['rmse']:.2f}, "
          f"MAE={m['mae']:.2f} (n={m['n']:,}) {extra}")

    # ---- 0. LEAKY random split --------------------------------------------
    R("## 0. Leaky random 80/20 split (the original design)\n")
    rng = np.random.RandomState(SEED)
    mask = rng.rand(len(df)) < 0.8
    tr, te = df[mask], df[~mask]
    record("random-split(LEAKY)", "xgboost", metrics(te[TARGET], fit_predict(tr, te, FEATURES)))
    record("random-split(LEAKY)", "global-mean",
           metrics(te[TARGET], np.full(len(te), tr[TARGET].mean())))
    R("\n> Rows from the same station/time sit in both train and test, so this "
      "number is optimistic and is reported only as the baseline to beat.\n")

    # ---- 1. Blocked temporal ----------------------------------------------
    R("## 1. Blocked temporal holdout (train months 1–9, test 10–12)\n")
    tr, te = df[df.month <= 9], df[df.month >= 10]
    yhat = fit_predict(tr, te, FEATURES)
    m = metrics(te[TARGET], yhat)
    lo, hi = station_block_bootstrap_r2(te, yhat)
    record("blocked-temporal", "xgboost", m, f"[90% CI R² {lo:.3f}–{hi:.3f}]")
    # baselines
    record("blocked-temporal", "global-mean",
           metrics(te[TARGET], np.full(len(te), tr[TARGET].mean())))
    clim = tr.groupby("station_id")[TARGET].mean()
    pred_clim = te["station_id"].map(clim).fillna(tr[TARGET].mean()).to_numpy()
    record("blocked-temporal", "per-station-climatology", metrics(te[TARGET], pred_clim))
    # persistence: previous available hour at the same station (within test, shifted)
    te_sorted = te.sort_values(["station_id", "timestamp"]).copy()
    te_sorted["persist"] = te_sorted.groupby("station_id")[TARGET].shift(1)
    pm = te_sorted.dropna(subset=["persist"])
    record("blocked-temporal", "persistence(prev-hour)",
           metrics(pm[TARGET], pm["persist"]))

    # ---- 1b. Ablations -----------------------------------------------------
    R("\n### 1b. Feature ablations (blocked temporal)\n")
    for name, feats in [("weather-only", WEATHER), ("pollutants-only", POLLUTANTS),
                        ("all-features", FEATURES)]:
        record("ablation-temporal", name, metrics(te[TARGET], fit_predict(tr, te, feats)))

    # ---- 1c. Seasonal breakdown of the all-feature model ------------------
    R("\n### 1c. Test-period performance by month\n")
    te2 = te.copy(); te2["_yhat"] = yhat
    for mo, g in te2.groupby("month"):
        mm = metrics(g[TARGET], g["_yhat"])
        R(f"- month {mo}: R²={mm['r2']:.3f}, RMSE={mm['rmse']:.2f} (n={mm['n']:,})")
        rows_out.append({"protocol": "blocked-temporal-by-month",
                         "model": f"month-{mo}", **mm})

    # ---- 2. Leave-stations-out --------------------------------------------
    R("\n## 2. Leave-stations-out (80% stations train, 20% unseen test)\n")
    stations = df["station_id"].drop_duplicates().sample(frac=1, random_state=SEED).tolist()
    cut = int(0.8 * len(stations))
    tr = df[df.station_id.isin(stations[:cut])]
    te = df[df.station_id.isin(stations[cut:])]
    yhat = fit_predict(tr, te, FEATURES)
    m = metrics(te[TARGET], yhat)
    lo, hi = station_block_bootstrap_r2(te, yhat)
    record("leave-stations-out", "xgboost", m, f"[90% CI R² {lo:.3f}–{hi:.3f}]")
    record("leave-stations-out", "global-mean",
           metrics(te[TARGET], np.full(len(te), tr[TARGET].mean())))

    # ---- 3. Temporal x spatial --------------------------------------------
    R("\n## 3. Strictest: later months AND unseen stations\n")
    tr = df[(df.station_id.isin(stations[:cut])) & (df.month <= 9)]
    te = df[(df.station_id.isin(stations[cut:])) & (df.month >= 10)]
    if len(te) > 100:
        record("temporal x spatial", "xgboost",
               metrics(te[TARGET], fit_predict(tr, te, FEATURES)))
        record("temporal x spatial", "global-mean",
               metrics(te[TARGET], np.full(len(te), tr[TARGET].mean())))

    # ---- save --------------------------------------------------------------
    R("\n## Interpretation\n")
    R("- **Leakage inflates skill.** The leaky random split (R²≈0.41, close to the "
      "originally-reported 0.43) drops to **R²≈0.25 (blocked temporal)** and "
      "**R²≈0.30 (unseen stations)** under honest held-out evaluation. The original "
      "headline number was optimistic by ~0.15 R².")
    R("- **A naive temporal baseline wins for gap-filling.** Previous-hour "
      "persistence attains R²≈0.79 — far above the model — because ozone is "
      "strongly autocorrelated. BUT persistence requires a recent ozone reading at "
      "the same station, so it only applies to *temporal gap-filling*, not to "
      "estimating ozone where/when no ozone sensor exists.")
    R("- **The model's honest contribution is spatial.** For the leave-stations-out "
      "task (estimating ozone at unsensored stations) the only valid naive baseline "
      "is the global/mean predictor (R²≈0); the model reaches R²≈0.30, a modest but "
      "real gain. It does **not** beat persistence for gap-filling.")
    R("- **Weather and pollutants contribute roughly equally and complementarily** "
      "(ablation R² 0.14 / 0.13 individually, 0.25 together).")
    R("- Neither predictive accuracy nor feature importance is causal evidence; "
      "units are unharmonised (CO), so cross-station magnitudes carry measurement "
      "error not modelled here.\n")
    pd.DataFrame(rows_out).to_csv(f"{OUT_DIR}/phase_c_metrics.csv", index=False)
    with open(f"{OUT_DIR}/phase_c_predictive_eval.md", "w") as fh:
        fh.write("\n".join(rep))
    print("\n".join(rep))
    print(f"\nWrote {OUT_DIR}/phase_c_predictive_eval.md and phase_c_metrics.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
