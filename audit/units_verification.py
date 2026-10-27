"""
Units verification: reconcile the AUTHORITATIVE OpenAQ per-sensor unit metadata
(audit/reports/units_authoritative.csv, produced by fetch_units.py with a key)
against the pollutants used in the pipeline.

Key result: CO, NO2 and SO2 have duplicate sensors reporting in BOTH ppb and
ug/m3 at almost every station, while NO (ppb), ozone (ug/m3), PM2.5 and PM10
(ug/m3) are unit-consistent. The stored telemetry has one value per pollutant
per station-hour with no per-sensor provenance, so for the mixed pollutants the
unit of a given stored value is INDETERMINATE and cannot be harmonized post-hoc;
it requires re-collection with per-sensor unit capture (now done in
data_collection.py). Quantitative cross-station claims should rest only on the
unit-consistent pollutants.

    python audit/units_verification.py
"""
from __future__ import annotations
import pandas as pd

SRC = "audit/reports/units_authoritative.csv"
OUT_MD = "audit/reports/units_verification.md"
OUT_CSV = "audit/reports/units_verdict.csv"
POLL = ["co", "no", "no2", "ozone", "pm10", "pm25", "so2"]


def main() -> int:
    u = pd.read_csv(SRC)
    rows = []
    for p in POLL:
        sub = u[u.parameter == p]
        nst = sub.station_id.nunique()
        both = int((sub.groupby("station_id").unit.nunique() > 1).sum())
        units = sorted(sub.unit.unique())
        if len(units) == 1:
            verdict = "uniform"
        elif both <= 1:
            verdict = "near-uniform"
        else:
            verdict = "mixed (per-station duplicate sensors)"
        usable = verdict in ("uniform", "near-uniform")
        rows.append(dict(parameter=p, units="; ".join(units), n_stations=nst,
                         stations_multi_unit=both, verdict=verdict,
                         unit_consistent=usable))
    v = pd.DataFrame(rows)
    v.to_csv(OUT_CSV, index=False)

    consistent = v[v.unit_consistent].parameter.tolist()
    mixed = v[~v.unit_consistent].parameter.tolist()

    md = ["# Units Verification (authoritative)\n",
          "Source: `audit/reports/units_authoritative.csv` — per-sensor unit "
          "metadata fetched from the OpenAQ v3 API with an API key "
          "(`audit/fetch_units.py`). This is the authoritative record of what unit "
          "each sensor reports, and it supersedes any unit inferred from values.\n",
          "## Verdict by pollutant\n",
          "| Pollutant | Unit(s) reported | Stations | Stations with >1 unit | Verdict |",
          "|-----------|------------------|----------|-----------------------|---------|"]
    for r in rows:
        md.append(f"| {r['parameter'].upper()} | {r['units']} | {r['n_stations']} | "
                  f"{r['stations_multi_unit']} | **{r['verdict']}** |")
    md += ["",
           f"**Unit-consistent (safe for quantitative cross-station use):** "
           f"{', '.join(x.upper() for x in consistent)}.",
           f"**Unit-indeterminate (duplicate ppb + ug/m3 sensors per station):** "
           f"{', '.join(x.upper() for x in mixed)}.",
           "",
           "## What this means\n",
           "- `ppb` is a mixing ratio; `ug/m3` is a mass concentration. They are "
           "not comparable without converting via molecular weight and ambient "
           "temperature/pressure.",
           "- For CO, NO2 and SO2, almost every station carries BOTH a ppb and a "
           "ug/m3 sensor. The stored dataset keeps a single value per pollutant per "
           "station-hour with no record of which sensor produced it, so the unit of "
           "any given CO/NO2/SO2 value is **indeterminate** and cannot be recovered "
           "or harmonized from the stored data alone.",
           "- This **corrects an earlier value-based inference** that CO was "
           "uniform: the authoritative metadata shows CO is mixed. The authoritative "
           "source governs.",
           "",
           "## Impact on the analyses (what survives)\n",
           "- **Ozone prediction** — the target is ug/m3 at all but one sensor, so "
           "the leakage-safe R2 result is unaffected.",
           "- **NO -> ozone** — NO is ppb at every station (unit-consistent), so the "
           "one stable association rests on a clean variable.",
           "- **PM2.5 / PM10** — uniform ug/m3.",
           "- **CO, NO2, SO2 as features** — unit-indeterminate; cross-station "
           "quantitative use is unreliable and should be dropped or explicitly "
           "caveated. Within-station temporal structure may still hold if a station "
           "used one sensor consistently, but this cannot be verified from the data.",
           "",
           "## Fix\n",
           "Re-collect retaining per-sensor unit (and sensor id) so each value's "
           "unit is known; convert ppb to ug/m3 per species before pooling. "
           "`data_collection.py` now captures per-sensor units for this reason.\n"]
    open(OUT_MD, "w").write("\n".join(md))
    print("\n".join(md))
    print(f"\nWrote {OUT_MD} and {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
