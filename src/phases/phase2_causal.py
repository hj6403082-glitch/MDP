"""
Phase 2b - Causal Discovery with DirectLiNGAM.

Goal (per CLAUDE.md):
    Uncover the causal Directed Acyclic Graph (DAG) and the linear Structural
    Equation Models (SEMs) that link the *primary* pollutants (directly
    emitted: NO, NO2, CO, SO2, VOCs...) to the *secondary* pollutants that form
    from them in the atmosphere (Ozone, PM2.5...). This maps the atmospheric
    regimes that Phase 3 will then optimise.

Why DirectLiNGAM:
    DirectLiNGAM (``lingam.DirectLiNGAM``) identifies a *unique* causal order
    and the structural coefficients for linear non-Gaussian data - exactly the
    setting of pollutant chemistry, where the driving emissions are decidedly
    non-Gaussian. It returns both the DAG and the SEM coefficients in one fit.

Memory discipline (CLAUDE.md - important):
    DirectLiNGAM is a **single-node** algorithm: it operates on an in-memory
    ``n_samples x n_variables`` matrix and cannot be distributed. We therefore
    do all the heavy lifting in Spark first - column pruning, mean-imputation,
    and most importantly a **bounded random sample** - and only then pull that
    *bounded* sample (default <= 50k rows x a handful of pollutant columns, a
    few MB) to the driver. The full telemetry is never collected. This is the
    deliberate, documented exception to "no single-node work": the sample size
    is capped so the driver footprint stays constant regardless of how large
    the source telemetry grows.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from config.pipeline_config import (
    CausalConfig,
    OutputConfig,
    PipelineConfig,
    load_config,
)
from src.phases.phase1_clustering import ingest_telemetry
from src.spark_utils import build_spark_session

logger = logging.getLogger("mdp.phase2.causal")


def resolve_pollutant_columns(df, cfg: CausalConfig) -> Tuple[List[str], List[str]]:
    """Return the (primary, secondary) pollutant columns actually present.

    Configured names that are missing from the data are dropped with a warning
    rather than failing the whole run, since station coverage varies. At least
    one primary and one secondary must survive.
    """
    present = set(df.columns)
    primary = [c for c in cfg.primary_pollutants if c in present]
    secondary = [c for c in cfg.secondary_pollutants if c in present]

    missing = [c for c in (cfg.primary_pollutants + cfg.secondary_pollutants)
               if c not in present]
    if missing:
        logger.warning("Configured pollutants absent from data (skipped): %s", missing)
    if not primary or not secondary:
        raise ValueError(
            "Need at least one primary and one secondary pollutant present; "
            f"got primary={primary}, secondary={secondary}."
        )
    return primary, secondary


def collect_bounded_sample(df, columns: List[str], cfg: CausalConfig):
    """Clean, bound-sample and bring the pollutant matrix to the driver.

    All reduction happens in Spark; only the capped sample crosses to the
    driver. Returns a pandas DataFrame with exactly ``columns`` (order
    preserved) - the matrix DirectLiNGAM consumes.
    """
    from pyspark.ml.feature import Imputer
    from pyspark.sql import functions as F

    # 1) Prune to just the pollutant columns so Spark scans/shuffles minimal data.
    narrow = df.select(*columns)

    # 2) Mean-impute missing readings (distributed). LiNGAM needs a full matrix;
    #    dropping rows with any null would bias toward fully-reporting stations.
    imputed_cols = [f"{c}__imp" for c in columns]
    narrow = Imputer(
        inputCols=columns, outputCols=imputed_cols, strategy="mean"
    ).fit(narrow).transform(narrow).select(
        *[F.col(ic).alias(c) for ic, c in zip(imputed_cols, columns)]
    )

    # 3) Bounded random sample -> constant driver footprint. We slightly
    #    over-sample the target fraction then hard-cap with limit() so the
    #    driver collect can never exceed max_sample_rows.
    total = narrow.count()
    if total > cfg.max_sample_rows:
        fraction = min(1.0, (cfg.max_sample_rows / total) * 1.1)
        narrow = narrow.sample(withReplacement=False, fraction=fraction,
                               seed=cfg.seed).limit(cfg.max_sample_rows)
        logger.info("Sampled %d of %d rows for DirectLiNGAM (driver-bounded).",
                    cfg.max_sample_rows, total)
    else:
        logger.info("Collecting all %d rows for DirectLiNGAM (within cap).", total)

    # 4) Only now cross to the driver. Arrow (enabled in SparkConfig) makes this
    #    conversion cheap; the result is bounded by construction.
    pdf = narrow.toPandas()
    # Guard against any residual non-finite values from all-null imputed columns.
    pdf = pdf.dropna(axis=0, how="any")
    if pdf.shape[0] < 2:
        raise ValueError("Too few complete rows for causal discovery after cleaning.")
    return pdf[columns]


def build_prior_knowledge(columns: List[str], primary: List[str],
                          secondary: List[str]):
    """Build a DirectLiNGAM prior-knowledge matrix forbidding secondary ->
    primary edges.

    lingam convention: ``pk[i, j]`` encodes the directed path ``j -> i``:
        0  = no such path (forbidden),
       -1  = no prior knowledge (let the algorithm decide).
    Secondary pollutants are formed *from* primaries downstream, so a secondary
    cannot cause a primary emission. We encode that physical/temporal law so the
    recovered DAG is chemically plausible. All other relations stay ``-1``.
    """
    import numpy as np

    idx = {c: i for i, c in enumerate(columns)}
    n = len(columns)
    pk = -np.ones((n, n), dtype=int)  # default: no prior knowledge
    for s in secondary:
        for p in primary:
            pk[idx[p], idx[s]] = 0  # forbid path secondary(s) -> primary(p)
    return pk


def fit_direct_lingam(pdf, columns: List[str], primary: List[str],
                      secondary: List[str], cfg: CausalConfig):
    """Standardise, fit DirectLiNGAM, and return the model plus the
    standardised adjacency matrix.

    Standardisation makes the structural coefficients *comparable across edges*
    (they become path strengths in standard-deviation units), so a single
    ``edge_threshold`` is meaningful for every variable.
    """
    import numpy as np
    from lingam import DirectLiNGAM

    X = pdf.to_numpy(dtype=float)
    # Standardise on the driver (the sample is small/bounded).
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0  # avoid divide-by-zero for a constant column
    Xz = (X - mean) / std

    prior = (build_prior_knowledge(columns, primary, secondary)
             if cfg.use_prior_knowledge else None)
    model = DirectLiNGAM(prior_knowledge=prior, random_state=cfg.seed)
    model.fit(Xz)
    # adjacency_matrix_[i, j] = coefficient of path j -> i in x = Bx + e.
    # Return the fitted scalers so z-space results can be mapped back to the
    # original concentration units (and so the run is reproducible).
    return model, np.asarray(model.adjacency_matrix_), mean, std


def extract_dag_and_sem(adjacency, columns: List[str], causal_order: List[int],
                        cfg: CausalConfig) -> Tuple[List[Dict], List[Dict]]:
    """Turn the adjacency matrix into (edge list, SEM equations).

    Returns:
        edges: ``[{source, target, coefficient}]`` for |coef| >= threshold.
        sems:  ``[{target, equation, order}]`` - one structural equation per
               variable, ordered by the recovered causal order.
    """
    n = len(columns)
    edges: List[Dict] = []
    for i in range(n):          # effect
        for j in range(n):      # cause
            coef = float(adjacency[i][j])
            if i != j and abs(coef) >= cfg.edge_threshold:
                edges.append({
                    "source": columns[j],
                    "target": columns[i],
                    "coefficient": coef,
                })

    # Build readable SEMs: x_i = c1*x_a + c2*x_b + ... + e_i
    order_rank = {var_idx: rank for rank, var_idx in enumerate(causal_order)}
    sems: List[Dict] = []
    for i in range(n):
        terms = [
            f"{adjacency[i][j]:+.4f}*{columns[j]}"
            for j in range(n)
            if i != j and abs(adjacency[i][j]) >= cfg.edge_threshold
        ]
        rhs = " ".join(terms) if terms else "0"
        sems.append({
            "target": columns[i],
            "equation": f"{columns[i]} = {rhs} + e_{columns[i]}",
            "order": order_rank.get(i, -1),
        })
    sems.sort(key=lambda d: d["order"])
    return edges, sems


def run_causal_discovery(config: Optional[PipelineConfig] = None, spark=None) -> Dict:
    """Run Phase 2b end-to-end and persist the DAG + SEM artefacts.

    Pass an existing ``spark`` session to share one across phases; when omitted
    this function creates and stops its own.
    """
    cfg = config or load_config()
    owns_spark = spark is None
    if spark is None:
        spark = build_spark_session(cfg.spark)

    try:
        df = ingest_telemetry(spark, cfg.ingestion)
        primary, secondary = resolve_pollutant_columns(df, cfg.causal)
        # Keep a deterministic column order: primaries first, then secondaries.
        columns = primary + secondary

        pdf = collect_bounded_sample(df, columns, cfg.causal)
        model, adjacency, scaler_mean, scaler_std = fit_direct_lingam(
            pdf, columns, primary, secondary, cfg.causal
        )
        causal_order = [int(i) for i in model.causal_order_]
        edges, sems = extract_dag_and_sem(adjacency, columns, causal_order, cfg.causal)

        ordered_names = [columns[i] for i in causal_order]
        logger.info("Recovered causal order: %s", " -> ".join(ordered_names))
        logger.info("Recovered %d edges above threshold %.3f",
                    len(edges), cfg.causal.edge_threshold)

        # Persist via Spark so paths can be GCS. Both artefacts are small.
        base = cfg.output.output_path.rstrip("/")
        if edges:
            spark.createDataFrame(edges).coalesce(1).write.mode("overwrite") \
                .parquet(f"{base}/{cfg.output.causal_dag_subpath}")
        spark.createDataFrame(sems).coalesce(1).write.mode("overwrite") \
            .parquet(f"{base}/{cfg.output.causal_sem_subpath}")

        # Persist a reproducibility manifest: the fitted variable list and order,
        # per-variable scaler (mean/std) so z-space maps back to concentrations,
        # the full standardized adjacency, thresholds, seed, prior-knowledge flag,
        # sample size and library versions. Without this the response model (and
        # any downstream scenario analysis) is not reproducible or interpretable.
        import json as _json
        import sys as _sys
        try:
            import lingam as _lingam
            _lingam_ver = getattr(_lingam, "__version__", "unknown")
        except Exception:  # noqa: BLE001
            _lingam_ver = "unknown"
        manifest = {
            "schema_version": 1,
            "columns": list(columns),
            "causal_order": ordered_names,
            "scaler_mean": {c: float(m) for c, m in zip(columns, scaler_mean)},
            "scaler_std": {c: float(s) for c, s in zip(columns, scaler_std)},
            "adjacency_standardized": [[float(v) for v in row] for row in adjacency],
            "edge_threshold": float(cfg.causal.edge_threshold),
            "seed": int(cfg.causal.seed),
            "used_prior_knowledge": bool(cfg.causal.use_prior_knowledge),
            "n_samples_used": int(pdf.shape[0]),
            "standardized_space": True,
            "space_note": ("coefficients and interventions are in standardized "
                           "AMBIENT-CONCENTRATION z-space; not emissions"),
            "versions": {"python": _sys.version.split()[0], "lingam": _lingam_ver},
        }
        spark.createDataFrame([(_json.dumps(manifest, sort_keys=True),)],
                              ["manifest_json"]).coalesce(1).write.mode("overwrite") \
            .text(f"{base}/{cfg.output.causal_manifest_subpath}")

        result = {
            "columns": columns,
            "primary_pollutants": primary,
            "secondary_pollutants": secondary,
            "causal_order": ordered_names,
            "n_edges": len(edges),
            "edges": edges,
            "sems": sems,
            "used_prior_knowledge": cfg.causal.use_prior_knowledge,
            "n_samples_used": int(pdf.shape[0]),
        }
        logger.info("Phase 2b artefacts written under %s", base)
        return result
    finally:
        if owns_spark:
            spark.stop()


if __name__ == "__main__":
    out = run_causal_discovery()
    logger.info("Phase 2b complete: order=%s, edges=%d",
                out["causal_order"], out["n_edges"])
