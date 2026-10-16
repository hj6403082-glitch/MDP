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
class OutputConfig:
    """Where Phase 1 writes its artefacts."""

    # Root output location. On Dataproc a ``gs://`` bucket.
    output_path: str = field(default_factory=lambda: _env(
        "MDP_OUTPUT_PATH", "gs://mdp-air-pollution/processed/"))

    # Sub-paths for the individual artefacts.
    cluster_assignments_subpath: str = "phase1/species_clusters"
    correlation_subpath: str = "phase1/species_correlation"
    metrics_subpath: str = "phase1/clustering_metrics"


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
    })


@dataclass(frozen=True)
class PipelineConfig:
    """Top-level config aggregating the sections above."""

    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    spark: SparkConfig = field(default_factory=SparkConfig)


def load_config() -> PipelineConfig:
    """Build a :class:`PipelineConfig` from the current environment."""
    return PipelineConfig()
