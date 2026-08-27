# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from data_designer.mcp.server import mcp
from data_designer.mcp.tools.export import export_to_bigquery
from data_designer.mcp.tools.generate import generate_dataset
from data_designer.mcp.tools.introspect import introspect_catalog
from data_designer.mcp.tools.preview import preview_dataset
from data_designer.mcp.tools.scaffold import scaffold_builder_script
from data_designer.mcp.tools.validate import validate_builder


def test_mcp_tool_registration():
    """Verify that all core MCP tools are registered on the FastMCP instance."""
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    expected_tools = [
        "introspect_catalog",
        "validate_builder",
        "preview_dataset",
        "generate_dataset",
        "export_to_bigquery",
        "scaffold_builder_script",
    ]
    for expected in expected_tools:
        assert expected in tool_names, f"Tool '{expected}' missing from MCP server."


def test_introspect_catalog_samplers():
    """Verify introspect_catalog discovers samplers accurately."""
    res = introspect_catalog(family="samplers", query="person")
    assert res["status"] == "success"
    assert "samplers" in res["catalog"]
    sampler_names = [s["type_name"] for s in res["catalog"]["samplers"]]
    assert "person" in sampler_names or "person_from_faker" in sampler_names


def test_scaffold_and_validate():
    """Verify scaffold generates valid Python scripts that compile successfully."""
    scaffold = scaffold_builder_script(
        dataset_name="user_analytics",
        domain_description="Mock user analytics dataset for testing",
    )
    assert scaffold["status"] == "success"
    assert "load_config_builder" in scaffold["script_content"]

    val = validate_builder(script_content=scaffold["script_content"])
    assert val["valid"] is True
    assert val["column_count"] >= 3


def test_preview_dataset(tmp_path: Path):
    """Verify preview_dataset generates records, markdown table, and column statistics."""
    scaffold = scaffold_builder_script("test_preview", "Preview testing")
    preview = preview_dataset(
        script_content=scaffold["script_content"],
        num_records=3,
        artifact_path=str(tmp_path),
    )
    assert preview["status"] == "success"
    assert preview["num_records"] == 3
    assert len(preview["records"]) == 3
    assert "| record_id |" in preview["markdown_table"]
    assert "record_id" in preview["column_stats"]


def test_generate_dataset(tmp_path: Path):
    """Verify generate_dataset writes parquet files and exported artifacts."""
    scaffold = scaffold_builder_script("test_gen", "Generation testing")
    gen = generate_dataset(
        script_content=scaffold["script_content"],
        num_records=5,
        dataset_name="gen_run",
        artifact_path=str(tmp_path),
        output_format="parquet",
    )
    assert gen["status"] == "success"
    assert gen["num_records"] == 5
    assert Path(gen["exported_file"]).exists()


def test_export_to_bigquery_fallback(tmp_path: Path):
    """Verify export_to_bigquery generates a valid fallback shell script when SDK is not connecting."""
    fake_parquet = tmp_path / "accounts.parquet"
    fake_parquet.write_bytes(b"PAR1fakecontent")

    res = export_to_bigquery(
        source_path=str(tmp_path),
        project_id="mock-project",
        dataset_id="mock_dataset",
    )
    assert res["status"] in ("success", "fallback_script_generated")
