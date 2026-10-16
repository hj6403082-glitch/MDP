"""
MDP - Causal AI for Air Pollution: end-to-end pipeline driver.

Chains all three phases in one Spark application so the whole pipeline runs
with a single ``spark-submit``:

    Phase 1  Data ingestion + K-means clustering of chemical species
    Phase 2  (a) Distributed XGBoost predictive baseline
             (b) DirectLiNGAM causal discovery (DAG + SEMs)
    Phase 3  (a) Optuna NSGA-II multi-objective policy optimization
             (b) SHAP explainability of the Phase 2a baseline

Design notes:
    * ONE SparkSession is built here and shared across every phase (each phase
      accepts an injected ``spark`` and does not stop it). This avoids tearing
      down and re-initialising the Spark context mid-application, which is both
      wasteful and fragile on Dataproc.
    * Phases run in dependency order: Phase 3 reads Phase 2's persisted model
      and causal DAG, so the sequence below must not be reordered.
    * Each phase is wrapped so a failure is reported with its phase name; pass
      ``--continue-on-error`` to attempt remaining phases anyway (useful when
      re-running only to refresh a later artefact).

Usage (Dataproc):
    spark-submit --py-files config.zip,src.zip main.py
    # or, if the repo root is on PYTHONPATH:
    spark-submit main.py --phases all

See README.md for packaging and configuration details.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import Callable, Dict, List

from config.pipeline_config import PipelineConfig, load_config
from src.spark_utils import build_spark_session

# Import the phase entry points. These imports are light (PySpark/XGBoost/etc.
# are imported lazily inside each phase), so importing main.py is cheap.
from src.phases.phase1_clustering import run_phase1
from src.phases.phase2_predictive import run_predictive_baseline
from src.phases.phase2_causal import run_causal_discovery
from src.phases.phase3_optimization import run_optimization
from src.phases.phase3_xai import run_xai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mdp.main")


# Ordered registry of (key, human label, runner). The key is what the user
# selects with --phases; order here is the execution (dependency) order.
PHASES: List = [
    ("phase1", "Phase 1 - ingestion & species clustering", run_phase1),
    ("phase2a", "Phase 2a - XGBoost predictive baseline", run_predictive_baseline),
    ("phase2b", "Phase 2b - DirectLiNGAM causal discovery", run_causal_discovery),
    ("phase3a", "Phase 3a - Optuna NSGA-II optimization", run_optimization),
    ("phase3b", "Phase 3b - SHAP explainability", run_xai),
]
PHASE_KEYS = [key for key, _, _ in PHASES]


def _select_phases(selected: List[str]) -> List:
    """Resolve the --phases selection into an ordered list of phase tuples."""
    if not selected or selected == ["all"]:
        return PHASES
    unknown = [s for s in selected if s not in PHASE_KEYS]
    if unknown:
        raise SystemExit(
            f"Unknown phase(s): {unknown}. Choose from {PHASE_KEYS} or 'all'."
        )
    # Keep canonical execution order regardless of how the user ordered them.
    return [p for p in PHASES if p[0] in set(selected)]


def _run_one(label: str, runner: Callable, cfg: PipelineConfig, spark) -> Dict:
    """Run a single phase with timing and a concise summary log."""
    logger.info("=" * 72)
    logger.info("STARTING %s", label)
    logger.info("=" * 72)
    start = time.time()
    result = runner(config=cfg, spark=spark)
    elapsed = time.time() - start
    logger.info("FINISHED %s in %.1fs", label, elapsed)
    return {"elapsed_seconds": round(elapsed, 1), "result": result}


def run_pipeline(selected_phases: List[str], continue_on_error: bool) -> Dict:
    """Build one SparkSession, run the selected phases in order, return a report."""
    cfg = load_config()
    spark = build_spark_session(cfg.spark)
    logger.info("Pipeline starting (Spark %s). Output root: %s",
                spark.version, cfg.output.output_path)

    report: Dict[str, Dict] = {}
    failed: List[str] = []
    try:
        for key, label, runner in _select_phases(selected_phases):
            try:
                report[key] = _run_one(label, runner, cfg, spark)
                report[key]["status"] = "ok"
            except Exception as exc:  # noqa: BLE001 - we want the phase name attached
                logger.exception("%s FAILED: %s", label, exc)
                report[key] = {"status": "failed", "error": str(exc)}
                failed.append(key)
                if not continue_on_error:
                    raise
    finally:
        # The driver owns the single shared session, so it alone stops it.
        spark.stop()
        logger.info("Spark session stopped.")

    report["_summary"] = {
        "phases_run": [k for k in report if not k.startswith("_")],
        "failed": failed,
        "all_ok": not failed,
    }
    return report


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MDP Causal-AI-for-Air-Pollution pipeline.")
    parser.add_argument(
        "--phases", nargs="+", default=["all"], metavar="PHASE",
        help=(f"Phases to run, in any order (canonical order is enforced). "
              f"Choices: {PHASE_KEYS} or 'all' (default)."))
    parser.add_argument(
        "--continue-on-error", action="store_true",
        help="Attempt remaining phases even if one fails.")
    # Spark/Dataproc may append extra args; ignore unknown ones gracefully.
    args, _unknown = parser.parse_known_args(argv)
    return args


def main(argv: List[str]) -> int:
    args = _parse_args(argv)
    report = run_pipeline(args.phases, args.continue_on_error)
    # Emit a machine-readable summary on stdout for CI / orchestration capture.
    print(json.dumps(report.get("_summary", {}), indent=2))
    return 0 if report["_summary"]["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
