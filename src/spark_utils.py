"""
Spark session management and small reusable helpers shared across phases.

Isolating session creation here keeps each phase focused on its analytics and
guarantees every phase uses the same memory-conscious configuration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config.pipeline_config import SparkConfig

if TYPE_CHECKING:  # Imported lazily at runtime; typed here for editors/linters.
    from pyspark.sql import SparkSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mdp.spark")


def build_spark_session(spark_conf: SparkConfig) -> "SparkSession":
    """Create (or fetch) the shared :class:`SparkSession`.

    On Dataproc the master/executor topology is supplied by the cluster, so we
    intentionally do NOT hard-code ``.master(...)``; we only layer our
    memory/perf tuning on top via ``spark.conf``. Locally, Spark falls back to
    ``local[*]`` automatically when no master is configured.
    """
    # Local import so that merely importing this module (e.g. for config in
    # unit tests) does not require PySpark to be installed.
    from pyspark.sql import SparkSession

    builder = SparkSession.builder.appName(spark_conf.app_name)
    for key, value in spark_conf.conf.items():
        builder = builder.config(key, value)

    spark = builder.getOrCreate()
    logger.info("Spark session ready (version=%s)", spark.version)
    return spark
