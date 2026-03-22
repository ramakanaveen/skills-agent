"""
Tests for session.py — save/load transcript, session listing.
"""
import json
import os
import time
import pytest

import session as session_module
from session import save_turn, load_history, read_transcript, list_sessions


class TestSaveTurn:
    def test_save_user_turn(self, tmp_backend):
        """save_turn with role='user' writes a JSONL line with correct fields."""
        save_turn("s1", "user", content="Hello agent")
        path = tmp_backend / "sessions" / "s1.jsonl"
        assert path.exists()
        record = json.loads(path.read_text().strip())
        assert record["role"] == "user"
        assert record["content"] == "Hello agent"
        assert "ts" in record

    def test_save_assistant_turn(self, tmp_backend):
        """save_turn with role='assistant' records correctly."""
        save_turn("s2", "assistant", content="Hi there")
        path = tmp_backend / "sessions" / "s2.jsonl"
        record = json.loads(path.read_text().strip())
        assert record["role"] == "assistant"
        assert record["content"] == "Hi there"

    def test_save_tool_turn_includes_tool_fields(self, tmp_backend):
        """Tool turns include tool_name, tool_input, tool_result."""
        save_turn(
            "s3",
            "tool",
            content="file contents here",
            tool_name="read_file",
            tool_input={"path": "skills/public/test-skill/SKILL.md"},
            tool_result="# Test Skill body",
        )
        path = tmp_backend / "sessions" / "s3.jsonl"
        record = json.loads(path.read_text().strip())
        assert record["tool_name"] == "read_file"
        assert record["tool_input"]["path"] == "skills/public/test-skill/SKILL.md"
        assert record["tool_result"] == "# Test Skill body"

    def test_content_truncated_at_2000_chars(self, tmp_backend):
        """Content longer than 2000 characters is truncated to 2000."""
        long_content = "x" * 5000
        save_turn("s4", "user", content=long_content)
        path = tmp_backend / "sessions" / "s4.jsonl"
        record = json.loads(path.read_text().strip())
        assert len(record["content"]) == 2000

    def test_creates_sessions_dir_if_not_exists(self, tmp_backend, monkeypatch):
        """save_turn creates the sessions directory if it is missing."""
        new_sessions = tmp_backend / "sessions_new"
        monkeypatch.setattr(session_module, "SESSIONS_DIR", str(new_sessions))
        save_turn("sx", "user", content="test")
        assert (new_sessions / "sx.jsonl").exists()

    def test_multiple_turns_appended(self, tmp_backend):
        """Multiple save_turn calls append separate lines to the same file."""
        save_turn("smulti", "user", content="msg1")
        save_turn("smulti", "assistant", content="msg2")
        path = tmp_backend / "sessions" / "smulti.jsonl"
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 2


class TestLoadHistory:
    def test_empty_file_returns_empty_list(self, tmp_backend):
        """load_history returns [] for a session file with no content."""
        (tmp_backend / "sessions" / "empty.jsonl").write_text("")
        assert load_history("empty") == []

    def test_nonexistent_session_returns_empty_list(self, tmp_backend):
        """load_history returns [] when the session file doesn't exist."""
        assert load_history("nonexistent-xyz") == []

    def test_returns_only_user_and_assistant_turns(self, tmp_backend):
        """Tool turns are excluded from load_history output."""
        save_turn("hist1", "user", content="question")
        save_turn("hist1", "tool", content="result", tool_name="read_file",
                  tool_input={"path": "x"}, tool_result="y")
        save_turn("hist1", "assistant", content="answer")
        messages = load_history("hist1")
        roles = [m["role"] for m in messages]
        assert "tool" not in roles
        assert roles == ["user", "assistant"]

    def test_respects_max_turns_limit(self, tmp_backend):
        """load_history returns at most max_turns messages."""
        for i in range(10):
            save_turn("hist2", "user", content=f"message {i}")
        messages = load_history("hist2", max_turns=4)
        assert len(messages) <= 4

    def test_reconstructs_anthropic_message_format(self, tmp_backend):
        """load_history returns dicts with 'role' and 'content' keys."""
        save_turn("hist3", "user", content="hello")
        save_turn("hist3", "assistant", content="world")
        messages = load_history("hist3")
        assert all("role" in m and "content" in m for m in messages)
        assert messages[0] == {"role": "user", "content": "hello"}
        assert messages[1] == {"role": "assistant", "content": "world"}


class TestReadTranscript:
    def test_returns_all_records_including_tool_turns(self, tmp_backend):
        """read_transcript returns user, assistant, and tool records."""
        save_turn("tr1", "user", content="ask")
        save_turn("tr1", "tool", content="res", tool_name="read_file",
                  tool_input={"path": "x"}, tool_result="data")
        save_turn("tr1", "assistant", content="done")
        records = read_transcript("tr1")
        assert len(records) == 3
        roles = [r["role"] for r in records]
        assert "tool" in roles

    def test_returns_empty_list_for_nonexistent_session(self, tmp_backend):
        """read_transcript returns [] when the session file doesn't exist."""
        assert read_transcript("does-not-exist") == []


class TestListSessions:
    def test_returns_list_with_expected_fields(self, tmp_backend):
        """list_sessions returns dicts with the required metadata keys."""
        save_turn("ls1", "user", content="hi")
        sessions = list_sessions()
        assert len(sessions) >= 1
        s = next(x for x in sessions if x["session_id"] == "ls1")
        for key in ["session_id", "created_at", "updated_at", "preview", "user_turns", "assistant_turns"]:
            assert key in s

    def test_preview_is_first_user_message(self, tmp_backend):
        """preview contains the first user message (up to 120 chars)."""
        save_turn("ls2", "user", content="First user message")
        save_turn("ls2", "assistant", content="Response")
        sessions = list_sessions()
        s = next(x for x in sessions if x["session_id"] == "ls2")
        assert s["preview"] == "First user message"

    def test_user_and_assistant_turns_counted_correctly(self, tmp_backend):
        """user_turns and assistant_turns are counted separately."""
        save_turn("ls3", "user", content="u1")
        save_turn("ls3", "user", content="u2")
        save_turn("ls3", "assistant", content="a1")
        sessions = list_sessions()
        s = next(x for x in sessions if x["session_id"] == "ls3")
        assert s["user_turns"] == 2
        assert s["assistant_turns"] == 1

    def test_sorted_by_updated_at_descending(self, tmp_backend):
        """list_sessions returns sessions sorted by updated_at descending."""
        save_turn("older-sess", "user", content="old")
        time.sleep(0.01)
        save_turn("newer-sess", "user", content="new")
        sessions = list_sessions()
        ids = [s["session_id"] for s in sessions]
        assert ids.index("newer-sess") < ids.index("older-sess")

    def test_empty_sessions_dir_returns_empty_list(self, tmp_backend):
        """list_sessions returns [] when no .jsonl files exist."""
        # Remove any sessions created by other tests using isolated session IDs
        sessions_dir = tmp_backend / "sessions"
        for f in sessions_dir.iterdir():
            f.unlink()
        result = list_sessions()
        assert result == []
