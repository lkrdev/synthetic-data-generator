# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest
from pydantic import ValidationError

from data_designer.config.models import ModelProvider, build_vertex_openai_endpoint


@pytest.fixture(autouse=True)
def _clear_vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep provider resolution deterministic regardless of the caller's shell.

    ``ModelProvider`` now falls back to ``GOOGLE_CLOUD_PROJECT`` /
    ``GOOGLE_CLOUD_LOCATION`` for the ``vertex`` provider type, so every test
    starts from a clean slate and opts into env vars explicitly when needed.
    """
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)


def test_build_vertex_openai_endpoint_regional() -> None:
    url = build_vertex_openai_endpoint("my-project", "us-central1")
    assert url == (
        "https://us-central1-aiplatform.googleapis.com/v1/projects/my-project/locations/us-central1/endpoints/openapi"
    )


def test_build_vertex_openai_endpoint_global() -> None:
    url = build_vertex_openai_endpoint("my-project", "global")
    assert url == "https://aiplatform.googleapis.com/v1/projects/my-project/locations/global/endpoints/openapi"


def test_vertex_provider_derives_regional_endpoint() -> None:
    provider = ModelProvider(name="vertex", provider_type="vertex", project="my-project", location="us-central1")
    assert provider.endpoint == (
        "https://us-central1-aiplatform.googleapis.com/v1/projects/my-project/locations/us-central1/endpoints/openapi"
    )
    assert provider.api_key is None


def test_vertex_provider_derives_global_endpoint() -> None:
    provider = ModelProvider(name="vertex", provider_type="vertex", project="my-project", location="global")
    assert provider.endpoint == (
        "https://aiplatform.googleapis.com/v1/projects/my-project/locations/global/endpoints/openapi"
    )


def test_vertex_provider_defaults_location() -> None:
    provider = ModelProvider(name="vertex", provider_type="vertex", project="my-project")
    assert provider.location == "us-central1"
    assert "us-central1" in provider.endpoint


def test_vertex_provider_type_case_insensitive() -> None:
    provider = ModelProvider(name="vertex", provider_type="Vertex", project="my-project")
    assert provider.provider_type == "vertex"
    assert provider.endpoint is not None


def test_vertex_provider_explicit_endpoint_is_preserved() -> None:
    endpoint = "https://us-central1-aiplatform.googleapis.com/v1/projects/p/locations/us-central1/endpoints/openapi"
    provider = ModelProvider(name="vertex", provider_type="vertex", project="p", endpoint=endpoint)
    assert provider.endpoint == endpoint


def test_vertex_provider_requires_project() -> None:
    with pytest.raises(ValidationError, match="requires a `project`"):
        ModelProvider(name="vertex", provider_type="vertex")


def test_vertex_provider_project_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
    provider = ModelProvider(name="vertex", provider_type="vertex")
    assert provider.project == "env-project"
    assert "projects/env-project/" in provider.endpoint


def test_vertex_provider_location_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "europe-west4")
    provider = ModelProvider(name="vertex", provider_type="vertex")
    assert provider.location == "europe-west4"
    assert "locations/europe-west4/" in provider.endpoint
    assert "europe-west4-aiplatform.googleapis.com" in provider.endpoint


def test_vertex_provider_explicit_project_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
    provider = ModelProvider(name="vertex", provider_type="vertex", project="explicit-project")
    assert provider.project == "explicit-project"
    assert "projects/explicit-project/" in provider.endpoint


def test_vertex_provider_explicit_location_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "europe-west4")
    provider = ModelProvider(name="vertex", provider_type="vertex", location="global")
    assert provider.location == "global"
    assert "locations/global/" in provider.endpoint


def test_vertex_provider_env_location_ignored_without_project(monkeypatch: pytest.MonkeyPatch) -> None:
    # location env alone must not satisfy the required-project check.
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "europe-west4")
    with pytest.raises(ValidationError, match="requires a `project`"):
        ModelProvider(name="vertex", provider_type="vertex")


def test_non_vertex_provider_requires_endpoint() -> None:
    with pytest.raises(ValidationError, match="requires an `endpoint`"):
        ModelProvider(name="openai", provider_type="openai")


def test_non_vertex_provider_ignores_gcp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # The env fallback is scoped to the vertex provider type only.
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
    with pytest.raises(ValidationError, match="requires an `endpoint`"):
        ModelProvider(name="openai", provider_type="openai")


def test_openai_provider_still_works() -> None:
    provider = ModelProvider(name="openai", endpoint="https://api.openai.com/v1", provider_type="openai")
    assert provider.endpoint == "https://api.openai.com/v1"
    assert provider.project is None
    assert provider.location is None
