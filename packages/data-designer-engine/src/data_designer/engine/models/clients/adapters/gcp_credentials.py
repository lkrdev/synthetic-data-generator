# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Google Cloud Application Default Credentials (ADC) token provider.

Provides short-lived OAuth2 access tokens for authenticating to Vertex AI using
the standard ``google-auth`` library. Tokens are cached and refreshed on expiry.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import data_designer.lazy_heavy_imports as lazy
from data_designer.config.utils.constants import VERTEX_AUTH_SCOPE
from data_designer.engine.models.errors import FormattedLLMErrorMessage, ModelAuthenticationError

if TYPE_CHECKING:
    from google.auth.credentials import Credentials


class GcpTokenProvider:
    """Supplies OAuth2 access tokens from Google Cloud ADC.

    Uses Application Default Credentials via ``google.auth.default()`` — i.e.
    ``gcloud auth application-default login`` locally, the attached service
    account on GCP, or ``GOOGLE_APPLICATION_CREDENTIALS``. Tokens are cached and
    refreshed automatically when they expire. Thread-safe so a single instance can
    back both sync and async model clients.
    """

    def __init__(self, scopes: tuple[str, ...] = (VERTEX_AUTH_SCOPE,)) -> None:
        self._scopes = list(scopes)
        self._lock = threading.Lock()
        self._credentials: Credentials | None = None

    def get_token(self) -> str:
        """Return a valid OAuth2 access token, refreshing it if necessary.

        Returns:
            A valid bearer token string.

        Raises:
            ModelAuthenticationError: If ADC is not configured or a token cannot
                be obtained.
        """
        with self._lock:
            credentials = self._ensure_credentials()
            if not credentials.valid:
                try:
                    credentials.refresh(lazy.google_auth_requests.Request())
                except Exception as exc:  # noqa: BLE001 - normalized to a canonical error below
                    raise self._auth_error(str(exc)) from exc
            token = credentials.token
        if not token:
            raise self._auth_error("The refreshed credentials did not contain an access token.")
        return token

    def _ensure_credentials(self) -> Credentials:
        if self._credentials is None:
            try:
                credentials, _ = lazy.google_auth.default(scopes=self._scopes)
            except Exception as exc:  # noqa: BLE001 - normalized to a canonical error below
                raise self._auth_error(str(exc)) from exc
            self._credentials = credentials
        return self._credentials

    @staticmethod
    def _auth_error(detail: str) -> ModelAuthenticationError:
        return ModelAuthenticationError(
            FormattedLLMErrorMessage(
                cause=f"Could not obtain Google Cloud credentials via Application Default Credentials (ADC): {detail}",
                solution=(
                    "Authenticate with `gcloud auth application-default login`, or set "
                    "GOOGLE_APPLICATION_CREDENTIALS to a service account key file, and ensure the "
                    "account has access to Vertex AI in the configured project."
                ),
            )
        )
