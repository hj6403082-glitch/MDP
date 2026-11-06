"""
Robustness re-analysis for reviewers: re-run the leakage-safe ozone estimation using
ONLY the unit-consistent pollutants (NO, PM2.5, PM10 — plus weather), dropping the
unit-indeterminate species (CO, NO2, SO2) entirely, and compare against the
full-feature model. If the held-out skill and the incremental pollutant signal are
essentially unchanged, the headline result does not depend on the species whose units
are indeterminate. Blocked-temporal and leave-stations-out protocols; preprocessing fit
on train only; a-priori hyper-parameters.

    python audit/robustness_unit_consistent.py
"""
from __future__ import annotations
import glob, json
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_squared_error
from xgboost import XGBRegressor

R = "audit/reports"
TGT = "ozone"
UC_POLL = ["no", "pm25", "pm10"]          # unit-consistent (NO ppb; PM ug/m3)
IND_POLL = ["co", "no2", "so2"]           # unit-indeterminate (ppb/ug mix)
WX = ["temperature", "relative_humidity", "wind_speed", "pressure"]
SEED = 42
XGB = dict(n_estimators=250, max_depth=6, learning_rate=0.05, subsample=0.8,
           colsample_bytree=0.8, tree_method="hist", n_jobs=-1, random_state=SEED)


def load():
    fr = []
    for f in sorted(glob.glob("data/raw/telemetry/*.parquet")):
        d = pd.read_parquet(f)
        for c in [TGT] + UC_POLL + IND_POLL + WX:
            if c not in d.columns:
                d[c] = np.nan
        d["station_id"] = d["station_id"].astype(str)
        fr.append(d[["timestamp", "station_id", TGT] + UC_POLL + IND_POLL + WX])
    df = pd.concat(fr, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.dropna(subset=[TGT]).sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    df["month"] = df["timestamp"].dt.month
    return df


def m(y, p):
    return dict(r2=round(float(r2_score(y, p)), 3),
                rmse=round(float(np.sqrt(mean_squared_error(y, p))), 2), n=int(len(y)))


def fit_blocked(df, feats):
    tr, te = df[df.month <= 9], df[df.month >= 10]
    mdl = XGBRegressor(**XGB).fit(tr[feats].fillna(tr[feats].median()), tr[TGT])
    return m(te[TGT], mdl.predict(te[feats].fillna(tr[feats].median())))


def fit_lso(df, feats):
    gkf = GroupKFold(n_splits=5); yy, pp = [], []
    for tri, tei in gkf.split(df, groups=df.station_id):
        tr, te = df.iloc[tri], df.iloc[tei]
        med = tr[feats].median()
        mdl = XGBRegressor(**XGB).fit(tr[feats].fillna(med), tr[TGT])
        yy.append(te[TGT].values); pp.append(mdl.predict(te[feats].fillna(med)))
    return m(np.concatenate(yy), np.concatenate(pp))


def main() -> int:
    df = load()
    sets = {
        "weather only": WX,
        "weather + UC pollutants (NO,PM2.5,PM10)": WX + UC_POLL,
        "weather + ALL pollutants": WX + UC_POLL + IND_POLL,
    }
    rows = []
    for name, feats in sets.items():
        rows.append(dict(features=name, protocol="blocked-temporal", **fit_blocked(df, feats)))
        rows.append(dict(features=name, protocol="leave-stations-out", **fit_lso(df, feats)))
    out = pd.DataFrame(rows)
    out.to_csv(f"{R}/robustness_unit_consistent.csv", index=False)

    def g(name, proto):
        r = out[(out.features == name) & (out.protocol == proto)]
        return float(r.r2.iloc[0])
    inc_uc = g("weather + UC pollutants (NO,PM2.5,PM10)", "blocked-temporal") - g("weather only", "blocked-temporal")
    inc_all = g("weather + ALL pollutants", "blocked-temporal") - g("weather only", "blocked-temporal")
    summary = dict(
        blocked_weather_only=g("weather only", "blocked-temporal"),
        blocked_weather_UC=g("weather + UC pollutants (NO,PM2.5,PM10)", "blocked-temporal"),
        blocked_weather_all=g("weather + ALL pollutants", "blocked-temporal"),
        lso_weather_UC=g("weather + UC pollutants (NO,PM2.5,PM10)", "leave-stations-out"),
        lso_weather_all=g("weather + ALL pollutants", "leave-stations-out"),
        incremental_UC_beyond_weather=round(inc_uc, 3),
        incremental_ALL_beyond_weather=round(inc_all, 3),
        delta_from_dropping_indeterminate=round(g("weather + ALL pollutants", "blocked-temporal")
                                                - g("weather + UC pollutants (NO,PM2.5,PM10)", "blocked-temporal"), 3),
    )
    json.dump(summary, open(f"{R}/robustness_unit_consistent.json", "w"), indent=2)
    print(out.to_string(index=False))
    print("\nSUMMARY:"); print(json.dumps(summary, indent=2))
    print("\nNote: the NO->ozone causal edge already involves only unit-consistent "
          "variables (NO in ppb, ozone in ug/m3), so it is inherently unaffected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
