"""
Shared fixtures for the skills-agent backend test suite.

The ``tmp_backend`` fixture creates a temporary directory that mirrors the
real backend/ layout and patches all module-level path constants so no test
ever touches the real backend files.
"""
import os
import pytest


SAMPLE_SKILL_MD = """\
---
name: test-skill
category: utility
description: A test skill for unit tests.
---
# Test Skill body
"""


@pytest.fixture()
def tmp_backend(tmp_path, monkeypatch):
    """
    Create a temp directory tree that mirrors backend/ and redirect every
    module-level constant to it so tests are fully isolated.

    Directory layout created:
        tmp_path/
          skills/public/test-skill/SKILL.md
          skills/private/
          outputs/
          uploads/
          sessions/
          workspace/SOUL.md
          workspace/AGENTS.md
          workspace/TOOLS.md
    """
    # ── directory skeleton ──────────────────────────────────────────────────
    for sub in [
        "skills/public/test-skill",
        "skills/private",
        "outputs",
        "uploads",
        "sessions",
        "workspace",
    ]:
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)

    # ── workspace files ─────────────────────────────────────────────────────
    (tmp_path / "workspace" / "SOUL.md").write_text("# SOUL\nYou are a helpful agent.")
    (tmp_path / "workspace" / "AGENTS.md").write_text("# AGENTS\nAgent instructions here.")
    (tmp_path / "workspace" / "TOOLS.md").write_text("# TOOLS\nTool usage instructions.")

    # ── sample public skill ──────────────────────────────────────────────────
    (tmp_path / "skills" / "public" / "test-skill" / "SKILL.md").write_text(SAMPLE_SKILL_MD)

    # ── patch tool_executor ──────────────────────────────────────────────────
    import tool_executor
    monkeypatch.setattr(tool_executor, "BASE", str(tmp_path))

    # ── patch session module ─────────────────────────────────────────────────
    import session as session_module
    monkeypatch.setattr(session_module, "SESSIONS_DIR", str(tmp_path / "sessions"))

    # ── patch skill_loader dirs ──────────────────────────────────────────────
    import skill_loader
    monkeypatch.setattr(skill_loader, "SKILLS_DIR", str(tmp_path / "skills"))
    monkeypatch.setattr(skill_loader, "PUBLIC_DIR", str(tmp_path / "skills" / "public"))
    monkeypatch.setattr(skill_loader, "PRIVATE_DIR", str(tmp_path / "skills" / "private"))

    # ── patch context_assembler to use tmp workspace ─────────────────────────
    import context_assembler
    monkeypatch.setattr(context_assembler, "__file__", str(tmp_path / "context_assembler.py"))

    return tmp_path
