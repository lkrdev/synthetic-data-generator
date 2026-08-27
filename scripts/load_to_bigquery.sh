#!/usr/bin/env bash
set -e
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false
export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
PROJECT_ID="mock-project"
DATASET_ID="mock_dataset"
LOCATION="US"

# Ensure dataset exists
bq --project_id="${PROJECT_ID}" show "${PROJECT_ID}:${DATASET_ID}" >/dev/null 2>&1 || \
bq --project_id="${PROJECT_ID}" mk --location="${LOCATION}" --dataset "${PROJECT_ID}:${DATASET_ID}"

echo "Loading accounts..."
bq --project_id="${PROJECT_ID}" load --source_format=PARQUET --replace --autodetect "${PROJECT_ID}:${DATASET_ID}.accounts" "/tmp/pytest-of-maluka/pytest-11/test_export_to_bigquery_fallba0/accounts.parquet"