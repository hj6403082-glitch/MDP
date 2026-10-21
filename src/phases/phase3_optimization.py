"""
Phase 3a - Multi-Objective Policy Optimization with Optuna (NSGA-II).

Goal (per CLAUDE.md):
    Minimise **both** PM2.5 and Ozone simultaneously by searching over emission-
    reduction interventions on the primary pollutants. Optuna's
    ``NSGAIISampler`` returns the Pareto front of interventions - the policies
    where you cannot reduce one pollutant further without worsening the other.

How a candidate policy is scored:
    Each trial proposes an intervention level (in standardised units) for every
    primary pollutant. We apply it as a causal *do*-operation on the Phase 2b
    SEM - fix the primaries, sever their incoming edges, and propagate through
    the recovered causal order - then read off the resulting Ozone and PM2.5.
    Because the SEM encodes the (sign-sensitive) ozone chemistry, reducing NOx
    can *raise* ozone in some regimes, which is exactly what makes this a true
    multi-objective trade-off rather than "reduce everything to zero".

Distributed execution (the key CLAUDE.md requirement):
    The study lives in a **relational database** (``storage='sqlite:///...'``
    by default). Each Spark worker calls ``optuna.load_study(...)`` against that
    same storage and runs its share of trials; the RDBMS is the coordination
    point, so workers fetch parameters and push results **in parallel across the
    cluster**. The per-trial evaluation is pure NumPy over a tiny broadcast
    matrix, so no big data is shuffled and the driver never accumulates trial
    data - it only reads the final Pareto front back from storage.

    NOTE on SQLite: it coordinates fine when the ``.sqlite3`` file sits on a
    path every worker can reach (e.g. a mounted bucket). For very high
    parallelism prefer Cloud SQL (MySQL/Postgres) by setting MDP_OPTUNA_STORAGE
    - the code is storage-agnostic.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

from config.pipeline_config import (
    OptimizationConfig,
    OutputConfig,
    PipelineConfig,
    load_config,
)
from src.spark_utils import build_spark_session

logger = logging.getLogger("mdp.phase3.optimization")


# --------------------------------------------------------------------------- #
# Load the causal model (from Phase 2b artefacts) into a small, broadcastable
# structure. Only coefficients are moved around - never telemetry.
# --------------------------------------------------------------------------- #
class CausalPolicyModel:
    """A tiny, picklable wrapper around the SEM that evaluates interventions.

    Holds the standardised adjacency matrix, the column order and the causal
    (topological) order. Instances are broadcast to Spark workers; evaluating a
    policy is a handful of NumPy dot-products, so it is cheap to run thousands
    of times per worker.
    """

    def __init__(self, columns: List[str], adjacency, causal_order: List[int],
                 primary: List[str], objectives: List[str]):
        self.columns = columns
        self.index = {c: i for i, c in enumerate(columns)}
        self.adjacency = adjacency          # numpy array B, x = Bx + e
        self.causal_order = causal_order
        self.primary = primary
        self.objectives = objectives

    def evaluate(self, intervention: Dict[str, float]) -> Dict[str, float]:
        """Apply a *do*-intervention on the primaries and propagate.

        ``intervention`` maps each primary pollutant to its fixed standardised
        level. Returns the resulting standardised value of every objective.
        """
        import numpy as np

        # Reject any intervention on a variable absent from the fitted model
        # rather than silently ignoring it (guards against phantom variables
        # such as voc that are not part of the fitted graph).
        unknown = [p for p in intervention if p not in self.index]
        if unknown:
            raise ValueError(
                f"Intervention variables not in the fitted model: {unknown}. "
                f"Fitted variables are {self.columns}.")

        n = len(self.columns)
        x = np.zeros(n)
        primary_set = set(self.primary)
        # Fix intervened primaries; do-operator overrides their equation.
        for p, level in intervention.items():
            x[self.index[p]] = level
        # Propagate the remaining variables in causal order.
        for node in self.causal_order:
            if self.columns[node] in primary_set:
                continue  # value set by the intervention, parents severed
            x[node] = float(self.adjacency[node].dot(x))
        return {obj: float(x[self.index[obj]]) for obj in self.objectives}


def _topological_order(n: int, adjacency, threshold: float = 1e-12) -> List[int]:
    """Kahn topological sort of the DAG implied by the adjacency matrix.

    ``adjacency[i, j] != 0`` means edge ``j -> i``. DirectLiNGAM guarantees
    acyclicity, so a valid order always exists; we fall back to natural order
    for any numerically-isolated nodes.
    """
    import numpy as np

    adj = np.abs(np.asarray(adjacency)) > threshold
    indegree = adj.sum(axis=1)          # parents of each node
    order, queue = [], [i for i in range(n) if indegree[i] == 0]
    remaining = indegree.copy()
    while queue:
        node = queue.pop(0)
        order.append(node)
        # node is a parent (column) of children i where adj[i, node] is True.
        for i in range(n):
            if adj[i][node]:
                remaining[i] -= 1
                if remaining[i] == 0:
                    queue.append(i)
    if len(order) < n:  # cycle guard (shouldn't happen with a DAG)
        order += [i for i in range(n) if i not in order]
    return order


def supported_decision_variables(configured, graph_vars):
    """Split configured decision variables into those present in the fitted graph
    and those that are not.

    A variable absent from the fitted model (e.g. ``voc``, which is structurally
    missing from the data) can have no identifiable effect and MUST NOT be an
    optimization variable — optimizing over it silently produces meaningless
    ``policy_*`` columns. Returns ``(supported, rejected)`` preserving order.
    """
    gv = set(graph_vars)
    supported = [v for v in configured if v in gv]
    rejected = [v for v in configured if v not in gv]
    return supported, rejected


def load_causal_model(spark, cfg: PipelineConfig) -> CausalPolicyModel:
    """Reconstruct the SEM from the Phase 2b DAG parquet.

    The node set is taken from the **fitted graph** (the persisted edges), not
    from configuration, so variables that were never fitted (e.g. ``voc``) are
    excluded. Decision variables are the configured primaries intersected with
    the fitted nodes; any configured-but-unfitted variable is rejected with a
    warning rather than optimized over.
    """
    import numpy as np

    base = cfg.output.output_path.rstrip("/")
    edges_path = f"{base}/{cfg.output.causal_dag_subpath}"
    edges = spark.read.parquet(edges_path).collect()  # tiny edge list

    # Node set = variables that actually appear in the fitted graph.
    graph_vars = sorted({r["source"] for r in edges} | {r["target"] for r in edges})
    configured_secondary = [c for c in cfg.causal.secondary_pollutants if c in graph_vars]
    # Deterministic column order: fitted primaries first, then fitted secondaries.
    primary, rejected = supported_decision_variables(
        cfg.causal.primary_pollutants, graph_vars)
    if rejected:
        logger.warning("Rejecting configured decision variables absent from the "
                       "fitted graph (no identifiable effect): %s", rejected)
    columns = [c for c in graph_vars if c not in configured_secondary] + configured_secondary
    index = {c: i for i, c in enumerate(columns)}

    n = len(columns)
    B = np.zeros((n, n))
    for row in edges:
        s, t, coef = row["source"], row["target"], float(row["coefficient"])
        if s in index and t in index:
            B[index[t]][index[s]] = coef  # edge source -> target

    order = _topological_order(n, B)
    for obj in cfg.optimization.objectives:
        if obj not in index:
            raise ValueError(
                f"Objective {obj!r} is not among the configured pollutants "
                f"{columns}; cannot optimise it."
            )
    logger.info("Loaded causal policy model over %d nodes from %s", n, edges_path)
    return CausalPolicyModel(columns, B, order, primary, cfg.optimization.objectives)


# --------------------------------------------------------------------------- #
# Optuna objective + study management
# --------------------------------------------------------------------------- #
def make_objective(model: CausalPolicyModel, opt: OptimizationConfig):
    """Build the Optuna objective closure for a multi-objective study.

    Returns a function ``trial -> (obj1, obj2, ...)``. Each primary pollutant is
    a decision variable bounded by the configured intervention range.
    """
    def objective(trial) -> Tuple[float, ...]:
        intervention = {
            p: trial.suggest_float(p, opt.intervention_low, opt.intervention_high)
            for p in model.primary
        }
        scored = model.evaluate(intervention)
        return tuple(scored[obj] for obj in opt.objectives)

    return objective


def create_study(opt: OptimizationConfig):
    """Create (or load) the shared NSGA-II multi-objective study in the RDBMS.

    ``load_if_exists=True`` makes this safe to call from every worker: the first
    creates the study, the rest attach to it.
    """
    import optuna

    sampler = optuna.samplers.NSGAIISampler(seed=opt.seed)
    directions = ["minimize"] * len(opt.objectives)
    return optuna.create_study(
        study_name=opt.study_name,
        storage=opt.storage_url,
        sampler=sampler,
        directions=directions,
        load_if_exists=True,
    )


def run_optimization(config: Optional[PipelineConfig] = None, spark=None) -> Dict:
    """Run the distributed multi-objective optimization and persist the Pareto
    front.

    Pass an existing ``spark`` session to share one across phases; when omitted
    this function creates and stops its own.
    """
    cfg = config or load_config()
    owns_spark = spark is None
    if spark is None:
        spark = build_spark_session(cfg.spark)
    opt = cfg.optimization

    try:
        model = load_causal_model(spark, cfg)

        # Create the study once on the driver so the schema/record exists before
        # workers attach (avoids a creation race on the RDBMS).
        create_study(opt)

        n_workers = opt.n_parallel_workers or max(
            1, spark.sparkContext.defaultParallelism)
        trials_per_worker = max(1, math.ceil(opt.n_trials / n_workers))
        logger.info("Optimizing: %d trials over %d workers (%d each) -> %s",
                    opt.n_trials, n_workers, trials_per_worker, opt.storage_url)

        # Broadcast the tiny causal model so every worker shares one copy.
        bc_model = spark.sparkContext.broadcast(model)

        # Capture only plain, picklable values in the worker closure.
        storage_url = opt.storage_url
        study_name = opt.study_name
        objectives = list(opt.objectives)
        low, high, seed = opt.intervention_low, opt.intervention_high, opt.seed

        def worker(_partition_id):
            # Runs on an executor: attach to the SAME study in the RDBMS and run
            # this worker's share of trials. The DB coordinates concurrency, so
            # all workers optimise the one Pareto front in parallel.
            import optuna
            from config.pipeline_config import OptimizationConfig  # noqa: F401

            local_model = bc_model.value
            # The study's sampler is NOT persisted in storage; load_study without
            # an explicit sampler silently falls back to the default (TPE), NOT
            # the driver's NSGA-II. Re-supply the sampler on every worker so the
            # configured multi-objective optimizer is actually used.
            study = optuna.load_study(
                study_name=study_name, storage=storage_url,
                sampler=optuna.samplers.NSGAIISampler(seed=seed))

            def objective(trial):
                intervention = {
                    p: trial.suggest_float(p, low, high) for p in local_model.primary
                }
                scored = local_model.evaluate(intervention)
                return tuple(scored[o] for o in objectives)

            study.optimize(objective, n_trials=trials_per_worker)

        # One partition per worker; foreachPartition runs the share in parallel.
        spark.sparkContext.parallelize(range(n_workers), n_workers) \
            .foreach(worker)

        # Read the completed study back from storage and extract the Pareto front.
        import optuna
        study = optuna.load_study(study_name=study_name, storage=storage_url)
        pareto = study.best_trials  # the non-dominated set for a MO study

        front_rows = []
        for t in pareto:
            row = {"trial_number": t.number}
            row.update({f"policy_{k}": float(v) for k, v in t.params.items()})
            row.update({obj: float(val) for obj, val in zip(objectives, t.values)})
            front_rows.append(row)
        logger.info("Pareto front: %d non-dominated policies from %d trials",
                    len(front_rows), len(study.trials))

        base = cfg.output.output_path.rstrip("/")
        if front_rows:
            spark.createDataFrame(front_rows).coalesce(1).write.mode("overwrite") \
                .parquet(f"{base}/{cfg.output.pareto_front_subpath}")

        return {
            "n_trials_completed": len(study.trials),
            "pareto_front_size": len(front_rows),
            "objectives": objectives,
            "pareto_front": front_rows,
            "storage": storage_url,
        }
    finally:
        if owns_spark:
            spark.stop()


if __name__ == "__main__":
    result = run_optimization()
    logger.info("Phase 3a complete: %d Pareto-optimal policies",
                result["pareto_front_size"])
