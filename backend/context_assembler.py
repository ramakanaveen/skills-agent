import os
from datetime import datetime
from typing import List, Dict

# Import tool_executor to ensure all built-in tools are registered
# into the registry before build_tools() is called.
import tool_executor as _tool_executor  # noqa: F401
from tool_registry import registry


def build_system_prompt(skills: List[Dict], uploaded_files: List[Dict] = None) -> str:
    if uploaded_files is None:
        uploaded_files = []

    backend_dir = os.path.dirname(__file__)

    soul = open(os.path.join(backend_dir, "workspace", "SOUL.md"), encoding="utf-8").read()
    agents = open(os.path.join(backend_dir, "workspace", "AGENTS.md"), encoding="utf-8").read()
    tools = open(os.path.join(backend_dir, "workspace", "TOOLS.md"), encoding="utf-8").read()

    if skills:
        skills_block = "\n".join([
            f"- **{s['name']}** [{s.get('visibility', 'public')}]: {s['description']}\n"
            f"  Read with: read_file(\"{s['skill_md_path']}\")"
            for s in skills
        ])
        skills_block += (
            "\n\n## Skill Visibility Rules\n"
            "When creating a new skill, ALWAYS ask the user first:\n"
            "  'Should this skill be **public** (shared with everyone, committed to git)\n"
            "   or **private** (only visible to you, never committed)?\n'\n"
            "Then write to the correct path:\n"
            "  Public skill:  write_file(\"../skills/public/{name}/SKILL.md\", content)\n"
            "  Private skill: write_file(\"../skills/private/{name}/SKILL.md\", content)"
        )
    else:
        skills_block = "(no skills available yet)"

    files_block = ""
    if uploaded_files:
        files_block = "## User-Uploaded Files (read with read_file)\n"
        files_block += "\n".join([
            f"- {f['name']}: read_file(\"uploads/{f['name']}\")"
            for f in uploaded_files
        ])

    return f"""{soul}

{agents}

{tools}

## Available Skills
{skills_block}

{files_block}

Current time: {datetime.utcnow().isoformat()}Z
"""


def build_tools() -> list:
    """Return all registered tool schemas. Built-in tools come from tool_executor;
    MCP tools are added by mcp_manager at startup — both show up here automatically."""
    return registry.schemas()


