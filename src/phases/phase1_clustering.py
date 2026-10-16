"""
Phase 1 - Data Ingestion & K-means Clustering of Chemical Species.

Goal (per CLAUDE.md):
    Objectively group the chemical species measured in the air-pollution
    telemetry into clusters, using PySpark so the work scales across the
    Dataproc cluster.

Why cluster the *species* rather than the *observations*?
    The downstream causal-discovery phase needs a principled, data-driven
    grouping of species (e.g. "oxidised nitrogen family", "secondary
    aerosol precursors") instead of relying on textbook chemistry alone.
    Grouping species objectively means describing each species by *how it
    co-varies with every other species across the whole dataset*, then
    clustering those co-variation fingerprints.

Scalable strategy (avoids single-node pandas on the big data):
    1. Read the (potentially enormous) telemetry with Spark.
    2. Compute the full inter-species correlation matrix with Spark MLlib.
       This is the only step that touches every row, and Spark distributes
       it across the cluster. The *result* is only ``n_species x n_species``
       - tiny - so it is safe to bring to the driver.
    3. Treat each species' row of that correlation matrix as its feature
       vector and run K-means on the (tiny) species-level table.

The heavy, data-parallel work therefore stays in Spark; only a kilobyte-scale
matrix is ever materialised on the driver. That is the memory-bottleneck
discipline CLAUDE.md asks for.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from config.pipeline_config import (
    ClusteringConfig,
    IngestionConfig,
    OutputConfig,
    PipelineConfig,
    load_config,
)
from src.spark_utils import build_spark_session

logger = logging.getLogger("mdp.phase1")


# --------------------------------------------------------------------------- #
# Step 1: Ingestion
# --------------------------------------------------------------------------- #
def ingest_telemetry(spark, cfg: IngestionConfig):
    """Read the raw telemetry into a Spark DataFrame.

    Returns the DataFrame. No ``.collect()`` / ``.toPandas()`` is performed -
    the data stays distributed. Parquet is read with schema inference built
    in; CSV is read with schema inference enabled and the configured header
    handling.
    """
    reader = spark.read
    if cfg.input_format == "parquet":
        df = reader.parquet(cfg.input_path)
    elif cfg.input_format == "csv":
        df = (
            reader.option("header", cfg.csv_header)
            # inferSchema makes a second pass over the data but spares us a
            # brittle hand-maintained schema; acceptable for ingestion.
            .option("inferSchema", "true")
            .csv(cfg.input_path)
        )
    else:
        raise ValueError(f"Unsupported input_format: {cfg.input_format!r}")

    logger.info("Ingested telemetry with %d columns", len(df.columns))
    return df


def resolve_species_columns(df, cfg: IngestionConfig) -> List[str]:
    """Decide which columns are chemical-species features.

    If the config lists species explicitly we honour it; otherwise we infer
    "all numeric columns that are not id columns". This keeps the pipeline
    usable on a new dataset without reconfiguration while allowing a locked-
    down explicit list in production.
    """
    from pyspark.sql.types import NumericType

    if cfg.species_columns:
        missing = [c for c in cfg.species_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Configured species columns absent from data: {missing}")
        return list(cfg.species_columns)

    id_set = set(cfg.id_columns)
    inferred = [
        field.name
        for field in df.schema.fields
        if field.name not in id_set and isinstance(field.dataType, NumericType)
    ]
    if not inferred:
        raise ValueError("Could not infer any numeric species columns.")
    logger.info("Inferred %d species columns: %s", len(inferred), inferred)
    return inferred


# --------------------------------------------------------------------------- #
# Step 2: Cleaning / quality filtering (distributed)
# --------------------------------------------------------------------------- #
def filter_sparse_species(
    df, species: List[str], min_valid_fraction: float
) -> Tuple[List[str], Dict[str, float]]:
    """Drop species whose non-null coverage is below ``min_valid_fraction``.

    The valid-fraction per column is computed with a single distributed
    aggregation (one pass, no data pulled to the driver beyond a one-row
    summary). Sensors frequently drop out, so clustering on a species that is
    99% null would be meaningless and would also poison the correlation step.
    """
    from pyspark.sql import functions as F

    total = df.count()  # single distributed action, returns a scalar
    if total == 0:
        raise ValueError("Telemetry is empty - nothing to cluster.")

    # Count non-null, non-NaN readings per species in ONE aggregation pass.
    agg_exprs = [
        F.count(F.when(F.col(c).isNotNull() & ~F.isnan(F.col(c)), c)).alias(c)
        for c in species
    ]
    counts_row = df.agg(*agg_exprs).first().asDict()

    fractions = {c: counts_row[c] / total for c in species}
    kept = [c for c in species if fractions[c] >= min_valid_fraction]
    dropped = {c: fractions[c] for c in species if c not in kept}
    if dropped:
        logger.warning(
            "Dropping %d sparse species (below %.0f%% coverage): %s",
            len(dropped), min_valid_fraction * 100, dropped,
        )
    if len(kept) < 2:
        raise ValueError(
            "Fewer than 2 species survived the coverage filter; cannot cluster."
        )
    return kept, fractions


# --------------------------------------------------------------------------- #
# Step 3: Species feature vectors via the distributed correlation matrix
# --------------------------------------------------------------------------- #
def build_species_feature_vectors(df, species: List[str], cfg: ClusteringConfig):
    """Compute the inter-species correlation matrix and turn each species'
    row of it into that species' feature vector.

    Returns ``(spark_feature_df, correlation_rows)`` where:
      * ``spark_feature_df`` has columns ``species`` (str) and ``features``
        (an ML dense vector) - exactly ``len(species)`` rows.
      * ``correlation_rows`` is the correlation matrix as a list of
        ``{"species": name, "<other species>": value, ...}`` dicts, suitable
        for writing out as an auditable artefact.

    Memory note:
        Only the ``n x n`` matrix (n = number of species, typically tens)
        crosses back to the driver. The per-row correlation itself is computed
        by Spark MLlib across the cluster.
    """
    from pyspark.ml.feature import Imputer, VectorAssembler
    from pyspark.ml.linalg import Vectors
    from pyspark.ml.stat import Correlation

    # Correlation requires fully-populated vectors. Impute remaining nulls with
    # the per-species mean - a distributed operation handled by MLlib. We keep
    # only the species columns to minimise the data scanned/shuffled.
    imputed_cols = [f"{c}__imp" for c in species]
    imputer = Imputer(
        inputCols=species, outputCols=imputed_cols, strategy="mean"
    )
    # Select only what we need so Spark can prune columns at the scan.
    narrow = df.select(*species)
    imputed = imputer.fit(narrow).transform(narrow).select(*imputed_cols)

    # Assemble one feature vector per row, then let MLlib compute correlations.
    assembler = VectorAssembler(inputCols=imputed_cols, outputCol="__vec")
    vectorised = assembler.transform(imputed).select("__vec")

    # This is the heavy, cluster-distributed computation.
    corr_row = Correlation.corr(vectorised, "__vec", method=cfg.correlation_method)
    corr_matrix = corr_row.head()[0]  # DenseMatrix - small (n x n)
    n = len(species)
    # DenseMatrix stores column-major; .toArray() gives a numpy array but is
    # only n x n, so this tiny driver-side materialisation is safe.
    matrix = corr_matrix.toArray()

    # Build the auditable correlation artefact as plain Python dicts.
    correlation_rows = []
    for i, name in enumerate(species):
        row = {"species": name}
        row.update({species[j]: float(matrix[i][j]) for j in range(n)})
        correlation_rows.append(row)

    # Each species' feature vector = its row of correlations. Parallelise the
    # tiny list back into a Spark DataFrame so K-means stays a Spark job.
    spark = df.sparkSession
    feature_data = [
        (species[i], Vectors.dense([float(matrix[i][j]) for j in range(n)]))
        for i in range(n)
    ]
    feature_df = spark.createDataFrame(feature_data, ["species", "features"])
    return feature_df, correlation_rows


# --------------------------------------------------------------------------- #
# Step 4: K-means with silhouette-based model selection
# --------------------------------------------------------------------------- #
def select_and_fit_kmeans(feature_df, cfg: ClusteringConfig):
    """Standardise the species feature vectors and fit K-means.

    When ``fixed_k`` is unset we sweep ``k_candidates`` and pick the k with
    the best silhouette score. The feature table has one row per species, so
    this sweep is cheap even though each fit is a full MLlib K-means run.

    Returns ``(fitted_pipeline_model, assignments_df, metrics)``.
    """
    from pyspark.ml import Pipeline
    from pyspark.ml.clustering import KMeans
    from pyspark.ml.evaluation import ClusteringEvaluator
    from pyspark.ml.feature import StandardScaler

    n_species = feature_df.count()

    # Standardise so every species-correlation dimension contributes equally.
    scaler = StandardScaler(
        inputCol="features", outputCol="scaled_features",
        withMean=True, withStd=True,
    )
    evaluator = ClusteringEvaluator(
        featuresCol="scaled_features", predictionCol="cluster",
        metricName="silhouette",
    )

    # Candidate k cannot meet or exceed the number of species.
    if cfg.fixed_k and cfg.fixed_k > 0:
        candidates = [cfg.fixed_k]
    else:
        candidates = [k for k in cfg.k_candidates if 2 <= k < n_species]
    if not candidates:
        raise ValueError(
            f"No valid k candidates for {n_species} species "
            f"(need 2 <= k < {n_species})."
        )

    best = None  # (silhouette, k, pipeline_model, assignments_df)
    per_k_scores: Dict[int, float] = {}

    for k in candidates:
        kmeans = KMeans(
            featuresCol="scaled_features", predictionCol="cluster",
            k=k, maxIter=cfg.max_iter, seed=cfg.seed,
        )
        model = Pipeline(stages=[scaler, kmeans]).fit(feature_df)
        assignments = model.transform(feature_df)
        silhouette = evaluator.evaluate(assignments)
        per_k_scores[k] = silhouette
        logger.info("k=%d -> silhouette=%.4f", k, silhouette)
        if best is None or silhouette > best[0]:
            best = (silhouette, k, model, assignments)

    best_silhouette, best_k, best_model, best_assignments = best
    logger.info("Selected k=%d (silhouette=%.4f)", best_k, best_silhouette)

    metrics = {
        "selected_k": best_k,
        "selected_silhouette": best_silhouette,
        "silhouette_by_k": per_k_scores,
        "correlation_method": cfg.correlation_method,
        "n_species_clustered": n_species,
    }
    return best_model, best_assignments, metrics


# --------------------------------------------------------------------------- #
# Step 5: Persist artefacts
# --------------------------------------------------------------------------- #
def write_outputs(spark, assignments, correlation_rows, fractions, metrics,
                  out: OutputConfig) -> None:
    """Write the three Phase-1 artefacts back to the output store (GCS on
    Dataproc): the species->cluster assignments, the correlation matrix, and
    the clustering metrics.

    The assignments and correlation tables are small, so we ``coalesce(1)`` to
    avoid a scatter of tiny part-files - a deliberate, size-aware choice (we do
    NOT coalesce big data elsewhere, which would create memory hot-spots).
    """
    import json

    from pyspark.sql import functions as F

    base = out.output_path.rstrip("/")

    # 1) species -> cluster assignments. Drop the vector columns before writing.
    assignments_out = (
        assignments.select("species", "cluster")
        .withColumn("cluster", F.col("cluster").cast("int"))
        .orderBy("cluster", "species")
    )
    assignments_out.coalesce(1).write.mode("overwrite").parquet(
        f"{base}/{out.cluster_assignments_subpath}"
    )

    # 2) correlation matrix as an auditable table.
    corr_df = spark.createDataFrame(correlation_rows)
    corr_df.coalesce(1).write.mode("overwrite").parquet(
        f"{base}/{out.correlation_subpath}"
    )

    # 3) metrics as a single JSON document (coverage fractions included).
    metrics_doc = dict(metrics)
    metrics_doc["species_valid_fraction"] = fractions
    metrics_json = json.dumps(metrics_doc, indent=2, sort_keys=True)
    # Write via Spark so the path can be GCS. One tiny row -> one file.
    spark.createDataFrame([(metrics_json,)], ["metrics_json"]) \
        .coalesce(1).write.mode("overwrite").text(
            f"{base}/{out.metrics_subpath}"
        )
    logger.info("Phase 1 artefacts written under %s", base)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run_phase1(config: Optional[PipelineConfig] = None) -> Dict:
    """Run the full Phase-1 pipeline and return the metrics dict.

    This is the function a Dataproc submit (or an orchestrator) calls.
    """
    cfg = config or load_config()
    spark = build_spark_session(cfg.spark)

    try:
        df = ingest_telemetry(spark, cfg.ingestion)
        species = resolve_species_columns(df, cfg.ingestion)

        # Cache: the raw frame is scanned by both the coverage aggregation and
        # the correlation computation. Caching avoids re-reading the (large)
        # source twice. MEMORY_AND_DISK spills to disk instead of OOM-ing when
        # the data does not fit in RAM - the key large-telemetry safeguard.
        from pyspark import StorageLevel
        df = df.persist(StorageLevel.MEMORY_AND_DISK)

        kept_species, fractions = filter_sparse_species(
            df, species, cfg.clustering.min_valid_fraction
        )
        feature_df, correlation_rows = build_species_feature_vectors(
            df, kept_species, cfg.clustering
        )

        # The big frame is no longer needed once feature vectors exist; release
        # its cached blocks promptly to free executor memory for K-means.
        df.unpersist()

        _model, assignments, metrics = select_and_fit_kmeans(
            feature_df, cfg.clustering
        )
        write_outputs(
            spark, assignments, correlation_rows, fractions, metrics, cfg.output
        )
        return metrics
    finally:
        spark.stop()


if __name__ == "__main__":
    # Entry point for `spark-submit src/phases/phase1_clustering.py` on Dataproc.
    result = run_phase1()
    logger.info("Phase 1 complete: %s", result)
