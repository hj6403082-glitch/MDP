"""
Supporting numbers for the manuscript (paper_latex/). Computes, from the committed
data only: (1) per-pollutant summary statistics; (2) a Ridge-regression baseline for
ozone under random / blocked-temporal / leave-stations-out protocols; (3) a
station x hour x month diurnal-seasonal mean baseline (blocked-temporal); and
(4) generational distance / hypervolume error of the saved NSGA-II policies against
the exact Pareto front. Writes CSVs to audit/reports/ and prints a summary.

    python audit/paper_support.py
"""
from __future__ import annotations
import glob, json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

R = "audit/reports"
TGT = "ozone"
POLL = ["co", "no", "no2", "pm10", "pm25", "so2"]
WX = ["temperature", "relative_humidity", "wind_speed", "pressure"]
FEAT = POLL + WX
SEED = 42


def load():
    fr = []
    for f in sorted(glob.glob("data/raw/telemetry/*.parquet")):
        d = pd.read_parquet(f)
        for c in [TGT] + FEAT:
            if c not in d.columns:
                d[c] = np.nan
        d["station_id"] = d["station_id"].astype(str)
        fr.append(d[["timestamp", "station_id", TGT] + FEAT])
    df = pd.concat(fr, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.dropna(subset=[TGT]).sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    df["month"] = df["timestamp"].dt.month
    df["hour"] = df["timestamp"].dt.hour
    return df


def met(y, p):
    return dict(r2=round(float(r2_score(y, p)), 3),
                rmse=round(float(np.sqrt(mean_squared_error(y, p))), 2),
                mae=round(float(mean_absolute_error(y, p)), 2), n=int(len(y)))


def ridge_fit(tr, te):
    mu = tr[FEAT].median()
    Xtr = tr[FEAT].fillna(mu); Xte = te[FEAT].fillna(mu)
    m = (Xtr.mean(), Xtr.std().replace(0, 1))
    Xtr = (Xtr - m[0]) / m[1]; Xte = (Xte - m[0]) / m[1]
    mdl = Ridge(alpha=1.0, random_state=SEED).fit(Xtr, tr[TGT])
    return mdl.predict(Xte)


def main() -> int:
    df = load()
    rows = []

    # ---- 1. summary statistics -------------------------------------------
    # total present rows across the full station grid for missingness
    stats = []
    av = pd.read_csv(f"{R}/pollutant_availability.csv").set_index("variable")
    for c in [TGT] + POLL:
        s = df[c].dropna()
        miss = 1 - av.loc[c, "nonnull_frac_of_present_rows"] if c in av.index else np.nan
        stats.append(dict(pollutant=c.upper(),
                          mean=round(float(s.mean()), 2), std=round(float(s.std()), 2),
                          p5=round(float(s.quantile(0.05)), 2),
                          p95=round(float(s.quantile(0.95)), 2),
                          missing_frac=round(float(miss), 3)))
    pd.DataFrame(stats).to_csv(f"{R}/paper_summary_stats.csv", index=False)

    # ---- 2. Ridge under three protocols ----------------------------------
    rng = np.random.RandomState(SEED)
    # random split
    idx = rng.permutation(len(df)); cut = int(0.7 * len(df))
    tr, te = df.iloc[idx[:cut]], df.iloc[idx[cut:]]
    rows.append(dict(model="Ridge", protocol="random-split(LEAKY)", **met(te[TGT], ridge_fit(tr, te))))
    # blocked temporal (Q1-Q3 train, Q4 test)
    tr, te = df[df.month <= 9], df[df.month >= 10]
    rows.append(dict(model="Ridge", protocol="blocked-temporal", **met(te[TGT], ridge_fit(tr, te))))
    # leave-stations-out (5-fold GroupKFold, pooled predictions)
    gkf = GroupKFold(n_splits=5); yy, pp = [], []
    for tri, tei in gkf.split(df, groups=df.station_id):
        tr2, te2 = df.iloc[tri], df.iloc[tei]
        yy.append(te2[TGT].values); pp.append(ridge_fit(tr2, te2))
    rows.append(dict(model="Ridge", protocol="leave-stations-out",
                     **met(np.concatenate(yy), np.concatenate(pp))))

    # ---- 3. diurnal-seasonal (station x hour x month) mean ---------------
    tr, te = df[df.month <= 9], df[df.month >= 10]
    key = ["station_id", "hour", "month"]
    cell = tr.groupby(key)[TGT].mean()
    smean = tr.groupby("station_id")[TGT].mean(); gmean = tr[TGT].mean()
    pred = te.set_index(key).index.map(cell)
    pred = pd.Series(pred, index=te.index).astype(float)
    pred = pred.fillna(te.station_id.map(smean)).fillna(gmean)
    rows.append(dict(model="DiurnalSeasonalMean(st x hr x mo)", protocol="blocked-temporal",
                     **met(te[TGT], pred.values)))

    pd.DataFrame(rows).to_csv(f"{R}/paper_baselines.csv", index=False)

    # ---- 4. Pareto GD / HVE ----------------------------------------------
    front = pd.read_csv(f"{R}/exact_pareto_front.csv")[["ozone", "pm25"]].values
    saved = pd.read_parquet(glob.glob("results/out/phase3/pareto_front/*.parquet")[0])
    pts = saved[["ozone", "pm25"]].values
    d = np.sqrt(((pts[:, None, :] - front[None, :, :]) ** 2).sum(-1)).min(1)  # dist to front
    gd = float(np.sqrt((d ** 2).mean()))
    # hypervolume (2D, minimisation) wrt a shared reference point
    ref = np.array([max(pts[:, 0].max(), front[:, 0].max()),
                    max(pts[:, 1].max(), front[:, 1].max())]) + 0.05
    def hv(P):
        P = P[np.argsort(P[:, 0])]
        nd, best = [], np.inf
        for p in P:
            if p[1] < best:
                nd.append(p); best = p[1]
        nd = np.array(nd); area = 0.0; prev_x = ref[0]
        for p in nd[::-1]:
            area += (prev_x - p[0]) * (ref[1] - p[1]); prev_x = p[0]
        return area
    hv_front, hv_saved = hv(front), hv(pts)
    hve = (hv_front - hv_saved) / hv_front
    pareto = dict(generational_distance=round(gd, 4),
                  hv_front=round(hv_front, 4), hv_saved=round(hv_saved, 4),
                  hypervolume_error_frac=round(float(hve), 4))
    json.dump(pareto, open(f"{R}/paper_pareto_metrics.json", "w"), indent=2)

    print("== summary stats =="); print(pd.DataFrame(stats).to_string(index=False))
    print("\n== baselines =="); print(pd.DataFrame(rows).to_string(index=False))
    print("\n== pareto =="); print(json.dumps(pareto, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
