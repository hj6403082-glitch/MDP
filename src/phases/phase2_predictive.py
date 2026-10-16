"""
Phase 2a - Predictive Baseline with distributed XGBoost (``xgboost.spark``).

Goal (per CLAUDE.md):
    Establish a predictive baseline for a secondary pollutant (e.g. Ozone)
    using ``xgboost.spark.SparkXGBRegressor``, trained *distributed* across the
    Spark workers. This quantifies how much of the target is explainable by a
    strong supervised learner before Phase 2b attempts causal discovery, and it
    is the model Phase 3 will optimise against.

Distributed-training notes:
    ``SparkXGBRegressor`` runs one XGBoost worker per Spark task. We set
    ``num_workers`` to the cluster's parallelism so training fans out across
    executors rather than collapsing onto one. Feature vectors are assembled
    with MLlib's ``VectorAssembler`` and the data is **never** pulled to the
    driver - XGBoost's own Spark integration shuffles the partitions between
    workers.

Memory discipline (CLAUDE.md):
    * Only the needed columns are selected before assembly (scan-time pruning).
    * The training frame is cached ``MEMORY_AND_DISK`` so the train/eval passes
      do not re-read the source, while still spilling instead of OOM-ing.
    * No ``.toPandas()`` / ``.collect()`` of the feature data.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from config.pipeline_config import (
    IngestionConfig,
    OutputConfig,
    PipelineConfig,
    PredictiveConfig,
    load_config,
)
from src.phases.phase1_clustering import ingest_telemetry
from src.spark_utils import build_spark_session

logger = logging.getLogger("mdp.phase2.predictive")


def resolve_feature_columns(
    df, ingest: IngestionConfig, pred: PredictiveConfig
) -> List[str]:
    """Decide which columns are predictors.

    Explicit ``feature_columns`` win; otherwise infer "all numeric columns that
    are neither id columns nor the target". The target must exist and be
    numeric.
    """
    from pyspark.sql.types import NumericType

    if pred.target_column not in df.columns:
        raise ValueError(f"Target column {pred.target_column!r} not in data.")

    if pred.feature_columns:
        missing = [c for c in pred.feature_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Configured feature columns absent: {missing}")
        features = list(pred.feature_columns)
    else:
        exclude = set(ingest.id_columns) | {pred.target_column}
        features = [
            f.name for f in df.schema.fields
            if f.name not in exclude and isinstance(f.dataType, NumericType)
        ]
    if not features:
        raise ValueError("No usable feature columns for the predictive baseline.")
    logger.info("Predictive baseline: %d features -> target %r",
                len(features), pred.target_column)
    return features


def prepare_training_frame(df, features: List[str], target: str):
    """Select the modelling columns, drop rows with a null target, and assemble
    the MLlib feature vector. Returns a DataFrame with ``features``/``label``.

    Null *predictors* are kept as-is: XGBoost handles missing values natively
    (they take the learned default branch), so we must NOT impute them away and
    lose that signal. Only rows with a missing *target* are unusable.
    """
    from pyspark.ml.feature import VectorAssembler
    from pyspark.sql import functions as F

    narrow = df.select(*features, target).where(
        F.col(target).isNotNull() & ~F.isnan(F.col(target))
    )
    # handleInvalid="keep" lets null predictors flow through as NaN, which the
    # XGBoost estimator interprets as "missing" (missing=float("nan")).
    assembler = VectorAssembler(
        inputCols=features, outputCol="features", handleInvalid="keep"
    )
    assembled = assembler.transform(narrow).select(
        "features", F.col(target).cast("double").alias("label")
    )
    return assembled


def build_regressor(pred: PredictiveConfig, num_workers: int):
    """Instantiate a distributed ``SparkXGBRegressor``."""
    # Local import so config/tests don't require xgboost installed.
    from xgboost.spark import SparkXGBRegressor

    return SparkXGBRegressor(
        features_col="features",
        label_col="label",
        prediction_col="prediction",
        # ---- distributed training layout ----
        num_workers=num_workers,     # one XGBoost worker per Spark task
        # ---- missing-value handling ----
        missing=float("nan"),        # matches VectorAssembler "keep" NaNs
        # ---- core hyper-parameters ----
        n_estimators=pred.n_estimators,
        max_depth=pred.max_depth,
        learning_rate=pred.learning_rate,
        subsample=pred.subsample,
        colsample_bytree=pred.colsample_bytree,
        random_state=pred.seed,
    )


def evaluate(predictions) -> Dict[str, float]:
    """Compute RMSE, MAE and R2 on a predictions DataFrame (distributed)."""
    from pyspark.ml.evaluation import RegressionEvaluator

    def _metric(name: str) -> float:
        return RegressionEvaluator(
            labelCol="label", predictionCol="prediction", metricName=name
        ).evaluate(predictions)

    return {"rmse": _metric("rmse"), "mae": _metric("mae"), "r2": _metric("r2")}


def run_predictive_baseline(config: Optional[PipelineConfig] = None) -> Dict:
    """Train and evaluate the distributed XGBoost baseline; persist model+metrics."""
    cfg = config or load_config()
    spark = build_spark_session(cfg.spark)
    from pyspark import StorageLevel

    try:
        df = ingest_telemetry(spark, cfg.ingestion)
        features = resolve_feature_columns(df, cfg.ingestion, cfg.predictive)
        data = prepare_training_frame(df, features, cfg.predictive.target_column)

        # Cache before the split so train + eval reuse one materialisation.
        data = data.persist(StorageLevel.MEMORY_AND_DISK)

        train, test = data.randomSplit(
            [cfg.predictive.train_fraction, 1.0 - cfg.predictive.train_fraction],
            seed=cfg.predictive.seed,
        )

        # Auto-detect worker count from the live cluster when not pinned.
        num_workers = cfg.predictive.num_workers or max(
            1, spark.sparkContext.defaultParallelism
        )
        logger.info("Training SparkXGBRegressor across %d workers", num_workers)

        model = build_regressor(cfg.predictive, num_workers).fit(train)
        metrics = evaluate(model.transform(test))
        metrics.update({
            "target": cfg.predictive.target_column,
            "n_features": len(features),
            "num_workers": num_workers,
        })
        logger.info("Baseline metrics: %s", metrics)

        data.unpersist()

        base = cfg.output.output_path.rstrip("/")
        model.write().overwrite().save(f"{base}/{cfg.output.xgb_model_subpath}")

        import json
        spark.createDataFrame(
            [(json.dumps(metrics, sort_keys=True),)], ["metrics_json"]
        ).coalesce(1).write.mode("overwrite").text(
            f"{base}/{cfg.output.xgb_metrics_subpath}"
        )
        logger.info("Phase 2a artefacts written under %s", base)
        return metrics
    finally:
        spark.stop()


if __name__ == "__main__":
    result = run_predictive_baseline()
    logger.info("Phase 2a complete: %s", result)
