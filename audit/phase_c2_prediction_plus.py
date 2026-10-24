"""
Phase C2 - stronger predictive modelling (the runnable 'prediction, done right').

Builds on Phase C with three things the readiness review asked for:
  1. METEOROLOGY NORMALISATION - how much ozone variance is weather alone, and
     what pollutants add *beyond* weather (incremental R^2 on the held-out set).
  2. TIME / STATION EFFECTS - add hour-of-day & day-of-year harmonics and a
     train-only per-station ozone mean; report the incremental gain (and flag
     that station-mean helps gap-filling, not unsensored sites).
  3. A PROPER FORECASTING TASK - predict ozone at t+1h from information up to t,
     and compare honestly against previous-hour persistence.

All evaluation is blocked-temporal (train months 1-9, test 10-12), preprocessing
fit on train only, hyper-parameters fixed a priori. Contemporaneous estimation
and forecasting are reported separately. Nothing here is causal.

    python audit/phase_c2_prediction_plus.py
"""

from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_squared_error
from xgboost import XGBRegressor

OUT = "audit/reports"
TARGET = "ozone"
POLL = ["co", "no", "no2", "pm10", "pm25", "so2"]
WX = ["temperature", "relative_humidity", "wind_speed", "pressure"]
SEED = 42
XGB = dict(n_estimators=250, max_depth=6, learning_rate=0.05, subsample=0.8,
           colsample_bytree=0.8, tree_method="hist", n_jobs=-1, random_state=SEED)


def load():
    fr = []
    for f in sorted(glob.glob("data/raw/telemetry/*.parquet")):
        d = pd.read_parquet(f)
        for c in [TARGET] + POLL + WX:
            if c not in d.columns:
                d[c] = np.nan
        d["station_id"] = d["station_id"].astype(str)
        fr.append(d[["timestamp", "station_id", TARGET] + POLL + WX])
    df = pd.concat(fr, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.dropna(subset=[TARGET]).sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    h = df["timestamp"].dt.hour; doy = df["timestamp"].dt.dayofyear
    df["hr_sin"], df["hr_cos"] = np.sin(2*np.pi*h/24), np.cos(2*np.pi*h/24)
    df["doy_sin"], df["doy_cos"] = np.sin(2*np.pi*doy/365), np.cos(2*np.pi*doy/365)
    df["month"] = df["timestamp"].dt.month
    return df


def m(y, p):
    return {"r2": round(float(r2_score(y, p)), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(y, p))), 2), "n": int(len(y))}


