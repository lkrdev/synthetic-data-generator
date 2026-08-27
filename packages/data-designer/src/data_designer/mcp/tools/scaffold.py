# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any


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

    Returns:
        Generated Python script content and instructions.
    """
    clean_name = dataset_name.lower().replace("-", "_").replace(" ", "_")

    col_blocks = []
    if columns:
        for c in columns:
            c_name = c.get("name", "col")
            c_type = c.get("type", "sampler").lower()
            if c_type in ("sampler", "sampler_column"):
                sampler_type = c.get("sampler_type", "category")
                if sampler_type == "category":
                    col_blocks.append(
                        f"    builder.add_column(\n"
                        f"        dd.SamplerColumnConfig(\n"
                        f'            name="{c_name}",\n'
                        f'            sampler_type="category",\n'
                        f'            params=dd.CategorySamplerParams(values=["A", "B", "C"]),\n'
                        f"        )\n"
                        f"    )"
                    )
                elif sampler_type == "uniform":
                    col_blocks.append(
                        f"    builder.add_column(\n"
                        f"        dd.SamplerColumnConfig(\n"
                        f'            name="{c_name}",\n'
                        f'            sampler_type="uniform",\n'
                        f"            params=dd.UniformSamplerParams(low=0.0, high=100.0),\n"
                        f"        )\n"
                        f"    )"
                    )
                elif sampler_type in ("person_from_faker", "person"):
                    col_blocks.append(
                        f"    builder.add_column(\n"
                        f"        dd.SamplerColumnConfig(\n"
                        f'            name="{c_name}",\n'
                        f"            drop=True,\n"
                        f'            sampler_type="person_from_faker",\n'
                        f'            params=dd.PersonFromFakerSamplerParams(locale="en_US"),\n'
                        f"        )\n"
                        f"    )"
                    )
                else:
                    col_blocks.append(
                        f"    builder.add_column(\n"
                        f"        dd.SamplerColumnConfig(\n"
                        f'            name="{c_name}",\n'
                        f'            sampler_type="uuid",\n'
                        f"            params=dd.UUIDSamplerParams(),\n"
                        f"        )\n"
                        f"    )"
                    )
            elif c_type in ("expression", "expr"):
                expr = c.get("expr", "{{ col }}")
                col_blocks.append(
                    f"    builder.add_column(\n"
                    f"        dd.ExpressionColumnConfig(\n"
                    f'            name="{c_name}",\n'
                    f'            expr="{expr}",\n'
                    f"        )\n"
                    f"    )"
                )
            else:
                col_blocks.append(
                    f"    # Column: {c_name} ({c_type})\n"
                    f"    builder.add_column(\n"
                    f"        dd.SamplerColumnConfig(\n"
                    f'            name="{c_name}",\n'
                    f'            sampler_type="uuid",\n'
                    f"            params=dd.UUIDSamplerParams(),\n"
                    f"        )\n"
                    f"    )"
                )
    else:
        # Default starter columns
        col_blocks.append(
            "    # 1. UUID primary key\n"
            "    builder.add_column(\n"
            "        dd.SamplerColumnConfig(\n"
            '            name="record_id",\n'
            '            sampler_type="uuid",\n'
            "            params=dd.UUIDSamplerParams(),\n"
            "        )\n"
            "    )"
        )
        col_blocks.append(
            "    # 2. Categorical distribution\n"
            "    builder.add_column(\n"
            "        dd.SamplerColumnConfig(\n"
            '            name="tier",\n'
            '            sampler_type="category",\n'
            "            params=dd.CategorySamplerParams(\n"
            '                values=["STANDARD", "PREMIUM", "ENTERPRISE"],\n'
            "                weights=[0.7, 0.25, 0.05],\n"
            "            ),\n"
            "        )\n"
            "    )"
        )
        col_blocks.append(
            "    # 3. Numeric distribution\n"
            "    builder.add_column(\n"
            "        dd.SamplerColumnConfig(\n"
            '            name="engagement_score",\n'
            '            sampler_type="uniform",\n'
            "            params=dd.UniformSamplerParams(low=0.0, high=100.0, decimal_places=2),\n"
            "        )\n"
            "    )"
        )

    columns_code = "\n\n".join(col_blocks)

    script_content = f'''# /// script
# dependencies = [
#   "data-designer",
#   "pydantic",
# ]
# ///
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Synthetic dataset generator for {clean_name}.

{domain_description}
"""

from __future__ import annotations

import data_designer.config as dd


def load_config_builder() -> dd.DataDesignerConfigBuilder:
    """Build and return the DataDesigner configuration."""
    builder = dd.DataDesignerConfigBuilder()

{columns_code}

    return builder
'''

    return {
        "status": "success",
        "dataset_name": clean_name,
        "suggested_filename": f"{clean_name}.py",
        "script_content": script_content,
    }
