# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

from data_designer.cli.utils.agent_introspection import (
    discover_family_types,
    get_family_names,
    get_family_spec,
    get_model_aliases_state,
    get_persona_datasets_state,
)
from data_designer.config.utils.constants import DATA_DESIGNER_HOME


def _extract_field_details(model_cls: type) -> dict[str, dict[str, Any]]:
    """Extract field names, types, defaults, and descriptions from a Pydantic model."""
    fields: dict[str, dict[str, Any]] = {}
    if not hasattr(model_cls, "model_fields"):
        return fields

    for name, field_info in model_cls.model_fields.items():
        annotation_str = str(field_info.annotation) if field_info.annotation is not None else "Any"
        annotation_str = (
            annotation_str.replace("typing.", "")
            .replace("collections.abc.", "")
            .replace("data_designer.config.", "dd.")
        )
        fields[name] = {
            "type": annotation_str,
            "description": field_info.description or "",
            "required": field_info.is_required(),
        }
    return fields


def introspect_catalog(
    family: str = "all",
    query: str | None = None,
) -> dict[str, Any]:
    """Discover available column types, samplers, validators, processors, personas, and models.

    Args:
        family: Schema family to inspect. Choices: 'all', 'columns', 'samplers', 'validators',
            'processors', 'constraints', 'personas', 'models'. Defaults to 'all'.
        query: Optional substring or keyword filter to narrow down results.

    Returns:
        Structured catalog with descriptions, parameter schemas, and usability status.
    """
    normalized_family = family.strip().lower()
    results: dict[str, Any] = {}

    available_families = get_family_names()

    # 1. Schema families (columns, samplers, validators, processors, constraints)
    target_families = available_families if normalized_family in ("all", "*", "") else [normalized_family]

    for fam in target_families:
        if fam in available_families:
            spec = get_family_spec(fam)
            types_dict = discover_family_types(fam)
            fam_catalog: list[dict[str, Any]] = []

            for type_name, cls in types_dict.items():
                doc = (cls.__doc__ or "").strip().split("\n\n")[0]
                entry = {
                    "type_name": type_name,
                    "class_name": cls.__name__,
                    "discriminator_field": spec.discriminator_field,
                    "description": doc,
                    "fields": _extract_field_details(cls),
                }

                if query:
                    q = query.lower()
                    haystack = (f"{type_name} {cls.__name__} {doc} {' '.join(entry['fields'].keys())}").lower()
                    if q not in haystack:
                        continue

                fam_catalog.append(entry)

            results[fam] = fam_catalog

    # 2. Models
    if normalized_family in ("all", "models"):
        try:
            aliases = get_model_aliases_state(DATA_DESIGNER_HOME)
            model_list = [
                {
                    "alias": a.alias,
                    "model": a.model,
                    "provider": a.provider,
                    "generation_type": a.generation_type,
                    "usable": a.usable,
                    "reason": a.reason,
                }
                for a in aliases
            ]
            if query:
                q = query.lower()
                model_list = [
                    m
                    for m in model_list
                    if q in f"{m['alias']} {m['model']} {m['provider']} {m['generation_type']}".lower()
                ]
            results["models"] = model_list
        except Exception as e:
            results["models"] = {"error": str(e)}

    # 3. Personas
    if normalized_family in ("all", "personas"):
        try:
            personas = get_persona_datasets_state(DATA_DESIGNER_HOME)
            persona_list = [
                {
                    "locale": p.locale,
                    "size_gb": p.size_gb,
                    "installed": p.installed,
                }
                for p in personas
            ]
            if query:
                q = query.lower()
                persona_list = [p for p in persona_list if q in p["locale"].lower()]
            results["personas"] = persona_list
        except Exception as e:
            results["personas"] = {"error": str(e)}

    return {
        "status": "success",
        "family": family,
        "catalog": results,
    }
