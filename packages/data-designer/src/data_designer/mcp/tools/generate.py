# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from data_designer.config.run_config import RunConfig
from data_designer.interface import DataDesigner
from data_designer.mcp.tools.validate import _resolve_builder


def generate_dataset(
    config_source: str | None = None,
    script_content: str | None = None,
    num_records: int = 100,
    dataset_name: str = "dataset",
    artifact_path: str = "./artifacts",
    output_format: Literal["parquet", "jsonl", "csv"] = "parquet",
) -> dict[str, Any]:
    """Execute full-scale synthetic dataset generation and save output files to disk.

    Args:
        config_source: Path or URL to a config file (.py, .yaml, .yml, .json).
        script_content: Raw Python script or YAML/JSON configuration content string.
        num_records: Total number of records to generate.
        dataset_name: Subfolder/dataset name for the output artifacts.
        artifact_path: Target directory to store output files. Defaults to ./artifacts.
        output_format: Single-file export format: 'parquet', 'jsonl', or 'csv'. Defaults to 'parquet'.

    Returns:
        Summary of the generation run including record count, output paths, and file locations.
    """
    temp_path: str | None = None
    try:
        # Ensure artifact path directory exists
        Path(artifact_path).mkdir(parents=True, exist_ok=True)

        builder, temp_path = _resolve_builder(config_source, script_content)
        designer = DataDesigner(artifact_path=artifact_path)

        # Configure run settings
        run_cfg = RunConfig(display_tui=False)
        designer.set_run_config(run_cfg)

        creation_results = designer.create(
            config_builder=builder,
            num_records=num_records,
            dataset_name=dataset_name,
        )

        total_records = creation_results.count_records()
        base_dir = creation_results.artifact_storage.base_dataset_path
        final_dir = creation_results.artifact_storage.final_dataset_path

        # Export to single file if requested
        export_file_name = f"{dataset_name}.{output_format}"
        export_target_path = base_dir / export_file_name
        exported_path = creation_results.export(export_target_path, format=output_format)

        return {
            "status": "success",
            "message": f"Successfully generated {total_records} records.",
            "num_records": total_records,
            "dataset_name": dataset_name,
            "base_dataset_dir": str(base_dir),
            "parquet_files_dir": str(final_dir),
            "exported_file": str(exported_path),
            "artifact_path": str(creation_results.artifact_storage.artifact_path),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
