# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _discover_parquet_files(source_path: str, table_name: str | None = None) -> list[tuple[str, Path]]:
    """Discover parquet files and associate each with a target table name."""
    p = Path(source_path).resolve()
    files: list[tuple[str, Path]] = []

    if p.is_file() and p.suffix.lower() == ".parquet":
        tbl = table_name or p.stem
        files.append((tbl, p))
    elif p.is_dir():
        # Look for direct parquet files in the directory
        direct_parquets = list(p.glob("*.parquet"))
        if direct_parquets:
            for pf in direct_parquets:
                files.append((pf.stem, pf))
        else:
            # Look for subdirectories with parquet files (e.g. exported datasets)
            for sub in p.iterdir():
                if sub.is_dir():
                    sub_parquets = list(sub.glob("*.parquet"))
                    for sp in sub_parquets:
                        files.append((sub.name, sp))
    return files


def export_to_bigquery(
    source_path: str,
    project_id: str,
    dataset_id: str,
    table_name: str | None = None,
    clustering_fields: list[str] | None = None,
    time_partitioning_field: str | None = None,
    location: str = "US",
) -> dict[str, Any]:
    """Export generated Parquet dataset files into Google Cloud BigQuery tables.

    Attempts to load files directly via the BigQuery Python client using Application Default Credentials (ADC).
    If BigQuery client is unavailable or credentials require CLI execution, automatically generates a
    ready-to-run shell script.

    Args:
        source_path: Path to a .parquet file or directory containing parquet datasets.
        project_id: Google Cloud Project ID (e.g. 'looker-demo-392616').
        dataset_id: BigQuery dataset name (e.g. 'synthetic_banking').
        table_name: Optional explicit table name override if source_path is a single file.
        clustering_fields: Optional list of fields to cluster the table by.
        time_partitioning_field: Optional TIMESTAMP or DATE column for daily partitioning.
        location: BigQuery dataset geographic location. Defaults to 'US'.

    Returns:
        Summary of loaded tables, row counts, or generated loading script instructions.
    """
    parquet_files = _discover_parquet_files(source_path, table_name)
    if not parquet_files:
        return {
            "status": "error",
            "message": f"No .parquet files found in source path: '{source_path}'",
        }

    # Try loading with google-cloud-bigquery client
    try:
        import google.auth
        from google.cloud import bigquery
        from google.cloud.bigquery import (
            Dataset,
            LoadJobConfig,
            SourceFormat,
            TimePartitioning,
            TimePartitioningType,
            WriteDisposition,
        )

        credentials, detected_project = google.auth.default()
        client = bigquery.Client(project=project_id, credentials=credentials, location=location)

        # 1. Ensure dataset exists
        dataset_ref = client.dataset(dataset_id)
        try:
            client.get_dataset(dataset_ref)
        except Exception:
            new_dataset = Dataset(dataset_ref)
            new_dataset.location = location
            client.create_dataset(new_dataset, exists_ok=True)

        loaded_tables = []
        for tbl_name, file_path in parquet_files:
            table_ref = dataset_ref.table(tbl_name)
            job_config = LoadJobConfig(
                source_format=SourceFormat.PARQUET,
                write_disposition=WriteDisposition.WRITE_TRUNCATE,
                autodetect=True,
            )
            if clustering_fields:
                job_config.clustering_fields = clustering_fields
            if time_partitioning_field:
                job_config.time_partitioning = TimePartitioning(
                    type_=TimePartitioningType.DAY,
                    field=time_partitioning_field,
                )

            with open(file_path, "rb") as source_file:
                job = client.load_table_from_file(source_file, table_ref, job_config=job_config)
                job.result()  # Wait for the load job to complete

            loaded_table = client.get_table(table_ref)
            loaded_tables.append(
                {
                    "table_id": f"{project_id}.{dataset_id}.{tbl_name}",
                    "row_count": loaded_table.num_rows,
                    "size_bytes": loaded_table.num_bytes,
                    "file": str(file_path),
                }
            )

        return {
            "status": "success",
            "mode": "python_sdk",
            "message": f"Successfully loaded {len(loaded_tables)} table(s) into {project_id}:{dataset_id}",
            "tables": loaded_tables,
        }

    except Exception as sdk_err:
        # Fallback: Generate load script
        script_lines = [
            "#!/usr/bin/env bash",
            "set -e",
            "export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false",
            "export GOOGLE_API_USE_CLIENT_CERTIFICATE=false",
            f'PROJECT_ID="{project_id}"',
            f'DATASET_ID="{dataset_id}"',
            f'LOCATION="{location}"',
            "",
            "# Ensure dataset exists",
            'bq --project_id="${PROJECT_ID}" show "${PROJECT_ID}:${DATASET_ID}" >/dev/null 2>&1 || \\',
            'bq --project_id="${PROJECT_ID}" mk --location="${LOCATION}" --dataset "${PROJECT_ID}:${DATASET_ID}"',
            "",
        ]

        for tbl_name, file_path in parquet_files:
            cmd = 'bq --project_id="${PROJECT_ID}" load --source_format=PARQUET --replace --autodetect '
            if clustering_fields:
                cmd += f'--clustering_fields="{",".join(clustering_fields)}" '
            if time_partitioning_field:
                cmd += f'--time_partitioning_field="{time_partitioning_field}" --time_partitioning_type="DAY" '
            cmd += f'"${{PROJECT_ID}}:${{DATASET_ID}}.{tbl_name}" "{file_path}"'
            script_lines.append(f'echo "Loading {tbl_name}..."')
            script_lines.append(cmd)

        script_content = "\n".join(script_lines)
        script_output_path = Path("./scripts/load_to_bigquery.sh").resolve()
        script_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(script_output_path, "w", encoding="utf-8") as sf:
            sf.write(script_content)
        os.chmod(script_output_path, 0o755)

        return {
            "status": "fallback_script_generated",
            "mode": "bash_script",
            "reason": f"Direct SDK load encountered: {sdk_err}. Generated executable script instead.",
            "script_path": str(script_output_path),
            "execute_command": f"./scripts/load_to_bigquery.sh {project_id} {dataset_id}",
            "tables_to_load": [t for t, _ in parquet_files],
        }
