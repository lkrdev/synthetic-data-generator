# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import types
from unittest.mock import MagicMock

import pytest

import data_designer.lazy_heavy_imports as lazy
from data_designer.config.models import ChatCompletionInferenceParams, ModelConfig, ModelProvider
from data_designer.engine.model_provider import ModelProviderRegistry
from data_designer.engine.models.clients.adapters.gcp_credentials import GcpTokenProvider
from data_designer.engine.models.clients.adapters.http_model_client import ClientConcurrencyMode
from data_designer.engine.models.clients.adapters.vertex_ai import VertexAIClient
from data_designer.engine.models.clients.factory import create_model_client
from data_designer.engine.models.errors import ModelAuthenticationError
from data_designer.engine.secret_resolver import SecretResolver

# --- VertexAIClient header injection ---


def test_build_headers_injects_bearer_token() -> None:
    token_provider = MagicMock(spec=GcpTokenProvider)
    token_provider.get_token.return_value = "test-token"
    client = VertexAIClient(
        provider_name="vertex",
        endpoint="https://us-central1-aiplatform.googleapis.com/v1/projects/p/locations/us-central1/endpoints/openapi",
        token_provider=token_provider,
    )
    headers = client._build_headers({})
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Content-Type"] == "application/json"


def test_build_headers_merges_extra_headers() -> None:
    token_provider = MagicMock(spec=GcpTokenProvider)
    token_provider.get_token.return_value = "tok"
    client = VertexAIClient(provider_name="vertex", endpoint="https://x/openapi", token_provider=token_provider)
    headers = client._build_headers({"X-Custom": "value"})
    assert headers["X-Custom"] == "value"
    assert headers["Authorization"] == "Bearer tok"


def test_build_headers_fetches_token_each_call() -> None:
    token_provider = MagicMock(spec=GcpTokenProvider)
    token_provider.get_token.side_effect = ["tok-1", "tok-2"]
    client = VertexAIClient(provider_name="vertex", endpoint="https://x/openapi", token_provider=token_provider)
    assert client._build_headers({})["Authorization"] == "Bearer tok-1"
    assert client._build_headers({})["Authorization"] == "Bearer tok-2"
    assert token_provider.get_token.call_count == 2


# --- GcpTokenProvider ADC handling ---


def _fake_credentials(*, valid: bool, token: str = "adc-token") -> MagicMock:
    creds = MagicMock()
    creds.valid = valid
    creds.token = token

    def _refresh(_request: object) -> None:
        creds.valid = True
        creds.token = token

    creds.refresh.side_effect = _refresh
    return creds


def test_token_provider_returns_valid_token_without_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    creds = _fake_credentials(valid=True, token="fresh")
    fake_google_auth = types.SimpleNamespace(default=MagicMock(return_value=(creds, "my-project")))
    monkeypatch.setattr(lazy, "google_auth", fake_google_auth, raising=False)

    provider = GcpTokenProvider()
    assert provider.get_token() == "fresh"
    creds.refresh.assert_not_called()


def test_token_provider_refreshes_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    creds = _fake_credentials(valid=False, token="refreshed")
    fake_google_auth = types.SimpleNamespace(default=MagicMock(return_value=(creds, "my-project")))
    fake_requests = types.SimpleNamespace(Request=MagicMock(return_value=object()))
    monkeypatch.setattr(lazy, "google_auth", fake_google_auth, raising=False)
    monkeypatch.setattr(lazy, "google_auth_requests", fake_requests, raising=False)

    provider = GcpTokenProvider()
    assert provider.get_token() == "refreshed"
    creds.refresh.assert_called_once()


def test_token_provider_raises_authentication_error_when_adc_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise Exception("could not find ADC")

    fake_google_auth = types.SimpleNamespace(default=MagicMock(side_effect=_boom))
    monkeypatch.setattr(lazy, "google_auth", fake_google_auth, raising=False)

    provider = GcpTokenProvider()
    with pytest.raises(ModelAuthenticationError):
        provider.get_token()


# --- Factory routing ---


@pytest.fixture
def secret_resolver() -> SecretResolver:
    resolver = MagicMock(spec=SecretResolver)
    resolver.resolve.return_value = "resolved-key"
    return resolver


@pytest.fixture
def vertex_model_config() -> ModelConfig:
    return ModelConfig(
        alias="gemini",
        model="google/gemini-2.5-pro",
        inference_parameters=ChatCompletionInferenceParams(),
        provider="vertex",
    )


def test_vertex_provider_routes_to_vertex_client(
    vertex_model_config: ModelConfig,
    secret_resolver: SecretResolver,
) -> None:
    provider = ModelProvider(name="vertex", provider_type="vertex", project="my-project", location="us-central1")
    registry = ModelProviderRegistry(providers=[provider])
    client = create_model_client(vertex_model_config, secret_resolver, registry)
    assert isinstance(client, VertexAIClient)


def test_vertex_provider_type_case_insensitive_routing(
    vertex_model_config: ModelConfig,
    secret_resolver: SecretResolver,
) -> None:
    provider = ModelProvider(name="vertex", provider_type="Vertex", project="my-project")
    registry = ModelProviderRegistry(providers=[provider])
    client = create_model_client(vertex_model_config, secret_resolver, registry)
    assert isinstance(client, VertexAIClient)


def test_vertex_client_concurrency_mode_forwarded(
    vertex_model_config: ModelConfig,
    secret_resolver: SecretResolver,
) -> None:
    provider = ModelProvider(name="vertex", provider_type="vertex", project="my-project")
    registry = ModelProviderRegistry(providers=[provider])
    client = create_model_client(
        vertex_model_config, secret_resolver, registry, client_concurrency_mode=ClientConcurrencyMode.ASYNC
    )
    assert isinstance(client, VertexAIClient)
    assert client.concurrency_mode == ClientConcurrencyMode.ASYNC
