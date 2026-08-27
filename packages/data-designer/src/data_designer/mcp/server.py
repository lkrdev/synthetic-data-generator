# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
from typing import Any, Literal

from data_designer.mcp.tools.export import export_to_bigquery as _export_to_bigquery
from data_designer.mcp.tools.generate import generate_dataset as _generate_dataset
from data_designer.mcp.tools.introspect import introspect_catalog as _introspect_catalog
from data_designer.mcp.tools.preview import preview_dataset as _preview_dataset
from data_designer.mcp.tools.scaffold import scaffold_builder_script as _scaffold_builder_script
from data_designer.mcp.tools.validate import validate_builder as _validate_builder
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP(
    name="data-designer",
    instructions=(
        "DataDesigner MCP Server: Autonomous synthetic dataset generation, schema introspection, "
        "fast previewing, dataset creation, and cloud/BigQuery export."
    ),
)


@mcp.tool()
def introspect_catalog(
    family: str = "all",
    query: str | None = None,
) -> dict[str, Any]:
    """Discover available column types, samplers, validators, processors, personas, and models.

    Args:
        family: Schema family to inspect ('all', 'columns', 'samplers', 'validators', 'processors', 'constraints', 'personas', 'models').
        query: Optional substring or keyword filter.
    """
    return _introspect_catalog(family=family, query=query)


@mcp.tool()
def validate_builder(
    config_source: str | None = None,
    script_content: str | None = None,
) -> dict[str, Any]:
    """Validate a DataDesigner configuration (file path, URL, or raw script code) without executing generation.

    Args:
        config_source: Path or URL to a config file (.py, .yaml, .yml, .json).
        script_content: Raw Python script or YAML/JSON configuration content string.
    """
    return _validate_builder(config_source=config_source, script_content=script_content)


@mcp.tool()
def preview_dataset(
    config_source: str | None = None,
    script_content: str | None = None,
    num_records: int = 5,
    artifact_path: str = "./artifacts",
) -> dict[str, Any]:
    """Generate a fast preview sample of a synthetic dataset with Markdown table and column statistics.

    Args:
        config_source: Path or URL to a config file (.py, .yaml, .yml, .json).
        script_content: Raw Python script or YAML/JSON configuration content string.
        num_records: Number of sample records to generate (1 to 20, default 5).
        artifact_path: Directory where intermediate artifacts may be stored. Defaults to ./artifacts.
    """
    return _preview_dataset(
        config_source=config_source,
        script_content=script_content,
        num_records=num_records,
        artifact_path=artifact_path,
    )


@mcp.tool()
def generate_dataset(
    config_source: str | None = None,
    script_content: str | None = None,
    num_records: int = 100,
    dataset_name: str = "dataset",
    artifact_path: str = "./artifacts",
    output_format: Literal["parquet", "jsonl", "csv"] = "parquet",
    seed: int = 42,
) -> dict[str, Any]:
    """Execute full-scale synthetic dataset generation and save output files to disk.

    Args:
        config_source: Path or URL to a config file (.py, .yaml, .yml, .json).
        script_content: Raw Python script or YAML/JSON configuration content string.
        num_records: Total number of records to generate.
        dataset_name: Subfolder/dataset name for the output artifacts.
        artifact_path: Target directory to store output files. Defaults to ./artifacts.
        output_format: Single-file export format: 'parquet', 'jsonl', or 'csv'. Defaults to 'parquet'.
        seed: Random seed for deterministic generation. Defaults to 42.
    """
    return _generate_dataset(
        config_source=config_source,
        script_content=script_content,
        num_records=num_records,
        dataset_name=dataset_name,
        artifact_path=artifact_path,
        output_format=output_format,
        seed=seed,
    )


@mcp.tool()
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
    """
    return _export_to_bigquery(
        source_path=source_path,
        project_id=project_id,
        dataset_id=dataset_id,
        table_name=table_name,
        clustering_fields=clustering_fields,
        time_partitioning_field=time_partitioning_field,
        location=location,
    )


@mcp.tool()
def scaffold_builder_script(
    dataset_name: str,
    domain_description: str,
    columns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate a clean, PEP 723 compliant Python script scaffold for a DataDesigner dataset.

    Args:
        dataset_name: Descriptive name for the dataset (e.g. 'e_commerce_transactions').
        domain_description: High-level overview of what the dataset represents and intended use case.
        columns: Optional list of column definitions with 'name', 'type' (e.g. 'sampler', 'expression',
            'llm_structured'), and optional parameters.
    """
    return _scaffold_builder_script(
        dataset_name=dataset_name,
        domain_description=domain_description,
        columns=columns,
    )


def run_mcp_server() -> None:
    """Run the FastMCP server over stdio transport."""
    mcp.run(transport="stdio")


def main() -> None:
    """Main CLI entry point for data-designer-mcp."""
    parser = argparse.ArgumentParser(description="DataDesigner Model Context Protocol (MCP) Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type for MCP server (default: stdio)",
    )
    args, _ = parser.parse_known_args()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
