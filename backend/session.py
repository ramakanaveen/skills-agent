import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")


def new_session_id() -> str:
    return str(uuid.uuid4())


def _session_path(session_id: str) -> str:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return os.path.join(SESSIONS_DIR, f"{session_id}.jsonl")


def save_turn(
    session_id: str,
    role: str,
    content: str = "",
    tool_name: Optional[str] = None,
    tool_input: Optional[dict] = None,
    tool_result: Optional[str] = None,
):
    """Append one JSON line per event to the session transcript."""
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "role": role,
        "content": content[:2000] if content else "",
    }
    if tool_name:
        record["tool_name"] = tool_name
    if tool_input is not None:
        record["tool_input"] = tool_input
    if tool_result is not None:
        record["tool_result"] = tool_result[:1000] if tool_result else ""

    path = _session_path(session_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_history(session_id: str, max_turns: int = 20) -> List[Dict]:
    """
    Read last max_turns lines, reconstruct messages array for Anthropic API.
    Returns list of {"role": "user"|"assistant", "content": ...}
    """
    path = _session_path(session_id)
    if not os.path.exists(path):
        return []

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    lines = lines[-max_turns:]

    messages = []
    for line in lines:
        try:
            record = json.loads(line.strip())
            if record["role"] == "user" and record.get("content"):
                messages.append({"role": "user", "content": record["content"]})
            elif record["role"] == "assistant" and record.get("content"):
                messages.append({"role": "assistant", "content": record["content"]})
        except (json.JSONDecodeError, KeyError):
            continue

    return messages


def read_transcript(session_id: str) -> List[Dict]:
    """Return all transcript lines as parsed JSON objects."""
    path = _session_path(session_id)
    if not os.path.exists(path):
        return []

    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def list_sessions() -> List[Dict]:
    """
    List all sessions with metadata for the session switcher.
    Returns: [{session_id, created_at, preview, turn_count, message_count}]
    sorted by most recent first.
    """
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    sessions = []

    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".jsonl"):
            continue
        session_id = fname[:-6]  # strip .jsonl
        path = os.path.join(SESSIONS_DIR, fname)

        try:
            stat = os.stat(path)
            created_at = datetime.utcfromtimestamp(stat.st_ctime).isoformat() + "Z"
            updated_at = datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z"

            # Read first user message as preview + count turns
            preview = ""
            user_count = 0
            assistant_count = 0

            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("role") == "user":
                            user_count += 1
                            if not preview and record.get("content"):
                                preview = record["content"][:120]
                        elif record.get("role") == "assistant":
                            assistant_count += 1
                    except json.JSONDecodeError:
                        pass

            sessions.append({
                "session_id": session_id,
                "created_at": created_at,
                "updated_at": updated_at,
                "preview": preview,
                "user_turns": user_count,
                "assistant_turns": assistant_count,
            })
        except Exception:
            continue

    # Most recently modified first
    sessions.sort(key=lambda s: s["updated_at"], reverse=True)
    return sessions
