"""
Tests for tool_executor.py — security boundaries and per-session isolation.
"""
import json
import os
import pytest
from unittest.mock import MagicMock

import tool_executor
from tool_executor import resolve_safe_path, execute_tool


# ──────────────────────────────────────────────────────────────────────────────
# resolve_safe_path
# ──────────────────────────────────────────────────────────────────────────────

class TestResolveSafePath:
    def test_valid_path_within_base(self, tmp_backend):
        """A path that stays inside BASE resolves to an absolute path under BASE."""
        resolved = resolve_safe_path("outputs/somefile.txt")
        assert resolved.startswith(str(tmp_backend))
        assert resolved.endswith("somefile.txt")

    def test_path_traversal_etc_passwd(self, tmp_backend):
        """../../etc/passwd must raise ValueError."""
        with pytest.raises(ValueError):
            resolve_safe_path("../../etc/passwd")

    def test_path_traversal_single_dotdot(self, tmp_backend):
        """../anything must raise ValueError."""
        with pytest.raises(ValueError):
            resolve_safe_path("../outside.txt")

    @pytest.mark.parametrize("bad_path", [
        "outputs/../../../etc/shadow",
        "skills/../../secret",
    ])
    def test_path_traversal_nested(self, tmp_backend, bad_path):
        """Deeply nested traversal attempts must raise ValueError."""
        with pytest.raises(ValueError):
            resolve_safe_path(bad_path)

    def test_percent_encoded_traversal(self, tmp_backend):
        """
        %2e%2e is decoded by os.path.abspath on some platforms; the result
        must either stay inside BASE or raise ValueError.
        When abspath keeps it inside BASE it is fine; when it escapes it raises.
        """
        # os.path.abspath does NOT decode percent-encoding on its own,
        # so "%2e%2e/etc/passwd" stays literally inside BASE as a directory
        # named "%2e%2e" — either outcome (resolves safely or raises) is acceptable,
        # but the resolved path must NOT point outside BASE.
        try:
            resolved = resolve_safe_path("%2e%2e/etc/passwd")
            # If it didn't raise, it must still be inside BASE
            assert resolved.startswith(str(tmp_backend))
        except ValueError:
            pass  # Also acceptable


# ──────────────────────────────────────────────────────────────────────────────
# execute_tool — read_file
# ──────────────────────────────────────────────────────────────────────────────

class TestReadFile:
    def test_read_existing_file(self, tmp_backend):
        """Reading an existing file returns its content."""
        target = tmp_backend / "workspace" / "SOUL.md"
        result = execute_tool("read_file", {"path": "workspace/SOUL.md"})
        assert "SOUL" in result

    def test_read_nonexistent_file(self, tmp_backend):
        """Reading a missing file returns an error string."""
        result = execute_tool("read_file", {"path": "outputs/ghost.txt"})
        assert result.startswith("ERROR: File not found:")

    def test_read_path_traversal_returns_security_error(self, tmp_backend):
        """Path traversal on read_file must return a security error."""
        result = execute_tool("read_file", {"path": "../../etc/passwd"})
        assert "ERROR" in result
        assert "Security violation" in result or "security" in result.lower()

    def test_read_output_file_via_session_scoped_path(self, tmp_backend):
        """
        read_file("outputs/file.txt") should transparently find a file that
        was written to outputs/{session_id}/file.txt — matching write_file scoping.
        This is the core bug: Claude writes a file, then can't read it back.
        """
        # Write via write_file (goes to outputs/sess1/report.md)
        execute_tool("write_file", {"filename": "report.md", "content": "# Report"}, session_id="sess1")
        # Read back with the plain outputs/ path — should auto-resolve to session dir
        result = execute_tool("read_file", {"path": "outputs/report.md"}, session_id="sess1")
        assert result == "# Report"

    def test_read_output_file_wrong_session_returns_error(self, tmp_backend):
        """A file written in sess1 should not be found by sess2."""
        execute_tool("write_file", {"filename": "secret.md", "content": "data"}, session_id="sess1")
        result = execute_tool("read_file", {"path": "outputs/secret.md"}, session_id="sess2")
        assert result.startswith("ERROR: File not found:")

    def test_read_uploads_path_unchanged(self, tmp_backend):
        """uploads/ paths are not affected by session scoping."""
        f = tmp_backend / "uploads" / "policy.md"
        f.write_text("policy content")
        result = execute_tool("read_file", {"path": "uploads/policy.md"}, session_id="sess1")
        assert result == "policy content"


