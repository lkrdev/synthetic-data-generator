# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Vertex AI (Google Cloud) model client adapter.

Vertex AI exposes an OpenAI-compatible Chat Completions endpoint, so this adapter
reuses all of ``OpenAICompatibleClient`` and only overrides header construction to
inject a fresh OAuth2 bearer token from Google Cloud ADC on every request.
"""

from __future__ import annotations

from typing import Any

from data_designer.engine.models.clients.adapters.gcp_credentials import GcpTokenProvider
from data_designer.engine.models.clients.adapters.openai_compatible import OpenAICompatibleClient


class VertexAIClient(OpenAICompatibleClient):
    """OpenAI-compatible client for Vertex AI using ADC bearer tokens.

    Authentication uses a short-lived OAuth2 access token minted per request from
    Google Cloud Application Default Credentials, rather than a static API key.
    """

    def __init__(self, *, token_provider: GcpTokenProvider, **kwargs: Any) -> None:
        super().__init__(api_key=None, **kwargs)
        self._token_provider = token_provider

    def _build_headers(self, extra_headers: dict[str, str]) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token_provider.get_token()}",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers
