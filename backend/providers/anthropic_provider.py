"""
Anthropic direct API provider for Skills Agent.

Usage:
    from providers.anthropic_provider import AnthropicProvider
    provider = AnthropicProvider(cfg)

    client = provider.get_client()
    model  = provider.model_name

Auth:
    Reads ANTHROPIC_API_KEY from the environment (set in .env).
    All other config (model name, token limits) comes from config.yaml.
"""

import os

import anthropic
from config import Config


class AnthropicProvider:
    def __init__(self, cfg: Config):
        self._model_name = cfg.model_name
        self._client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )

    def get_client(self) -> anthropic.Anthropic:
        """Return the Anthropic direct API client."""
        return self._client

    @property
    def model_name(self) -> str:
        return self._model_name