# ──────────────────────────────────────────────────────────────────────────────
# execute_tool — write_file
# ──────────────────────────────────────────────────────────────────────────────

class TestWriteFile:
    def test_write_plain_filename_goes_to_session_outputs(self, tmp_backend):
        """A plain filename with session_id goes to outputs/{session_id}/{filename}."""
        result = execute_tool("write_file", {"filename": "hello.txt", "content": "world"}, session_id="sess1")
        assert result.startswith("Written:")
        dest = tmp_backend / "outputs" / "sess1" / "hello.txt"
        assert dest.exists()
        assert dest.read_text() == "world"

    def test_write_skill_public_path(self, tmp_backend):
        """../skills/public/{name}/SKILL.md is routed to skills/public/."""
        result = execute_tool("write_file", {
            "filename": "../skills/public/new-skill/SKILL.md",
            "content": "# New Skill"
        }, session_id="sess1")
        assert result.startswith("Written:")
        dest = tmp_backend / "skills" / "public" / "new-skill" / "SKILL.md"
        assert dest.exists()
        assert dest.read_text() == "# New Skill"

    def test_write_skill_private_path(self, tmp_backend):
        """../skills/private/{name}/SKILL.md is routed to skills/private/."""
        result = execute_tool("write_file", {
            "filename": "../skills/private/my-priv/SKILL.md",
            "content": "# Private"
        }, session_id="sess1")
        assert result.startswith("Written:")
        dest = tmp_backend / "skills" / "private" / "my-priv" / "SKILL.md"
        assert dest.exists()

    def test_write_skills_prefix_legacy_routed_to_public(self, tmp_backend):
        """skills/ prefix (no visibility) is legacy and routes to skills/public/."""
        execute_tool("write_file", {
            "filename": "skills/legacy-skill/SKILL.md",
            "content": "# Legacy"
        })
        dest = tmp_backend / "skills" / "public" / "legacy-skill" / "SKILL.md"
        assert dest.exists()

    def test_write_path_traversal_returns_security_error(self, tmp_backend):
        """Path traversal in write_file filename returns a security error."""
        result = execute_tool("write_file", {
            "filename": "../../../../tmp/evil.txt",
            "content": "evil"
        })
        assert "ERROR" in result

    def test_write_creates_parent_directories(self, tmp_backend):
        """write_file creates any missing intermediate directories."""
        execute_tool("write_file", {
            "filename": "deep/nested/file.txt",
            "content": "deep"
        }, session_id="sess2")
        dest = tmp_backend / "outputs" / "sess2" / "deep" / "nested" / "file.txt"
        assert dest.exists()

    def test_write_without_session_goes_to_outputs_root(self, tmp_backend):
        """Without session_id output goes to outputs/ root."""
        execute_tool("write_file", {"filename": "rootfile.txt", "content": "root"})
        dest = tmp_backend / "outputs" / "rootfile.txt"
        assert dest.exists()

    def test_write_skills_public_direct_prefix(self, tmp_backend):
        """skills/public/ prefix is routed correctly."""
        execute_tool("write_file", {
            "filename": "skills/public/direct-skill/SKILL.md",
            "content": "# Direct"
        })
        dest = tmp_backend / "skills" / "public" / "direct-skill" / "SKILL.md"
        assert dest.exists()


# ──────────────────────────────────────────────────────────────────────────────
# execute_tool — run_code
# ──────────────────────────────────────────────────────────────────────────────