def fit_pred(tr, te, feats):
    mdl = XGBRegressor(**XGB).fit(tr[feats], tr[TARGET])
    return mdl.predict(te[feats])


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    df = load()
    tr, te = df[df.month <= 9], df[df.month >= 10]
    rep = ["# Phase C2 - Stronger Predictive Modelling\n",
           f"Blocked temporal split; train {len(tr):,} rows, test {len(te):,} rows, "
           f"{df['station_id'].nunique()} stations.\n"]
    rows = []

    def rec(block, name, mm, note=""):
        rows.append({"block": block, "model": name, **mm})
        rep.append(f"- **{name}** - R2={mm['r2']}, RMSE={mm['rmse']} (n={mm['n']:,}) {note}")

    TIME = ["hr_sin", "hr_cos", "doy_sin", "doy_cos"]

    # ---- 1. meteorology normalisation / incremental value -----------------
    rep.append("## 1. Contemporaneous: what weather vs pollutants explain\n")
    rec("contemporaneous", "weather only", m(te[TARGET], fit_pred(tr, te, WX)))
    rec("contemporaneous", "pollutants only", m(te[TARGET], fit_pred(tr, te, POLL)))
    rec("contemporaneous", "weather + pollutants", m(te[TARGET], fit_pred(tr, te, WX + POLL)))
    rec("contemporaneous", "+ time harmonics", m(te[TARGET], fit_pred(tr, te, WX + POLL + TIME)))
    # train-only per-station mean (deweathered-style station effect)
    smean = tr.groupby("station_id")[TARGET].mean()
    tr2 = tr.assign(st_mean=tr["station_id"].map(smean))
    te2 = te.assign(st_mean=te["station_id"].map(smean).fillna(tr[TARGET].mean()))
    rec("contemporaneous", "+ station mean (train-only)",
        m(te2[TARGET], fit_pred(tr2, te2, WX + POLL + TIME + ["st_mean"])),
        "[station memorisation - helps gap-filling, NOT unsensored sites]")
    rep.append("\n> Incremental value of pollutants *beyond weather* is the honest "
               "signal; the station-mean gain is site memorisation and does not "
               "transfer to stations without an ozone sensor.\n")

    # ---- 2. forecasting t+1h vs persistence -------------------------------
    rep.append("## 2. Forecasting ozone at t+1h (vs persistence)\n")
    d = df.sort_values(["station_id", "timestamp"]).copy()
    g = d.groupby("station_id")
    d["dt_next"] = g["timestamp"].shift(-1)
    d["y_next"] = g[TARGET].shift(-1)
    # only keep consecutive hourly steps
    d["gap_ok"] = (d["dt_next"] - d["timestamp"]).dt.total_seconds().eq(3600)
    d["lag1"] = g[TARGET].shift(1)
    d["lag24"] = g[TARGET].shift(24)
    fc = d[d["gap_ok"] & d["y_next"].notna()].copy()
    ftr, fte = fc[fc.month <= 9], fc[fc.month >= 10]
    # persistence: predict y_next with current ozone
    rep.append(f"- **persistence (y(t+1)=y(t))** - "
               f"R2={m(fte['y_next'], fte[TARGET])['r2']}, "
               f"RMSE={m(fte['y_next'], fte[TARGET])['rmse']} (n={len(fte):,})")
    rows.append({"block": "forecast+1h", "model": "persistence", **m(fte["y_next"], fte[TARGET])})
    feats_fc = POLL + WX + TIME + ["lag1", "lag24", TARGET]
    mdl = XGBRegressor(**XGB).fit(ftr[feats_fc].assign(**{TARGET: ftr[TARGET]}), ftr["y_next"])
    pred = mdl.predict(fte[feats_fc])
    mm = m(fte["y_next"], pred)
    rows.append({"block": "forecast+1h", "model": "xgboost(+lags)", **mm})
    rep.append(f"- **xgboost (pollutants+weather+time+lags)** - R2={mm['r2']}, "
               f"RMSE={mm['rmse']} (n={mm['n']:,})")
    rep.append("")

    # ---- interpretation ----------------------------------------------------
    r2 = {(x['block'], x['model']): x['r2'] for x in rows}
    inc = r2[('contemporaneous', 'weather + pollutants')] - r2[('contemporaneous', 'weather only')]
    rep.append("## Interpretation\n")
    rep.append(f"- Weather alone explains R2={r2[('contemporaneous','weather only')]} of ozone; "
               f"adding pollutants raises it by **{inc:+.3f}** - the genuine incremental "
               "pollutant signal (small).")
    rep.append("- Time harmonics add a little; the station-mean 'gain' is memorisation "
               "that does not generalise to unsensored sites.")
    fc_gain = r2[('forecast+1h', 'xgboost(+lags)')] - r2[('forecast+1h', 'persistence')]
    rep.append(f"- For 1-hour-ahead forecasting, persistence gives "
               f"R2={r2[('forecast+1h','persistence')]}; the model gives "
               f"R2={r2[('forecast+1h','xgboost(+lags)')]} "
               f"({'beats persistence by %+.3f' % fc_gain if fc_gain>0 else 'does NOT beat persistence'}).")
    rep.append("- None of this is causal evidence.\n")

    pd.DataFrame(rows).to_csv(f"{OUT}/phase_c2_metrics.csv", index=False)
    json.dump({"incremental_pollutant_r2": round(inc, 3),
               "forecast_gain_over_persistence": round(fc_gain, 3)},
              open(f"{OUT}/phase_c2_summary.json", "w"), indent=2)
    open(f"{OUT}/phase_c2_prediction_plus.md", "w").write("\n".join(rep))
    print("\n".join(rep))
    print(f"\nWrote {OUT}/phase_c2_prediction_plus.md, phase_c2_metrics.csv, summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
