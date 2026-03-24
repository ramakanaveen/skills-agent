"""
Configuration loader for Skills Agent backend.

Load order (highest priority last wins):
  1. config.yaml defaults
  2. Environment variables  SKILLS_AGENT_<SECTION>_<KEY>

Usage:
    from config import cfg

    model = cfg.model_name          # "claude-sonnet-4-20250514"
    max_tok = cfg.max_tokens        # 8096
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

import yaml

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def _env(key: str, default):
    """Read SKILLS_AGENT_<KEY> env var; cast to the same type as default."""
    val = os.environ.get(f"SKILLS_AGENT_{key.upper()}")
    if val is None:
        return default
    if isinstance(default, bool):
        return val.lower() in ("1", "true", "yes")
    if isinstance(default, int):
        return int(val)
    if isinstance(default, float):
        return float(val)
    if isinstance(default, list):
        return [v.strip() for v in val.split(",")]
    return val


def _load_yaml() -> dict:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


@dataclass
class Config:
    # provider section
    provider: str = "anthropic"          # "anthropic" or "vertex"

    # vertex section
    vertex_project_id: str = ""
    vertex_region: str = "us-east5"
    vertex_base_url: str = ""

    # model section
    model_name: str = "claude-sonnet-4-20250514"
    model_vertex_name: str = "claude-sonnet-4@20250514"
    max_tokens: int = 8096

    # agent section
    max_iterations: int = 20
    context_budget: int = 150_000
    context_trim_keep: int = 16
    max_nudges: int = 1

    # tools section
    result_preview_chars: int = 500
    run_code_stdout_limit: int = 3000
    run_code_stderr_limit: int = 2000
    run_code_timeout: int = 30
    text_file_limit: int = 50_000

    # server section
    cors_origins: List[str] = field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )


def _build() -> Config:
    raw = _load_yaml()
    model = raw.get("model", {})
    agent = raw.get("agent", {})
    tools = raw.get("tools", {})
    server = raw.get("server", {})
    vertex = raw.get("vertex", {})

    return Config(
        provider=_env("PROVIDER", raw.get("provider", Config.provider)),
        vertex_project_id=_env("VERTEX_PROJECT_ID", vertex.get("project_id", Config.vertex_project_id)),
        vertex_region=_env("VERTEX_REGION", vertex.get("region", Config.vertex_region)),
        vertex_base_url=_env("VERTEX_BASE_URL", vertex.get("base_url", Config.vertex_base_url)),
        model_name=_env("MODEL_NAME", model.get("name", Config.model_name)),
        model_vertex_name=_env("MODEL_VERTEX_NAME", model.get("vertex_name", Config.model_vertex_name)),
        max_tokens=_env("MAX_TOKENS", model.get("max_tokens", Config.max_tokens)),
        max_iterations=_env("AGENT_MAX_ITERATIONS", agent.get("max_iterations", Config.max_iterations)),
        context_budget=_env("AGENT_CONTEXT_BUDGET", agent.get("context_budget", Config.context_budget)),
        context_trim_keep=_env("AGENT_CONTEXT_TRIM_KEEP", agent.get("context_trim_keep", Config.context_trim_keep)),
        max_nudges=_env("AGENT_MAX_NUDGES", agent.get("max_nudges", Config.max_nudges)),
        result_preview_chars=_env("TOOLS_RESULT_PREVIEW_CHARS", tools.get("result_preview_chars", Config.result_preview_chars)),
        run_code_stdout_limit=_env("TOOLS_RUN_CODE_STDOUT_LIMIT", tools.get("run_code_stdout_limit", Config.run_code_stdout_limit)),
        run_code_stderr_limit=_env("TOOLS_RUN_CODE_STDERR_LIMIT", tools.get("run_code_stderr_limit", Config.run_code_stderr_limit)),
        run_code_timeout=_env("TOOLS_RUN_CODE_TIMEOUT", tools.get("run_code_timeout", Config.run_code_timeout)),
        text_file_limit=_env(
            "TOOLS_TEXT_FILE_LIMIT",
            tools.get("text_file_limit", Config.text_file_limit)
        ),
        cors_origins=_env("SERVER_CORS_ORIGINS", server.get("cors_origins", ["http://localhost:5173", "http://127.0.0.1:5173"])),
    )


cfg = _build()
