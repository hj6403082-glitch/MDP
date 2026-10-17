# ============================================================================
# Custom runtime image for the MDP pipeline on Dataproc Serverless.
#
# Dataproc Serverless provides Spark itself; this image layers in our Python
# dependencies (xgboost, lingam, optuna, shap, ...) so the driver and executors
# can import them. It follows Google's custom-container requirements:
#   * Debian base, with `procps`, `tini` and `libjemalloc2` installed.
#   * A `spark` user with UID/GID 1099 (Dataproc runs the workload as this user).
#
# Python is pinned to 3.12 to match the Dataproc Serverless 2.2 runtime
# (Spark 3.5.x), which is the version `submit.sh` requests and which matches the
# pinned pyspark==3.5.3 in requirements.txt. If you target a different runtime
# version, align both the Python version here and RUNTIME_VERSION in submit.sh.
#
# Build + push (see submit.sh for the automated path):
#   gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/mdp/mdp-runtime:latest .
# ============================================================================
FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive

# (Required) Spark helper utilities + native libs our wheels need:
#   procps/tini/libjemalloc2 -> Dataproc requirement
#   libgomp1                 -> OpenMP runtime for XGBoost
#   ca-certificates/curl/bzip2 -> fetch & install Miniforge
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      procps tini libjemalloc2 libgomp1 ca-certificates curl bzip2 \
 && rm -rf /var/lib/apt/lists/*

# (Optional) jemalloc reduces Spark/driver memory fragmentation.
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

# --- Python via Miniforge (conda-forge), pinned to match the 2.2 runtime -----
ENV CONDA_HOME=/opt/miniforge3
ENV PATH=${CONDA_HOME}/bin:${PATH}
# Dataproc uses PYSPARK_PYTHON for the driver/executor interpreter.
ENV PYSPARK_PYTHON=${CONDA_HOME}/bin/python

ARG MINIFORGE=Miniforge3-Linux-x86_64.sh
RUN curl -fsSLO "https://github.com/conda-forge/miniforge/releases/latest/download/${MINIFORGE}" \
 && bash "${MINIFORGE}" -b -p "${CONDA_HOME}" \
 && rm -f "${MINIFORGE}" \
 && conda config --system --set always_yes True \
 && conda config --system --set auto_update_conda False \
 && conda install -n base python=3.12 \
 && conda clean -afy

# --- Project Python dependencies ---------------------------------------------
# Copy only requirements first so Docker caches this layer across code changes.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# (Required) Create and switch to the 'spark' user with the mandated UID/GID.
RUN groupadd -g 1099 spark \
 && useradd -u 1099 -g 1099 -d /home/spark -m spark
USER spark
