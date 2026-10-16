"""
Phase 3b - Explainability (XAI) with SHAP on the Phase 2a XGBoost baseline.

Goal (per CLAUDE.md):
    Extract feature importance from the trained XGBoost baseline using SHAP and
    render a summary plot, visually demonstrating which chemical species - and
    which interactions - drive the model's predictions of the target pollutant.

Why SHAP (not just XGBoost gain):
    SHAP values are additive, per-prediction attributions with sound game-
    theoretic footing, so the summary plot shows both the *magnitude* and the
    *direction* of each species' effect across the sample - far more
    informative than a single gain bar chart for understanding atmospheric
    chemistry drivers.

Memory discipline (CLAUDE.md):
    ``shap.TreeExplainer`` is single-node. We therefore reuse the Phase 2
    pattern: Spark assembles and **bound-samples** the feature rows, and only
    that capped sample (default <= 5k rows) is pulled to the driver. The full
    telemetry and the distributed model are never materialised on one node.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from config.pipeline_config import (
    PipelineConfig,
    XaiConfig,
    load_config,
)
from src.phases.phase1_clustering import ingest_telemetry
from src.phases.phase2_predictive import resolve_feature_columns
from src.spark_utils import build_spark_session

logger = logging.getLogger("mdp.phase3.xai")


def collect_feature_sample(df, features: List[str], xai: XaiConfig):
    """Bound-sample the predictor rows and bring just that sample to the driver.

    Mirrors the memory-safe collection used for LiNGAM: all reduction in Spark,
    a hard row cap, and only then a (bounded) pandas conversion. Returns a
    pandas DataFrame whose columns are exactly ``features`` in order - the matrix
    SHAP consumes. Null predictors are preserved as NaN so they map onto the
    XGBoost "missing" branch, matching how the model was trained.
    """
    narrow = df.select(*features)
    total = narrow.count()
    if total > xai.max_sample_rows:
        fraction = min(1.0, (xai.max_sample_rows / total) * 1.1)
        narrow = narrow.sample(withReplacement=False, fraction=fraction,
                               seed=xai.seed).limit(xai.max_sample_rows)
        logger.info("Sampled %d of %d rows for SHAP (driver-bounded).",
                    xai.max_sample_rows, total)
    else:
        logger.info("Collecting all %d rows for SHAP (within cap).", total)
    pdf = narrow.toPandas()
    return pdf[features]


def load_booster(spark, cfg: PipelineConfig):
    """Load the saved Phase 2a Spark XGBoost model and return its native
    ``xgboost.Booster``.

    SHAP's ``TreeExplainer`` works directly on the booster, so we unwrap the
    Spark model rather than running distributed inference.
    """
    from xgboost.spark import SparkXGBRegressorModel

    base = cfg.output.output_path.rstrip("/")
    model_path = f"{base}/{cfg.output.xgb_model_subpath}"
    spark_model = SparkXGBRegressorModel.load(model_path)
    booster = spark_model.get_booster()
    logger.info("Loaded XGBoost booster from %s", model_path)
    return booster


def compute_shap(booster, pdf, features: List[str]):
    """Compute SHAP values for the sample. Returns ``(shap_values, explainer)``.

    We label the booster's feature names so the plot shows species names rather
    than ``f0, f1, ...``. The booster was trained on a VectorAssembler output,
    which uses positional features, so ``features`` must be in the exact
    training order (it is - we reuse ``resolve_feature_columns``).
    """
    import shap

    booster.feature_names = list(features)
    explainer = shap.TreeExplainer(booster)
    shap_values = explainer.shap_values(pdf)
    return shap_values, explainer


def render_summary_plot(shap_values, pdf, features: List[str], xai: XaiConfig) -> str:
    """Render and save the SHAP summary (beeswarm) plot to a PNG on the driver.

    Uses the non-interactive Agg backend so it works on a headless Dataproc
    driver. Returns the path written.
    """
    import matplotlib
    matplotlib.use("Agg")  # headless; must precede pyplot import
    import matplotlib.pyplot as plt
    import shap

    plt.figure()
    shap.summary_plot(
        shap_values, pdf, feature_names=features,
        max_display=xai.max_display, show=False,
    )
    plt.tight_layout()
    plt.savefig(xai.summary_plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("SHAP summary plot saved to %s", xai.summary_plot_path)
    return xai.summary_plot_path


def mean_abs_importance(shap_values, features: List[str]) -> List[Dict]:
    """Global importance = mean(|SHAP|) per feature, descending."""
    import numpy as np

    mean_abs = np.abs(shap_values).mean(axis=0)
    ranked = sorted(
        ({"feature": f, "mean_abs_shap": float(v)}
         for f, v in zip(features, mean_abs)),
        key=lambda d: d["mean_abs_shap"], reverse=True,
    )
    return ranked


def run_xai(config: Optional[PipelineConfig] = None) -> Dict:
    """Run Phase 3b end-to-end: load model, explain a bounded sample, save the
    plot and the importance table.
    """
    cfg = config or load_config()
    spark = build_spark_session(cfg.spark)

    try:
        df = ingest_telemetry(spark, cfg.ingestion)
        features = resolve_feature_columns(df, cfg.ingestion, cfg.predictive)
        pdf = collect_feature_sample(df, features, cfg.xai)

        booster = load_booster(spark, cfg)
        shap_values, _ = compute_shap(booster, pdf, features)

        plot_path = render_summary_plot(shap_values, pdf, features, cfg.xai)
        importance = mean_abs_importance(shap_values, features)

        base = cfg.output.output_path.rstrip("/")
        spark.createDataFrame(importance).coalesce(1).write.mode("overwrite") \
            .parquet(f"{base}/{cfg.output.shap_importance_subpath}")

        logger.info("Top drivers: %s",
                    ", ".join(f"{d['feature']}={d['mean_abs_shap']:.3f}"
                              for d in importance[:5]))
        return {
            "target": cfg.predictive.target_column,
            "n_samples_explained": int(pdf.shape[0]),
            "summary_plot_path": plot_path,
            "importance": importance,
        }
    finally:
        spark.stop()


if __name__ == "__main__":
    result = run_xai()
    logger.info("Phase 3b complete: plot=%s", result["summary_plot_path"])
