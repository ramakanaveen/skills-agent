import os
import json
import uuid
import re
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import anthropic
from dotenv import load_dotenv

import skill_loader
import context_assembler
import tool_executor
import session as session_module
from config import cfg

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="Skills Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")

for d in [UPLOADS_DIR, OUTPUTS_DIR, SESSIONS_DIR]:
    os.makedirs(d, exist_ok=True)

anthropic_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY", "")
)


class RunRequest(BaseModel):
    task: str
    session_id: Optional[str] = None
    uploaded_files: Optional[List[dict]] = []


def sanitize_filename(filename: str) -> str:
    """Sanitise uploaded filename — basename only, alphanumeric + safe chars."""
    basename = os.path.basename(filename)
    safe = re.sub(r"[^\w.\-]", "_", basename)
    return safe[:200]


def sanitize_session_id(session_id: str) -> str:
    """Ensure session_id is a valid UUID-like string."""
    safe = re.sub(r"[^\w\-]", "", session_id)
    return safe[:64]


def sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    safe_name = sanitize_filename(file.filename)
    dest = os.path.join(UPLOADS_DIR, safe_name)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    return {"filename": safe_name, "path": f"uploads/{safe_name}"}


@app.get("/api/skills")
async def get_skills():
    return skill_loader.scan()


@app.get("/api/sessions")
async def get_sessions():
    return session_module.list_sessions()


@app.post("/api/run")
async def run_agent(body: RunRequest):
    return StreamingResponse(
        _agent_stream(body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _agent_stream(body: RunRequest):
    session_id = body.session_id or str(uuid.uuid4())
    uploaded_files = body.uploaded_files or []

    # Ensure per-session output directory exists
    session_output_dir = os.path.join(OUTPUTS_DIR, session_id)
    os.makedirs(session_output_dir, exist_ok=True)

    # Re-scan skills on every run so new skills are immediately available
    skills = skill_loader.scan()
    system_prompt = context_assembler.build_system_prompt(skills, uploaded_files)
    tools = context_assembler.build_tools()

    # Load conversation history
    history = session_module.load_history(session_id)
    messages = history + [{"role": "user", "content": body.task}]

    # Save user turn
    session_module.save_turn(session_id, "user", content=body.task)

    yield sse({"stage": "start", "session_id": session_id})

    for iteration in range(cfg.max_iterations):
        # Context budget guard
        context_size = len(json.dumps(messages, default=str)) // 4
        if context_size > cfg.context_budget:
            messages = messages[-cfg.context_trim_keep:]
            yield sse({"stage": "warning", "text": "Context trimmed to stay within limits"})

        try:
            response = anthropic_client.messages.create(
                model=cfg.model_name,
                max_tokens=cfg.max_tokens,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )
        except Exception as e:
            yield sse({"stage": "error", "text": str(e)})
            return

        # Stream Claude's text to frontend
        assistant_text = ""
        for block in response.content:
            if block.type == "text" and block.text:
                assistant_text = block.text
                yield sse({"stage": "thinking", "text": block.text})

        # Check stop condition
        if response.stop_reason == "end_turn":
            session_module.save_turn(session_id, "assistant", content=assistant_text)
            break

        # Handle tool calls
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                yield sse({
                    "stage": "tool_call",
                    "tool": block.name,
                    "input": block.input,
                })

                # Pass session_id so outputs are scoped to this session
                result = tool_executor.execute_tool(block.name, block.input, session_id=session_id, anthropic_client=anthropic_client)

                yield sse({
                    "stage": "tool_result",
                    "tool": block.name,
                    "result": result[:cfg.result_preview_chars],
                    "full_length": len(result),
                })

                session_module.save_turn(
                    session_id,
                    "tool",
                    content=result,
                    tool_name=block.name,
                    tool_input=block.input,
                    tool_result=result,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    # Collect only this session's output files
    try:
        outputs = [
            f for f in os.listdir(session_output_dir)
            if not f.startswith(".")
        ]
    except Exception:
        outputs = []

    yield sse({
        "stage": "complete",
        "session_id": session_id,
        "output_files": outputs,
    })


@app.get("/api/outputs/{session_id}")
async def get_session_outputs(session_id: str):
    safe_session = sanitize_session_id(session_id)
    session_output_dir = os.path.join(OUTPUTS_DIR, safe_session)
    if not os.path.isdir(session_output_dir):
        return []
    return [f for f in os.listdir(session_output_dir) if not f.startswith(".")]


@app.get("/api/download/{session_id}/{filename:path}")
async def download_file(session_id: str, filename: str):
    safe_session = sanitize_session_id(session_id)
    safe_file = sanitize_filename(filename)
    path = os.path.join(OUTPUTS_DIR, safe_session, safe_file)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=safe_file)


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    return session_module.read_transcript(session_id)


@app.get("/api/skill-stats")
async def get_skill_stats():
    """Return usage count per skill derived from session transcripts."""
    stats = {}
    if not os.path.isdir(SESSIONS_DIR):
        return stats
    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".jsonl"):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line.strip())
                    if record.get("tool_name") == "read_file":
                        inp = record.get("tool_input", {})
                        p = inp.get("path", "") if isinstance(inp, dict) else ""
                        if "SKILL.md" in p:
                            # Extract skill name from path
                            parts = p.replace("\\", "/").split("/")
                            if len(parts) >= 2:
                                skill_name = parts[-2]
                                stats[skill_name] = stats.get(skill_name, 0) + 1
        except Exception:
            continue
    return stats


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}