class TestRunCode:
    def test_run_python_hello(self, tmp_backend):
        """Running a simple Python script that prints 'hello' returns stdout and exit_code 0."""
        # Write the script first
        execute_tool("write_file", {"filename": "hello.py", "content": "print('hello')"}, session_id="run-sess")
        result = execute_tool("run_code", {"filename": "hello.py", "runtime": "python3"}, session_id="run-sess")
        data = json.loads(result)
        assert data["exit_code"] == 0
        assert "hello" in data["stdout"]

    def test_run_script_nonzero_exit(self, tmp_backend):
        """A script that exits with code 1 returns exit_code 1."""
        execute_tool("write_file", {"filename": "fail.py", "content": "import sys; sys.exit(1)"}, session_id="run-sess2")
        result = execute_tool("run_code", {"filename": "fail.py", "runtime": "python3"}, session_id="run-sess2")
        data = json.loads(result)
        assert data["exit_code"] == 1

    def test_run_nonexistent_file(self, tmp_backend):
        """Running a non-existent file returns JSON with error key."""
        result = execute_tool("run_code", {"filename": "ghost.py", "runtime": "python3"}, session_id="run-sess3")
        data = json.loads(result)
        assert "error" in data
        assert data["exit_code"] == 1

    def test_run_timeout(self, tmp_backend, monkeypatch):
        """A script that sleeps longer than timeout returns timeout error JSON."""
        import subprocess
        # Write a script that sleeps 60s
        execute_tool("write_file", {"filename": "sleep.py", "content": "import time; time.sleep(60)"}, session_id="run-timeout")
        # Monkey-patch subprocess.run to raise TimeoutExpired immediately
        original_run = subprocess.run
        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=30)
        monkeypatch.setattr(subprocess, "run", fake_run)
        result = execute_tool("run_code", {"filename": "sleep.py", "runtime": "python3"}, session_id="run-timeout")
        data = json.loads(result)
        assert "timed out" in data.get("error", "").lower() or data["exit_code"] == -1

    def test_run_code_session_scoped(self, tmp_backend):
        """Script file must be in outputs/{session_id}/ not outputs/ root."""
        sid = "scope-test"
        execute_tool("write_file", {"filename": "scoped.py", "content": "print('scoped')"}, session_id=sid)
        expected = tmp_backend / "outputs" / sid / "scoped.py"
        assert expected.exists()
        result = execute_tool("run_code", {"filename": "scoped.py", "runtime": "python3"}, session_id=sid)
        data = json.loads(result)
        assert data["exit_code"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# execute_tool — list_files
# ──────────────────────────────────────────────────────────────────────────────

class TestListFiles:
    def test_list_outputs_scoped_to_session(self, tmp_backend):
        """list_files('outputs') with session_id returns only that session's files."""
        sid = "list-sess"
        execute_tool("write_file", {"filename": "myfile.txt", "content": "x"}, session_id=sid)
        result = execute_tool("list_files", {"directory": "outputs"}, session_id=sid)
        assert "myfile.txt" in result

    def test_list_outputs_does_not_see_other_session(self, tmp_backend):
        """Session A's list_files output must not contain Session B's files."""
        execute_tool("write_file", {"filename": "a.txt", "content": "a"}, session_id="sess-a")
        execute_tool("write_file", {"filename": "b.txt", "content": "b"}, session_id="sess-b")
        result_a = execute_tool("list_files", {"directory": "outputs"}, session_id="sess-a")
        assert "a.txt" in result_a
        assert "b.txt" not in result_a

    def test_list_skills_returns_subdirs(self, tmp_backend):
        """list_files('skills') returns public/ and private/ subdirs."""
        result = execute_tool("list_files", {"directory": "skills"})
        assert "public/" in result or "private/" in result

    def test_list_nonexistent_directory_returns_empty(self, tmp_backend):
        """Listing a non-existent directory returns '(empty)', not an error."""
        result = execute_tool("list_files", {"directory": "outputs/no-such-session"})
        assert result == "(empty)"

    def test_list_path_traversal_returns_security_error(self, tmp_backend):
        """Path traversal in list_files directory must return a security error."""
        result = execute_tool("list_files", {"directory": "../../"})
        assert "ERROR" in result


# ──────────────────────────────────────────────────────────────────────────────
# Session isolation
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# execute_tool — scan_folder
# ──────────────────────────────────────────────────────────────────────────────

class TestScanFolder:
    def test_scan_uploads_returns_files(self, tmp_backend):
        """Writing a file to uploads/ and scanning returns that filename."""
        (tmp_backend / "uploads" / "testfile.txt").write_text("hello")
        result = execute_tool("scan_folder", {"directory": "uploads"})
        assert "testfile.txt" in result

    def test_scan_with_extension_filter(self, tmp_backend):
        """Extension filter returns only matching files."""
        (tmp_backend / "uploads" / "test.pdf").write_bytes(b"%PDF-1.4")
        (tmp_backend / "uploads" / "test.txt").write_text("plain text")
        result = execute_tool("scan_folder", {"directory": "uploads", "extensions": [".pdf"]})
        assert "test.pdf" in result
        assert "test.txt" not in result

    def test_scan_nonexistent_directory(self, tmp_backend):
        """Scanning a non-existent directory returns an error string."""
        result = execute_tool("scan_folder", {"directory": "nonexistent_dir"})
        assert result.startswith("ERROR:")

    def test_scan_respects_session_scope_for_outputs(self, tmp_backend):
        """scan_folder('outputs') with session_id only sees that session's files."""
        (tmp_backend / "outputs" / "sess123").mkdir(parents=True, exist_ok=True)
        (tmp_backend / "outputs" / "sess123" / "myfile.txt").write_text("data")
        result_correct = execute_tool("scan_folder", {"directory": "outputs"}, session_id="sess123")
        assert "myfile.txt" in result_correct
        result_other = execute_tool("scan_folder", {"directory": "outputs"}, session_id="other")
        assert "myfile.txt" not in result_other

    def test_scan_path_traversal_blocked(self, tmp_backend):
        """Path traversal in scan_folder must return an error string."""
        result = execute_tool("scan_folder", {"directory": "../../etc"})
        assert result.startswith("ERROR:")


class TestAnalyzeFile:
    def test_text_file_returns_content(self, tmp_backend):
        """Plain text files are read directly without API call."""
        (tmp_backend / "uploads" / "notes.txt").write_text("hello world")
        result = execute_tool(
            "analyze_file", {"path": "uploads/notes.txt"}
        )
        assert "hello world" in result

    def test_csv_file_returns_content(self, tmp_backend):
        """CSV files returned as plain text."""
        (tmp_backend / "uploads" / "data.csv").write_text("a,b,c\n1,2,3")
        result = execute_tool(
            "analyze_file", {"path": "uploads/data.csv"}
        )
        assert "a,b,c" in result

    def test_text_file_truncated_at_limit(self, tmp_backend):
        """Text files longer than text_file_limit are truncated."""
        long_content = "x" * 100_000
        (tmp_backend / "uploads" / "big.txt").write_text(long_content)
        result = execute_tool(
            "analyze_file", {"path": "uploads/big.txt"}
        )
        assert len(result) <= 51_000

    def test_nonexistent_file_returns_error(self, tmp_backend):
        """Missing file returns ERROR string."""
        result = execute_tool(
            "analyze_file", {"path": "uploads/ghost.pdf"}
        )
        assert result.startswith("ERROR: File not found:")

    def test_unsupported_extension_returns_message(self, tmp_backend):
        """Unsupported file type returns helpful message."""
        (tmp_backend / "uploads" / "file.docx").write_bytes(
            b"PK fake docx"
        )
        result = execute_tool(
            "analyze_file", {"path": "uploads/file.docx"}
        )
        assert "Unsupported file type" in result
        assert ".docx" in result

    def test_path_traversal_blocked(self, tmp_backend):
        """Path traversal returns security error."""
        result = execute_tool(
            "analyze_file", {"path": "../../etc/passwd"}
        )
        assert "ERROR" in result

    def test_pdf_calls_anthropic_api(self, tmp_backend):
        """PDF files trigger an Anthropic API call."""
        (tmp_backend / "uploads" / "report.pdf").write_bytes(
            b"%PDF-1.4 fake"
        )
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="This is a financial report.")
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = execute_tool(
            "analyze_file",
            {"path": "uploads/report.pdf"},
            anthropic_client=mock_client
        )
        assert result == "This is a financial report."
        assert mock_client.messages.create.called

    def test_png_calls_anthropic_api(self, tmp_backend):
        """PNG image files trigger an Anthropic API call."""
        (tmp_backend / "uploads" / "chart.png").write_bytes(
            b"\x89PNG fake"
        )
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="Bar chart showing Q3 revenue.")
        ]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = execute_tool(
            "analyze_file",
            {"path": "uploads/chart.png"},
            anthropic_client=mock_client
        )
        assert result == "Bar chart showing Q3 revenue."

    def test_no_anthropic_client_for_pdf_returns_error(self, tmp_backend):
        """PDF without anthropic_client returns clear error."""
        (tmp_backend / "uploads" / "report.pdf").write_bytes(
            b"%PDF-1.4 fake"
        )
        result = execute_tool(
            "analyze_file",
            {"path": "uploads/report.pdf"},
            anthropic_client=None
        )
        assert "ERROR" in result


