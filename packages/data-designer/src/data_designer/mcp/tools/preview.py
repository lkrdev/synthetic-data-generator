# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
from typing import Any

from data_designer.interface import DataDesigner
from data_designer.mcp.tools.validate import _resolve_builder


def _format_markdown_table(records: list[dict[str, Any]]) -> str:
    """Format records into a clean Markdown table."""
    if not records:
        return "_No records generated._"

    headers = list(records[0].keys())
    lines = []
    # Header row
    lines.append("| " + " | ".join(headers) + " |")
    # Separator row
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    # Value rows
    for row in records:
        row_vals = []
        for h in headers:
            val = row.get(h)
            if val is None:
                row_vals.append("_null_")
            elif isinstance(val, (dict, list)):
                s = str(val).replace("\n", " ")
                if len(s) > 40:
                    s = s[:37] + "..."
                row_vals.append(f"`{s}`")
            else:
                s = str(val).replace("\n", " ").replace("|", "\\|")
                if len(s) > 50:
                    s = s[:47] + "..."
                row_vals.append(s)
        lines.append("| " + " | ".join(row_vals) + " |")

    return "\n".join(lines)


def _compute_column_stats(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Compute summary statistics for generated columns in preview."""
    if not records:
        return {}

    stats: dict[str, dict[str, Any]] = {}
    total_rows = len(records)
    headers = list(records[0].keys())

    for h in headers:
        values = [r.get(h) for r in records]
        null_count = sum(1 for v in values if v is None)
        non_null_values = [v for v in values if v is not None]
        try:
            unique_count = len(set(str(v) for v in non_null_values))
        except Exception:
            unique_count = len(non_null_values)

        inferred_type = type(non_null_values[0]).__name__ if non_null_values else "NoneType"

        stats[h] = {
            "type": inferred_type,
            "null_count": null_count,
            "null_percentage": round((null_count / total_rows) * 100, 1) if total_rows > 0 else 0,
            "unique_count": unique_count,
            "sample_value": str(non_null_values[0])[:100] if non_null_values else None,
        }

    return stats


def preview_dataset(
    config_source: str | None = None,
    script_content: str | None = None,
    num_records: int = 5,
    artifact_path: str = "./artifacts",
) -> dict[str, Any]:
    """Generate a fast preview sample of a synthetic dataset for validation and iteration.

    Args:
        config_source: Path or URL to a config file (.py, .yaml, .yml, .json).
        script_content: Raw Python script or YAML/JSON configuration content string.
        num_records: Number of sample records to generate (1 to 20, default 5).
        artifact_path: Directory where intermediate artifacts may be stored. Defaults to ./artifacts.

    Returns:
        Preview results containing sample records, Markdown table, and column statistics.
    """
    temp_path: str | None = None
    try:
        capped_num_records = max(1, min(num_records, 20))
        builder, temp_path = _resolve_builder(config_source, script_content)
        designer = DataDesigner(artifact_path=artifact_path)
        preview_results = designer.preview(builder, num_records=capped_num_records)

        records: list[dict[str, Any]] = (
            preview_results.dataset.to_dict(orient="records") if preview_results.dataset is not None else []
        )
        md_table = _format_markdown_table(records)
        col_stats = _compute_column_stats(records)

        return {
            "status": "success",
            "num_records": len(records),
            "columns": list(records[0].keys()) if records else [],
            "markdown_table": md_table,
            "records": records,
            "column_stats": col_stats,
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
