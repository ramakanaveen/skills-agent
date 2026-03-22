"""
Tests for tool_executor.py — security boundaries and per-session isolation.
"""
import json
import os
import pytest

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