class TestSpawnAgent:

    def test_skill_not_found_returns_error(self, tmp_backend):
        """spawn_agent with nonexistent skill returns ERROR."""
        mock_client = MagicMock()
        result = execute_tool(
            "spawn_agent",
            {"task": "do something", "skill_name": "nonexistent-skill"},
            anthropic_client=mock_client
        )
        assert result.startswith("ERROR: Skill not found:")

    def test_no_client_returns_error(self, tmp_backend):
        """spawn_agent without anthropic_client returns ERROR."""
        result = execute_tool(
            "spawn_agent",
            {"task": "do something", "skill_name": "test-skill"},
            anthropic_client=None
        )
        assert result.startswith("ERROR:")

    def test_end_turn_returns_text(self, tmp_backend):
        """spawn_agent returns text when subagent ends cleanly."""
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Subagent result here."

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = execute_tool(
            "spawn_agent",
            {
                "task": "summarise the test skill",
                "skill_name": "test-skill",
                "input_data": "some input"
            },
            session_id="test-sess",
            anthropic_client=mock_client
        )
        assert result == "Subagent result here."
        assert mock_client.messages.create.called

    def test_tool_use_loop_then_end_turn(self, tmp_backend):
        """spawn_agent handles one tool call then end_turn correctly."""
        # First response: tool_use
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "tu_001"
        tool_block.name = "read_file"
        tool_block.input = {"path": "workspace/SOUL.md"}

        first_response = MagicMock()
        first_response.stop_reason = "tool_use"
        first_response.content = [tool_block]

        # Second response: end_turn with text
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Final answer from subagent."

        second_response = MagicMock()
        second_response.stop_reason = "end_turn"
        second_response.content = [text_block]

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            first_response,
            second_response,
        ]

        result = execute_tool(
            "spawn_agent",
            {
                "task": "read soul and summarise",
                "skill_name": "test-skill",
            },
            session_id="test-sess",
            anthropic_client=mock_client
        )
        assert result == "Final answer from subagent."
        assert mock_client.messages.create.call_count == 2

    def test_uses_custom_model(self, tmp_backend):
        """spawn_agent passes the specified model to API call."""
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "done"

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        execute_tool(
            "spawn_agent",
            {
                "task": "summarise",
                "skill_name": "test-skill",
                "model": "claude-haiku-4-5-20251001"
            },
            anthropic_client=mock_client
        )
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-haiku-4-5-20251001"

    def test_spawn_agent_not_in_subagent_tools(self, tmp_backend):
        """spawn_agent tool is not available to subagents (no recursion)."""
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "done"

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        execute_tool(
            "spawn_agent",
            {"task": "do task", "skill_name": "test-skill"},
            anthropic_client=mock_client
        )
        # Check that the tools passed to the subagent do not include spawn_agent
        call_kwargs = mock_client.messages.create.call_args
        tool_names = {t["name"] for t in call_kwargs.kwargs["tools"]}
        assert "spawn_agent" not in tool_names

    def test_path_in_public_then_private(self, tmp_backend):
        """spawn_agent finds skill in private/ if not in public/."""
        priv_dir = tmp_backend / "skills" / "private" / "priv-skill"
        priv_dir.mkdir(parents=True, exist_ok=True)
        (priv_dir / "SKILL.md").write_text(
            "---\nname: priv-skill\ndescription: x.\ncategory: utility\n---\n# x"
        )

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "private skill result"

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = execute_tool(
            "spawn_agent",
            {"task": "use private skill", "skill_name": "priv-skill"},
            anthropic_client=mock_client
        )
        assert result == "private skill result"


class TestSessionIsolation:
    def test_session_a_file_not_visible_from_session_b(self, tmp_backend):
        """File written in session A is not returned when listing session B's outputs."""
        execute_tool("write_file", {"filename": "exclusive.txt", "content": "only-a"}, session_id="iso-a")
        listing_b = execute_tool("list_files", {"directory": "outputs"}, session_id="iso-b")
        assert "exclusive.txt" not in listing_b

    def test_write_without_session_goes_to_outputs_root(self, tmp_backend):
        """Without session_id, file is written to outputs/ root."""
        execute_tool("write_file", {"filename": "nosess.txt", "content": "ns"})
        dest = tmp_backend / "outputs" / "nosess.txt"
        assert dest.exists()
