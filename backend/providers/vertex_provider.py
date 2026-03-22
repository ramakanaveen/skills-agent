"""
Vertex AI provider for Skills Agent.

Usage:
    from providers.vertex_provider import VertexProvider
    provider = VertexProvider(cfg)

    # At the start of each agent run:
    client = provider.get_client()
    model  = provider.model_name

Customisation:
    Override _get_token() with your internal auth logic (e.g. r2d2).
    The base implementation returns None, which tells AnthropicVertex
    to fall back to Google Application Default Credentials (ADC).

    If _get_token() returns a token string, the provider will rebuild
    the client whenever the token changes — so token refresh is handled
    automatically as long as _get_token() returns the current valid token.
"""

import anthropic
from config import Config


class VertexProvider:
    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._client = None
        self._last_token: str | None = None

    # ------------------------------------------------------------------
    # Auth hook — replace with your r2d2 / internal token logic
    # ------------------------------------------------------------------
    def _get_token(self) -> str | None:
        """
        Return a valid Vertex AI access token string, or None to use ADC.

        Replace this method with your internal token fetch + refresh logic.
        This is called on every get_client() invocation; if the returned
        token differs from the last one, the client is rebuilt automatically.
        """
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _build_client(self, token: str | None) -> anthropic.AnthropicVertex:
        kwargs = dict(
            project_id=self._cfg.vertex_project_id,
            region=self._cfg.vertex_region,
        )
        if self._cfg.vertex_base_url:
            kwargs["base_url"] = self._cfg.vertex_base_url
        if token:
            kwargs["access_token"] = token
        return anthropic.AnthropicVertex(**kwargs)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def get_client(self) -> anthropic.AnthropicVertex:
        """
        Return a ready-to-use AnthropicVertex client.

        Rebuilds the client if the token has changed since the last call
        (handles internal token refresh transparently).
        """
        token = self._get_token()
        if self._client is None or token != self._last_token:
            self._client = self._build_client(token)
            self._last_token = token
        return self._client

    @property
    def model_name(self) -> str:
        return self._cfg.model_vertex_name
