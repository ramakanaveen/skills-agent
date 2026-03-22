"""
Integration tests for main.py — FastAPI endpoints.

Real Anthropic API calls are mocked so no network traffic occurs.
All file I/O uses temporary directories via the tmp_backend fixture.
"""
import io
import json
import os
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


# ── helpers to build mock Anthropic response objects ─────────────────────────

def _make_end_turn_response(text="Done."):
    """Return a minimal mock of anthropic.types.Message with stop_reason=end_turn."""
    block = MagicMock()
    block.type = "text"
    block.text = text

    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_backend, monkeypatch):
    """
    Return a FastAPI TestClient backed by tmp dirs.

    - Patches UPLOADS_DIR, OUTPUTS_DIR, SESSIONS_DIR in main
    - Patches anthropic_client.messages.create to avoid real API calls
    - Sets a dummy ANTHROPIC_API_KEY env var
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    import main
    monkeypatch.setattr(main, "UPLOADS_DIR", str(tmp_backend / "uploads"))
    monkeypatch.setattr(main, "OUTPUTS_DIR", str(tmp_backend / "outputs"))
    monkeypatch.setattr(main, "SESSIONS_DIR", str(tmp_backend / "sessions"))

    # Ensure directories exist
    (tmp_backend / "uploads").mkdir(exist_ok=True)
    (tmp_backend / "outputs").mkdir(exist_ok=True)
    (tmp_backend / "sessions").mkdir(exist_ok=True)

    # Patch the anthropic client via the provider
    mock_messages = MagicMock()
    mock_messages.create.return_value = _make_end_turn_response()
    mock_client = MagicMock()
    mock_client.messages = mock_messages
    monkeypatch.setattr(main._provider, "get_client", lambda: mock_client)

    return TestClient(main.app, raise_server_exceptions=True)


# ── GET /api/health ───────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200_with_ok_status(self, client):
        """GET /api/health returns 200 and body with status='ok'."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ── GET /api/skills ───────────────────────────────────────────────────────────

class TestGetSkills:
    def test_returns_200_list(self, client):
        """GET /api/skills returns 200 with a list."""
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_skill_has_expected_fields(self, client):
        """Each skill object has the required metadata fields."""
        resp = client.get("/api/skills")
        for skill in resp.json():
            for field in ["name", "description", "visibility", "category", "skill_md_path"]:
                assert field in skill, f"Missing field '{field}' in skill {skill}"


# ── GET /api/sessions ─────────────────────────────────────────────────────────

class TestGetSessions:
    def test_returns_200_list(self, client):
        """GET /api/sessions returns 200 with a list."""
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── POST /api/upload ──────────────────────────────────────────────────────────

