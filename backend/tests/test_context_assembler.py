"""
Tests for context_assembler.py — system prompt and tools list construction.
"""
import os
import pytest
from unittest.mock import patch

import context_assembler
from context_assembler import build_system_prompt, build_tools


def make_tmp_workspace(tmp_path):
    """Create workspace files in tmp_path and return the path."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "SOUL.md").write_text("# SOUL\nYou are a helpful agent.")
    (ws / "AGENTS.md").write_text("# AGENTS\nAgent instructions here.")
    (ws / "TOOLS.md").write_text("# TOOLS\nTool usage instructions.")
    return tmp_path


@pytest.fixture()
def workspace_dir(tmp_path):
    """Return a tmp dir with workspace/ files and patch context_assembler.__file__."""
    make_tmp_workspace(tmp_path)
    with patch.object(context_assembler, "__file__", str(tmp_path / "context_assembler.py")):
        yield tmp_path


SAMPLE_SKILLS = [
    {
        "name": "test-skill",
        "description": "A test skill for unit tests.",
        "skill_md_path": "skills/public/test-skill/SKILL.md",
        "visibility": "public",
        "category": "utility",
    },
    {
        "name": "priv-skill",
        "description": "A private skill.",
        "skill_md_path": "skills/private/priv-skill/SKILL.md",
        "visibility": "private",
        "category": "writing",
    },
]


class TestBuildSystemPrompt:
    def test_contains_soul_content(self, workspace_dir):
        """System prompt includes content from SOUL.md."""
        prompt = build_system_prompt(SAMPLE_SKILLS)
        assert "You are a helpful agent" in prompt

    def test_contains_agents_content(self, workspace_dir):
        """System prompt includes content from AGENTS.md."""
        prompt = build_system_prompt(SAMPLE_SKILLS)
        assert "Agent instructions here" in prompt

    def test_contains_tools_content(self, workspace_dir):
        """System prompt includes content from TOOLS.md."""
        prompt = build_system_prompt(SAMPLE_SKILLS)
        assert "Tool usage instructions" in prompt

    def test_contains_skill_name_and_description(self, workspace_dir):
        """System prompt includes each skill's name and description."""
        prompt = build_system_prompt(SAMPLE_SKILLS)
        assert "test-skill" in prompt
        assert "A test skill for unit tests." in prompt

    def test_contains_visibility_tag(self, workspace_dir):
        """System prompt contains [public] and [private] visibility tags."""
        prompt = build_system_prompt(SAMPLE_SKILLS)
        assert "[public]" in prompt
        assert "[private]" in prompt

    def test_contains_read_file_path(self, workspace_dir):
        """System prompt contains the read_file call with the skill's path."""
        prompt = build_system_prompt(SAMPLE_SKILLS)
        assert 'read_file("skills/public/test-skill/SKILL.md")' in prompt

    def test_with_uploaded_files_contains_filenames(self, workspace_dir):
        """When uploaded_files is provided, their names appear in the prompt."""
        uploaded = [{"name": "policy.pdf"}, {"name": "notes.txt"}]
        prompt = build_system_prompt(SAMPLE_SKILLS, uploaded_files=uploaded)
        assert "policy.pdf" in prompt
        assert "notes.txt" in prompt

    def test_without_uploaded_files_no_upload_section(self, workspace_dir):
        """Without uploaded files, no uploaded-files section is present."""
        prompt = build_system_prompt(SAMPLE_SKILLS, uploaded_files=[])
        assert "User-Uploaded Files" not in prompt

    def test_contains_current_time(self, workspace_dir):
        """System prompt contains a 'Current time:' timestamp."""
        prompt = build_system_prompt(SAMPLE_SKILLS)
        assert "Current time:" in prompt

    def test_no_skills_shows_placeholder(self, workspace_dir):
        """When skills list is empty, the prompt shows a placeholder."""
        prompt = build_system_prompt([])
        assert "no skills available yet" in prompt


class TestBuildTools:
    def test_returns_four_tools(self):
        """build_tools() returns exactly 4 tool definitions."""
        tools = build_tools()
        assert len(tools) == 4

    def test_tool_names(self):
        """All expected tool names are present."""
        tools = build_tools()
        names = {t["name"] for t in tools}
        assert names == {"read_file", "write_file", "run_code", "list_files"}

    def test_each_tool_has_required_keys(self):
        """Each tool dict has name, description, and input_schema."""
        for tool in build_tools():
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool

    def test_run_code_has_runtime_enum(self):
        """run_code tool has a 'runtime' property with enum ['node', 'python3']."""
        tools = build_tools()
        run_code = next(t for t in tools if t["name"] == "run_code")
        runtime_prop = run_code["input_schema"]["properties"]["runtime"]
        assert "enum" in runtime_prop
        assert set(runtime_prop["enum"]) == {"node", "python3"}

    def test_all_tools_have_required_fields_in_schema(self):
        """Every tool's input_schema includes a 'required' list."""
        for tool in build_tools():
            assert "required" in tool["input_schema"]
            assert isinstance(tool["input_schema"]["required"], list)

    def test_read_file_requires_path(self):
        """read_file input_schema requires 'path'."""
        tools = build_tools()
        rf = next(t for t in tools if t["name"] == "read_file")
        assert "path" in rf["input_schema"]["required"]

    def test_write_file_requires_filename_and_content(self):
        """write_file input_schema requires 'filename' and 'content'."""
        tools = build_tools()
        wf = next(t for t in tools if t["name"] == "write_file")
        assert "filename" in wf["input_schema"]["required"]
        assert "content" in wf["input_schema"]["required"]

    def test_list_files_requires_directory(self):
        """list_files input_schema requires 'directory'."""
        tools = build_tools()
        lf = next(t for t in tools if t["name"] == "list_files")
        assert "directory" in lf["input_schema"]["required"]
