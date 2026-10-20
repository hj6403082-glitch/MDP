"""
Central configuration for the Causal AI for Air Pollution pipeline.

Keeping all tunables in one module avoids scattering magic strings/numbers
across the three phases and makes the pipeline portable between a local dev
box and the Google Cloud Dataproc cluster (where paths point at GCS buckets).

Every value can be overridden from the environment so the same code runs in
CI, locally, and on Dataproc without edits (12-factor style).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


def _env(key: str, default: str) -> str:
    """Read an env var, falling back to a default. Trivial helper kept so the
    dataclass defaults below stay readable."""
    return os.environ.get(key, default)


@dataclass(frozen=True)
class IngestionConfig:
    """Where the raw telemetry lives and how to read it.

    On Dataproc these paths should be ``gs://`` URIs; locally they can be
    plain file paths. Parquet is strongly preferred over CSV for large
    telemetry because it is columnar, compressed and carries a schema, which
    dramatically cuts the I/O and memory pressure described in CLAUDE.md.
    """

    # Input location for the raw air-quality / atmospheric telemetry.
    input_path: str = field(default_factory=lambda: _env(
        "MDP_INPUT_PATH", "gs://mdp-air-pollution/raw/telemetry/"))

    # Input format: "parquet" (preferred) or "csv".
    input_format: str = field(default_factory=lambda: _env(
        "MDP_INPUT_FORMAT", "parquet"))

    # For CSV ingestion only: does the file carry a header row?
    csv_header: bool = field(default_factory=lambda: _env(
        "MDP_CSV_HEADER", "true").lower() == "true")

    # Columns that identify an observation (timestamp, station id, lat/lon,
    # etc.). These are carried through but are NOT treated as chemical
    # species features during clustering.
    id_columns: List[str] = field(default_factory=lambda: [
        c for c in _env("MDP_ID_COLUMNS", "timestamp,station_id").split(",")
        if c
    ])

    # Explicit list of chemical-species columns to cluster. If left empty the
    # pipeline infers the species columns as "all numeric columns that are not
    # id_columns". Being explicit is safer in production.
    species_columns: List[str] = field(default_factory=lambda: [
        c for c in _env("MDP_SPECIES_COLUMNS", "").split(",") if c
    ])


@dataclass(frozen=True)
class ClusteringConfig:
    """K-means settings for Phase 1 (grouping chemical species)."""

    # Candidate values of k to evaluate. The best k is chosen by silhouette
    # score unless ``fixed_k`` is set.
    k_candidates: List[int] = field(default_factory=lambda: [
        int(x) for x in _env("MDP_K_CANDIDATES", "2,3,4,5,6,7,8").split(",")
    ])

    # If set (> 0), skip the silhouette search and use exactly this k.
    fixed_k: int = field(default_factory=lambda: int(_env("MDP_FIXED_K", "0")))

    # K-means hyper-parameters.
    max_iter: int = field(default_factory=lambda: int(_env("MDP_KMEANS_MAX_ITER", "50")))
    seed: int = field(default_factory=lambda: int(_env("MDP_SEED", "42")))

    # Minimum fraction of non-null readings a species must have to be included
    # in clustering. Species sparser than this are dropped and reported.
    min_valid_fraction: float = field(default_factory=lambda: float(
        _env("MDP_MIN_VALID_FRACTION", "0.5")))

    # Correlation method used to build the species feature vectors.
    # "pearson" (linear) or "spearman" (rank / monotonic).
    correlation_method: str = field(default_factory=lambda: _env(
        "MDP_CORR_METHOD", "pearson"))


@dataclass(frozen=True)
class PredictiveConfig:
    """Phase 2 - distributed XGBoost predictive-baseline settings.

    The baseline predicts a secondary pollutant (e.g. Ozone) from the other
    measured species. It establishes how much of the target is explainable by
    straightforward supervised learning before we attempt causal discovery.
    """

    # Secondary pollutant to predict (the regression target).
    target_column: str = field(default_factory=lambda: _env(
        "MDP_TARGET_COLUMN", "ozone"))

    # Explicit predictor columns. Empty -> infer "all numeric columns that are
    # neither id columns nor the target".
    feature_columns: List[str] = field(default_factory=lambda: [
        c for c in _env("MDP_FEATURE_COLUMNS", "").split(",") if c
    ])

    # Number of Spark workers XGBoost trains across. 0 -> auto-detect from the
    # live cluster (defaultParallelism) so one JVM task maps to one XGBoost
    # worker, which is how xgboost.spark wants to be laid out.
    num_workers: int = field(default_factory=lambda: int(
        _env("MDP_XGB_NUM_WORKERS", "0")))

    # Core XGBoost hyper-parameters (kept modest; tune in Phase 3).
    n_estimators: int = field(default_factory=lambda: int(_env("MDP_XGB_N_ESTIMATORS", "300")))
    max_depth: int = field(default_factory=lambda: int(_env("MDP_XGB_MAX_DEPTH", "6")))
    learning_rate: float = field(default_factory=lambda: float(_env("MDP_XGB_ETA", "0.05")))
    subsample: float = field(default_factory=lambda: float(_env("MDP_XGB_SUBSAMPLE", "0.8")))
    colsample_bytree: float = field(default_factory=lambda: float(
        _env("MDP_XGB_COLSAMPLE", "0.8")))

    # Fraction of rows used for training (the rest is held out for evaluation).
    train_fraction: float = field(default_factory=lambda: float(
        _env("MDP_TRAIN_FRACTION", "0.8")))
    seed: int = field(default_factory=lambda: int(_env("MDP_SEED", "42")))


@dataclass(frozen=True)
class CausalConfig:
    """Phase 2 - DirectLiNGAM causal-discovery settings.

    DirectLiNGAM recovers a causal DAG + linear structural-equation
    coefficients among the pollutants. It is a *single-node* algorithm
    (operates on an in-memory matrix), so Phase 2 uses Spark to clean and
    **bound-sample** the data before collecting only that bounded sample to the
    driver - the memory-bottleneck discipline from CLAUDE.md.
    """

    # Primary (directly emitted) pollutants - candidate causes.
    primary_pollutants: List[str] = field(default_factory=lambda: [
        c for c in _env("MDP_PRIMARY_POLLUTANTS", "no,no2,co,so2,voc").split(",")
        if c
    ])

    # Secondary (chemically formed) pollutants - candidate effects.
    secondary_pollutants: List[str] = field(default_factory=lambda: [
        c for c in _env("MDP_SECONDARY_POLLUTANTS", "ozone,pm25").split(",")
        if c
    ])

    # Hard cap on rows pulled to the driver for LiNGAM. Protects driver memory:
    # if the (cleaned) data is larger we take a reproducible random sample.
    max_sample_rows: int = field(default_factory=lambda: int(
        _env("MDP_LINGAM_MAX_ROWS", "50000")))

    # Enforce the physical/temporal constraint that secondary pollutants cannot
    # cause primary emissions (used as DirectLiNGAM prior knowledge).
    use_prior_knowledge: bool = field(default_factory=lambda: _env(
        "MDP_LINGAM_PRIOR", "true").lower() == "true")

    # Edges with |coefficient| below this are pruned from the reported DAG.
    edge_threshold: float = field(default_factory=lambda: float(
        _env("MDP_LINGAM_EDGE_THRESHOLD", "0.05")))

    seed: int = field(default_factory=lambda: int(_env("MDP_SEED", "42")))


@dataclass(frozen=True)
class OptimizationConfig:
    """Phase 3 - multi-objective policy optimization with Optuna NSGA-II.

    We search over emission-reduction *interventions* on the primary pollutants
    and evaluate each candidate by propagating it through the Phase 2b causal
    SEM, reading off the resulting Ozone and PM2.5. NSGA-II returns the Pareto
    front of interventions that trade the two pollutants off against each other
    (the VOC-/NOx-limited ozone regimes make this a genuine trade-off, not a
    trivial "reduce everything").
    """

    # Relational storage backend. A shared RDBMS lets every Spark worker fetch
    # parameters and report trial results into ONE study, so trials run in
    # parallel across the cluster. SQLite (per CLAUDE.md) works when the file is
    # on a path all workers can reach; for heavy parallelism point this at Cloud
    # SQL (e.g. "mysql+pymysql://user:pw@host/db") via the env var.
    storage_url: str = field(default_factory=lambda: _env(
        "MDP_OPTUNA_STORAGE", "sqlite:///db.sqlite3"))

    study_name: str = field(default_factory=lambda: _env(
        "MDP_OPTUNA_STUDY", "mdp_pollution_pareto"))

    # Total trials across the whole cluster, and how many Spark partitions
    # (workers) share the work. trials_per_worker = ceil(n_trials/n_workers).
    n_trials: int = field(default_factory=lambda: int(_env("MDP_OPTUNA_TRIALS", "512")))
    n_parallel_workers: int = field(default_factory=lambda: int(
        _env("MDP_OPTUNA_WORKERS", "0")))  # 0 -> auto from cluster parallelism

    # The two objectives to minimise (must be secondary-pollutant columns).
    objectives: List[str] = field(default_factory=lambda: [
        c for c in _env("MDP_OPTUNA_OBJECTIVES", "ozone,pm25").split(",") if c
    ])

    # Intervention search bounds, in standardised units (the SEM is fitted on
    # standardised data). Policy can only *reduce* or hold emissions, hence the
    # default upper bound of 0.0 (the historical mean) down to 2 sd below it.
    intervention_low: float = field(default_factory=lambda: float(
        _env("MDP_INTERVENTION_LOW", "-2.0")))
    intervention_high: float = field(default_factory=lambda: float(
        _env("MDP_INTERVENTION_HIGH", "0.0")))

    seed: int = field(default_factory=lambda: int(_env("MDP_SEED", "42")))


@dataclass(frozen=True)
class XaiConfig:
    """Phase 3 - SHAP explainability of the Phase 2a XGBoost baseline."""

    # Bounded sample of rows explained (SHAP is single-node; cap the driver
    # footprint exactly as Phase 2b does for LiNGAM).
    max_sample_rows: int = field(default_factory=lambda: int(
        _env("MDP_SHAP_MAX_ROWS", "5000")))

    # Max features shown on the summary plot.
    max_display: int = field(default_factory=lambda: int(_env("MDP_SHAP_MAX_DISPLAY", "20")))

    # Local driver path for the rendered summary plot (copy to GCS afterwards on
    # Dataproc, or set to a mounted path).
    summary_plot_path: str = field(default_factory=lambda: _env(
        "MDP_SHAP_PLOT_PATH", "shap_summary.png"))

    seed: int = field(default_factory=lambda: int(_env("MDP_SEED", "42")))


@dataclass(frozen=True)
class OutputConfig:
    """Where the phases write their artefacts."""

    # Root output location. On Dataproc a ``gs://`` bucket.
    output_path: str = field(default_factory=lambda: _env(
        "MDP_OUTPUT_PATH", "gs://mdp-air-pollution/processed/"))

    # Phase 1 sub-paths.
    cluster_assignments_subpath: str = "phase1/species_clusters"
    correlation_subpath: str = "phase1/species_correlation"
    metrics_subpath: str = "phase1/clustering_metrics"

    # Phase 2 sub-paths.
    xgb_model_subpath: str = "phase2/xgb_baseline_model"
    xgb_metrics_subpath: str = "phase2/xgb_baseline_metrics"
    causal_dag_subpath: str = "phase2/causal_dag"
    causal_sem_subpath: str = "phase2/causal_sem"

    # Phase 3 sub-paths.
    pareto_front_subpath: str = "phase3/pareto_front"
    shap_importance_subpath: str = "phase3/shap_importance"


@dataclass(frozen=True)
class SparkConfig:
    """Spark/Dataproc runtime tuning, centred on the memory bottlenecks that
    large telemetry datasets create (CLAUDE.md core rule)."""

    app_name: str = "MDP-Phase1-SpeciesClustering"

    # Spark conf key/value pairs applied to every session. These defaults are
    # deliberately conservative and safe for large data; on Dataproc the
    # cluster-level defaults will usually also apply.
    conf: dict = field(default_factory=lambda: {
        # Kryo serialisation is far more memory/CPU efficient than Java
        # serialisation for the dense vectors K-means shuffles around.
        "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
        # Adaptive Query Execution lets Spark coalesce shuffle partitions at
        # runtime, avoiding tiny-file / oversized-partition memory blow-ups.
        "spark.sql.adaptive.enabled": "true",
        "spark.sql.adaptive.coalescePartitions.enabled": "true",
        # Arrow speeds up the rare, bounded driver-side pandas conversions we
        # allow (e.g. a small species x species matrix), without pulling big
        # data to the driver.
        "spark.sql.execution.arrow.pyspark.enabled": "true",
        # Push more work into scan time: skip row groups via stats.
        "spark.sql.parquet.filterPushdown": "true",
        # Telemetry from different stations reports different pollutant sets, so
        # the per-station Parquet files have differing columns. Merge their
        # schemas on read to take the UNION of columns (missing ones become
        # null) instead of silently using just one file's schema.
        "spark.sql.parquet.mergeSchema": "true",
    })


@dataclass(frozen=True)
class PipelineConfig:
    """Top-level config aggregating the sections above."""

    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    predictive: PredictiveConfig = field(default_factory=PredictiveConfig)
    causal: CausalConfig = field(default_factory=CausalConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    xai: XaiConfig = field(default_factory=XaiConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    spark: SparkConfig = field(default_factory=SparkConfig)


def load_config() -> PipelineConfig:
    """Build a :class:`PipelineConfig` from the current environment."""
    return PipelineConfig()
