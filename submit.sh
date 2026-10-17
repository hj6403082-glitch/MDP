#!/usr/bin/env bash
#
# submit.sh - package the MDP pipeline and submit it to Dataproc Serverless.
#
# Run this LOCALLY from an authenticated gcloud session (`gcloud auth login`
# and `gcloud auth application-default login`). It packages src/ + config/ into
# mdp_modules.zip and submits main.py as a PySpark batch, passing all MDP_*
# configuration to the driver and executors.
#
# Usage:
#   ./submit.sh                 # runs all phases
#   ./submit.sh phase1 phase2a  # runs a subset (canonical order is enforced)

set -euo pipefail

# ############################################################################
# ## FILL THESE IN before running  ↓↓↓                                      ##
# ############################################################################
PROJECT_ID="YOUR_GCP_PROJECT_ID"       # e.g. my-air-quality-project
REGION="YOUR_REGION"                   # e.g. us-central1
STAGING_BUCKET="YOUR_STAGING_BUCKET"   # Dataproc deps/staging bucket, NAME only, no gs:// (e.g. my-mdp-staging)
DATA_BUCKET="YOUR_DATA_BUCKET"         # bucket holding input telemetry + outputs, NAME only, no gs:// (e.g. my-mdp-data)
# ############################################################################
# ## Optional settings — sensible defaults derived from the values above    ##
# ############################################################################
INPUT_PATH="gs://${DATA_BUCKET}/raw/telemetry/"   # where the raw telemetry lives
OUTPUT_PATH="gs://${DATA_BUCKET}/processed/"       # where artefacts are written
INPUT_FORMAT="parquet"                              # parquet | csv

# Optuna study backend. SQLite only coordinates trials when every worker shares
# the file — which Serverless workers do NOT. For real parallel optimization,
# point this at Cloud SQL, e.g.:
#   OPTUNA_STORAGE="mysql+pymysql://user:pass@/db?unix_socket=/cloudsql/CONNECTION_NAME"
OPTUNA_STORAGE="sqlite:///db.sqlite3"

RUNTIME_VERSION="2.2"                  # Dataproc Serverless runtime (2.2 = Spark 3.5 / Python 3.12)
AR_REPO="mdp"                          # Artifact Registry repo name for the image
IMAGE_TAG="latest"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/mdp-runtime:${IMAGE_TAG}"

# Set BUILD_IMAGE=1 to build + push the custom runtime image from Dockerfile
# before submitting (needed the first time and whenever requirements.txt changes).
BUILD_IMAGE="${BUILD_IMAGE:-0}"
# ############################################################################

# Phases to run come from the command line (default: all).
PHASES_ARG="${*:-all}"
# Collapse multiple args ("phase1 phase2a") into the comma-less form main.py
# expects via argparse nargs (it accepts space-separated after `--`).

cd "$(dirname "$0")"

# --- Guard: refuse to run with unedited placeholders ------------------------
for var in PROJECT_ID REGION STAGING_BUCKET DATA_BUCKET; do
  val="${!var}"
  if [[ "${val}" == YOUR_* ]]; then
    echo "ERROR: Please edit submit.sh and set ${var} (still '${val}')." >&2
    exit 1
  fi
done

# --- 1) Package the importable modules --------------------------------------
echo ">> Packaging modules -> mdp_modules.zip"
rm -f mdp_modules.zip
zip -r mdp_modules.zip src config -x '*__pycache__*' '*.pyc' >/dev/null
echo "   packaged $(unzip -l mdp_modules.zip | tail -1 | awk '{print $2}') files."

# --- 2) (Optional) Build + push the custom runtime image --------------------
if [[ "${BUILD_IMAGE}" == "1" ]]; then
  echo ">> Ensuring Artifact Registry repo '${AR_REPO}' exists"
  gcloud artifacts repositories describe "${AR_REPO}" \
      --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1 \
    || gcloud artifacts repositories create "${AR_REPO}" \
         --project="${PROJECT_ID}" --location="${REGION}" \
         --repository-format=docker
  echo ">> Building + pushing ${IMAGE_URI}"
  gcloud builds submit --project="${PROJECT_ID}" --region="${REGION}" \
    --tag "${IMAGE_URI}" .
else
  echo ">> Skipping image build (set BUILD_IMAGE=1 to build/push it first)."
fi

# --- 3) Assemble MDP_* config for BOTH driver and executors -----------------
declare -A ENVVARS=(
  [MDP_INPUT_PATH]="${INPUT_PATH}"
  [MDP_INPUT_FORMAT]="${INPUT_FORMAT}"
  [MDP_OUTPUT_PATH]="${OUTPUT_PATH}"
  [MDP_OPTUNA_STORAGE]="${OPTUNA_STORAGE}"
)
PROPS=""
for key in "${!ENVVARS[@]}"; do
  val="${ENVVARS[$key]}"
  PROPS+="spark.dataproc.driverEnv.${key}=${val},"
  PROPS+="spark.executorEnv.${key}=${val},"
done
PROPS="${PROPS%,}"  # strip trailing comma

# --- 4) Submit ---------------------------------------------------------------
echo ">> Submitting Dataproc Serverless batch (phases: ${PHASES_ARG})"
# shellcheck disable=SC2086  # PHASES_ARG is intentionally word-split into args.
gcloud dataproc batches submit pyspark main.py \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --deps-bucket="gs://${STAGING_BUCKET}" \
  --version="${RUNTIME_VERSION}" \
  --container-image="${IMAGE_URI}" \
  --py-files="mdp_modules.zip" \
  --properties="${PROPS}" \
  -- --phases ${PHASES_ARG}

echo ">> Submitted. Track it with:  gcloud dataproc batches list --region=${REGION}"
