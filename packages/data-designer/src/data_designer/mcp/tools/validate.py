# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import tempfile
from typing import Any

from data_designer.cli.utils.config_loader import ConfigLoadError, load_config_builder
from data_designer.config.config_builder import DataDesignerConfigBuilder
from data_designer.config.errors import InvalidConfigError
from data_designer.interface import DataDesigner


def _resolve_builder(
    config_source: str | None = None,
    script_content: str | None = None,
) -> tuple[DataDesignerConfigBuilder, str | None]:
    """Helper to resolve a DataDesignerConfigBuilder from either a path or raw script content."""
    if not config_source and not script_content:
        raise ValueError("Either 'config_source' (file path) or 'script_content' (code string) must be provided.")

    temp_path: str | None = None
    if script_content is not None:
        trimmed = script_content.strip()
        if trimmed.startswith("{"):
            ext = ".json"
        elif trimmed.startswith("#") or "import data_designer" in trimmed or "def load_config_builder" in trimmed:
            ext = ".py"
        else:
            ext = ".yaml"

        fd, temp_file = tempfile.mkstemp(suffix=ext, prefix="dd_mcp_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script_content)
        temp_path = temp_file
        config_source = temp_file

    try:
        assert config_source is not None
        builder = load_config_builder(config_source)
        return builder, temp_path
    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def validate_builder(
    config_source: str | None = None,
    script_content: str | None = None,
) -> dict[str, Any]:
    """Validate a DataDesigner dataset builder configuration.

    Checks that all referenced columns, samplers, models, and processors compile cleanly.

    Args:
        config_source: Path or URL to a config file (.py, .yaml, .yml, .json).
        script_content: Raw Python script or YAML/JSON configuration content string.

    Returns:
        Validation results with column summary, or diagnostic error messages with remediation hints.
    """
    temp_path: str | None = None
    try:
        builder, temp_path = _resolve_builder(config_source, script_content)
        designer = DataDesigner()
        designer.validate(builder)
        config = builder.build()

        column_summaries = []
        for col in config.columns:
            column_summaries.append(
                {
                    "name": col.name,
                    "column_type": getattr(col, "column_type", "unknown"),
                    "drop": getattr(col, "drop", False),
                }
            )

        return {
            "valid": True,
            "status": "success",
            "message": "Configuration is valid and compiles successfully.",
            "column_count": len(config.columns),
            "columns": column_summaries,
            "has_seed_dataset": config.seed_config is not None,
            "processor_count": len(config.processors) if config.processors else 0,
        }
    except InvalidConfigError as exc:
        return {
            "valid": False,
            "status": "error",
            "error_type": "InvalidConfigError",
            "message": str(exc),
            "remediation": (
                "Review the column dependencies, Jinja2 template references (e.g. {{ col_name }}), "
                "and ensure all required sampler parameters are specified."
            ),
        }
    except ConfigLoadError as exc:
        return {
            "valid": False,
            "status": "error",
            "error_type": "ConfigLoadError",
            "message": str(exc),
            "remediation": (
                "Ensure the Python script defines a 'load_config_builder()' function that returns a "
                "DataDesignerConfigBuilder instance, or check YAML/JSON syntax."
            ),
        }
    except Exception as exc:
        return {
            "valid": False,
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