class TestUpload:
    def test_upload_text_file_returns_200(self, client, tmp_backend):
        """Uploading a text file returns 200 with filename and path."""
        resp = client.post(
            "/api/upload",
            files={"file": ("hello.txt", io.BytesIO(b"hello world"), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "filename" in data
        assert "path" in data

    def test_uploaded_file_exists_on_disk(self, client, tmp_backend):
        """After upload the file is present in the uploads directory."""
        client.post(
            "/api/upload",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
        )
        uploads = list((tmp_backend / "uploads").iterdir())
        assert len(uploads) >= 1

    def test_malicious_filename_is_sanitised(self, client, tmp_backend):
        """A filename with path traversal is sanitised to a safe name."""
        resp = client.post(
            "/api/upload",
            files={"file": ("../../evil.txt", io.BytesIO(b"evil"), "text/plain")},
        )
        assert resp.status_code == 200
        safe_name = resp.json()["filename"]
        # Must not contain path separators or dotdot sequences
        assert ".." not in safe_name
        assert "/" not in safe_name
        assert "\\" not in safe_name


# ── GET /api/download/{session_id}/{filename} ─────────────────────────────────

class TestDownload:
    def test_existing_file_returns_200(self, client, tmp_backend):
        """Downloading an existing output file returns 200 and the file content."""
        session_id = "dl-test"
        out_dir = tmp_backend / "outputs" / session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.txt").write_text("the result")
        resp = client.get(f"/api/download/{session_id}/result.txt")
        assert resp.status_code == 200
        assert b"the result" in resp.content

    def test_nonexistent_file_returns_404(self, client):
        """Downloading a file that doesn't exist returns 404."""
        resp = client.get("/api/download/no-such-session/no-such-file.txt")
        assert resp.status_code == 404


# ── GET /api/session/{session_id} ─────────────────────────────────────────────

class TestGetSession:
    def test_nonexistent_session_returns_empty_list(self, client):
        """A session that doesn't exist returns 200 with an empty list."""
        resp = client.get("/api/session/nonexistent-session-xyz")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_existing_session_returns_transcript(self, client, tmp_backend):
        """An existing session returns its transcript records."""
        import session as session_module
        save = session_module.save_turn
        save("existing-sess", "user", content="hello")
        save("existing-sess", "assistant", content="world")
        resp = client.get("/api/session/existing-sess")
        assert resp.status_code == 200
        records = resp.json()
        assert len(records) == 2


# ── GET /api/skill-stats ──────────────────────────────────────────────────────

class TestSkillStats:
    def test_returns_200_dict(self, client):
        """GET /api/skill-stats returns 200 with a dict."""
        resp = client.get("/api/skill-stats")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_counts_skill_reads_from_sessions(self, client, tmp_backend, monkeypatch):
        """skill-stats counts read_file calls that reference SKILL.md paths."""
        import main
        sessions_dir = tmp_backend / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        # Patch SESSIONS_DIR in main to use our tmp dir
        monkeypatch.setattr(main, "SESSIONS_DIR", str(sessions_dir))

        # Write a session with a tool call to read a SKILL.md
        record = json.dumps({
            "ts": "2024-01-01T00:00:00Z",
            "role": "tool",
            "content": "skill body",
            "tool_name": "read_file",
            "tool_input": {"path": "skills/public/test-skill/SKILL.md"},
            "tool_result": "skill body",
        })
        (sessions_dir / "stats-sess.jsonl").write_text(record + "\n")

        resp = client.get("/api/skill-stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert "test-skill" in stats
        assert stats["test-skill"] >= 1


# ── POST /api/run ─────────────────────────────────────────────────────────────

class TestRunAgent:
    def _parse_sse(self, text: str):
        """Parse SSE response text into a list of data dicts."""
        events = []
        for line in text.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        return events

    def test_returns_event_stream_content_type(self, client):
        """POST /api/run responds with text/event-stream content-type."""
        resp = client.post("/api/run", json={"task": "do something"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_first_event_is_start_with_session_id(self, client):
        """The first SSE event has stage='start' and a session_id."""
        resp = client.post("/api/run", json={"task": "hello"})
        events = self._parse_sse(resp.text)
        assert events[0]["stage"] == "start"
        assert "session_id" in events[0]
        assert events[0]["session_id"]  # non-empty

    def test_last_event_is_complete(self, client):
        """The final SSE event has stage='complete'."""
        resp = client.post("/api/run", json={"task": "do something"})
        events = self._parse_sse(resp.text)
        assert events[-1]["stage"] == "complete"

    def test_new_session_id_generated_when_none_provided(self, client):
        """When session_id is None, a new UUID is generated and returned."""
        resp = client.post("/api/run", json={"task": "new session"})
        events = self._parse_sse(resp.text)
        start = events[0]
        assert start["stage"] == "start"
        sid = start["session_id"]
        assert len(sid) > 0

    def test_existing_session_id_reused(self, client):
        """When session_id is provided, the same ID is used in the response."""
        existing_sid = "my-fixed-session-id"
        resp = client.post("/api/run", json={"task": "continue", "session_id": existing_sid})
        events = self._parse_sse(resp.text)
        start = events[0]
        assert start["session_id"] == existing_sid

    def test_complete_event_contains_session_id_and_output_files(self, client):
        """The complete event includes session_id and output_files list."""
        resp = client.post("/api/run", json={"task": "test complete"})
        events = self._parse_sse(resp.text)
        complete = events[-1]
        assert complete["stage"] == "complete"
        assert "session_id" in complete
        assert "output_files" in complete
