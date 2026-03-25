import os
import json
import subprocess
from datetime import datetime

from config import cfg
from tool_registry import registry

BASE = os.path.abspath(os.path.dirname(__file__))
ALLOWED_ROOTS = ["skills", "uploads", "outputs", "workspace"]


def resolve_safe_path(raw_path: str) -> str:
    """
    Normalise and resolve relative segments like ../skills/
    Ensures the resolved path stays within BASE (backend/).
    """
    full = os.path.abspath(os.path.join(BASE, raw_path))
    if not full.startswith(BASE):
        raise ValueError(f"Path outside allowed directory: {raw_path}")
    return full


def _resolve_readable_path(raw_path: str, session_id: str | None) -> str:
    """
    Resolve a path for reading, applying session scoping for outputs/ paths.

    write_file, list_files, and scan_folder all scope outputs/ to
    outputs/{session_id}/ automatically. read_file and analyze_file must
    do the same so Claude can reference its own output files without
    knowing the session ID.

    Resolution order:
      1. If path is under outputs/ and a session is active, try
         outputs/{session_id}/{remainder} first.
      2. Fall back to the literal path (covers uploads/, skills/, workspace/).
    """
    if session_id and (raw_path == "outputs" or raw_path.startswith("outputs/")):
        remainder = raw_path[len("outputs/"):] if raw_path.startswith("outputs/") else ""
        if remainder:
            scoped = f"outputs/{session_id}/{remainder}"
            try:
                candidate = resolve_safe_path(scoped)
                if os.path.exists(candidate):
                    return candidate
            except ValueError:
                pass  # fall through to literal path
    return resolve_safe_path(raw_path)


# ── Tool handlers ──────────────────────────────────────────────────────────────
# Each handler signature: (input_data: dict, *, session_id=None, anthropic_client=None) -> str
# Handlers are registered at the bottom of this file.


def _handle_read_file(input_data: dict, **ctx) -> str:
    session_id = ctx.get("session_id")
    raw_path = input_data["path"]
    path = _resolve_readable_path(raw_path, session_id)
    if not os.path.exists(path):
        return f"ERROR: File not found: {raw_path}"
    with open(path, encoding="utf-8") as f:
        return f.read()


def _handle_write_file(input_data: dict, **ctx) -> str:
    session_id = ctx.get("session_id")
    filename = input_data["filename"]
    content = input_data["content"]

    if filename.startswith("../skills/public/"):
        path = resolve_safe_path(filename.replace("../", "", 1))
    elif filename.startswith("../skills/private/"):
        path = resolve_safe_path(filename.replace("../", "", 1))
    elif filename.startswith("../skills/"):
        bare = filename.replace("../skills/", "", 1)
        path = resolve_safe_path(f"skills/public/{bare}")
    elif filename.startswith("skills/public/") or filename.startswith("skills/private/"):
        path = resolve_safe_path(filename)
    elif filename.startswith("skills/"):
        bare = filename.replace("skills/", "", 1)
        path = resolve_safe_path(f"skills/public/{bare}")
    else:
        if session_id:
            path = resolve_safe_path(f"outputs/{session_id}/{filename}")
        else:
            path = resolve_safe_path(f"outputs/{filename}")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written: {os.path.basename(path)}"


def _handle_run_code(input_data: dict, **ctx) -> str:
    session_id = ctx.get("session_id")
    filename = input_data["filename"]
    runtime = input_data["runtime"]

    if session_id:
        path = resolve_safe_path(f"outputs/{session_id}/{filename}")
        cwd = os.path.join(BASE, "outputs", session_id)
        os.makedirs(cwd, exist_ok=True)
    else:
        path = resolve_safe_path(f"outputs/{filename}")
        cwd = os.path.join(BASE, "outputs")

    if not os.path.exists(path):
        return json.dumps({"error": f"File not found: {filename}", "exit_code": 1})

    result = subprocess.run(
        [runtime, path],
        capture_output=True,
        text=True,
        timeout=cfg.run_code_timeout,
        cwd=cwd,
    )
    return json.dumps({
        "stdout": result.stdout[-cfg.run_code_stdout_limit:],
        "stderr": result.stderr[-cfg.run_code_stderr_limit:],
        "exit_code": result.returncode,
    })


def _handle_list_files(input_data: dict, **ctx) -> str:
    session_id = ctx.get("session_id")
    directory = input_data["directory"].strip("/")

    if directory == "outputs" and session_id:
        directory = f"outputs/{session_id}"

    path = resolve_safe_path(directory)
    if not os.path.isdir(path):
        return "(empty)"

    entries = []
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        entries.append(f"{item}/" if os.path.isdir(item_path) else item)
    return "\n".join(sorted(entries)) if entries else "(empty)"


def _handle_scan_folder(input_data: dict, **ctx) -> str:
    session_id = ctx.get("session_id")
    directory = input_data["directory"].strip("/")
    extensions = input_data.get("extensions", [])

    if directory == "outputs" and session_id:
        directory = f"outputs/{session_id}"

    path = resolve_safe_path(directory)
    if not os.path.isdir(path):
        return f"ERROR: Not a directory: {directory}"

    results = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            if filename.startswith("."):
                continue
            if extensions and not any(
                filename.lower().endswith(ext.lower()) for ext in extensions
            ):
                continue
            filepath = os.path.join(root, filename)
            stat = os.stat(filepath)
            rel = os.path.relpath(filepath, BASE).replace(os.sep, "/")
            results.append({
                "name": filename,
                "path": rel,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })

    if not results:
        return "No files found matching criteria"

    lines = [f"Found {len(results)} file(s) in {directory}:\n"]
    for f in results:
        lines.append(
            f"  - {f['name']} ({f['size_bytes']} bytes, "
            f"modified {f['modified']})\n    path: {f['path']}"
        )
    return "\n".join(lines)


def _handle_analyze_file(input_data: dict, **ctx) -> str:
    import base64

    anthropic_client = ctx.get("anthropic_client")
    raw_path = input_data["path"]
    question = input_data.get("question", "Describe the contents of this file in detail.")

    try:
        path = _resolve_readable_path(raw_path, ctx.get("session_id"))
    except ValueError as e:
        return f"ERROR: Security violation — {e}"

    if not os.path.exists(path):
        return f"ERROR: File not found: {raw_path}"

    ext = os.path.splitext(path)[1].lower()

    TEXT_EXTENSIONS = {
        ".txt", ".md", ".csv", ".json",
        ".py", ".js", ".ts", ".yaml", ".yml",
        ".html", ".css", ".xml",
    }
    if ext in TEXT_EXTENSIONS:
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        return content[:cfg.text_file_limit]

    IMAGE_EXTENSIONS = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }

    if ext not in {".pdf"} | set(IMAGE_EXTENSIONS.keys()):
        return (
            f"Unsupported file type: {ext}. "
            f"Supported: PDF, images (PNG/JPG/WEBP/GIF), "
            f"text files (TXT/MD/CSV/JSON/PY/JS/TS/YAML/HTML/CSS/XML)"
        )

    if anthropic_client is None:
        return "ERROR: anthropic_client not available for analyze_file"

    with open(path, "rb") as f:
        file_bytes = f.read()
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    if ext == ".pdf":
        try:
            response = anthropic_client.messages.create(
                model=cfg.model_name,
                max_tokens=2048,
                messages=[{"role": "user", "content": [
                    {"type": "document", "source": {
                        "type": "base64", "media_type": "application/pdf", "data": b64,
                    }},
                    {"type": "text", "text": question},
                ]}],
            )
            return response.content[0].text
        except Exception as e:
            return f"ERROR analyzing PDF: {type(e).__name__}: {e}"

    try:
        response = anthropic_client.messages.create(
            model=cfg.model_name,
            max_tokens=2048,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": IMAGE_EXTENSIONS[ext],
                    "data": b64,
                }},
                {"type": "text", "text": question},
            ]}],
        )
        return response.content[0].text
    except Exception as e:
        return f"ERROR analyzing image: {type(e).__name__}: {e}"


def _handle_spawn_agent(input_data: dict, **ctx) -> str:
    session_id = ctx.get("session_id")
    anthropic_client = ctx.get("anthropic_client")

    task = input_data["task"]
    skill_name = input_data["skill_name"]
    input_context = input_data.get("input_data", "")
    subagent_model = input_data.get("model", cfg.model_name)

    if anthropic_client is None:
        return "ERROR: anthropic_client not available for spawn_agent"

    skill_path = None
    for visibility in ["public", "private"]:
        candidate = os.path.join(BASE, "skills", visibility, skill_name, "SKILL.md")
        if os.path.exists(candidate):
            skill_path = candidate
            break

    if skill_path is None:
        return f"ERROR: Skill not found: {skill_name}"

    with open(skill_path, encoding="utf-8") as f:
        skill_body = f.read()

    soul_path = os.path.join(BASE, "workspace", "SOUL.md")
    soul = open(soul_path, encoding="utf-8").read() if os.path.exists(soul_path) else ""

    subagent_system = f"""{soul}

## Your Skill
{skill_body}

## Important
You are a focused subagent. Complete the task given to you
using the skill above and the tools available. Be concise.
Return your findings clearly in plain text or markdown.
"""

    # Subagents get all registered tools except spawn_agent (no recursion)
    subagent_tools = registry.schemas(exclude={"spawn_agent"})

    user_message = task
    if input_context:
        user_message += f"\n\nContext / input data:\n{input_context[:8000]}"

    messages = [{"role": "user", "content": user_message}]

    try:
        for _ in range(10):
            response = anthropic_client.messages.create(
                model=subagent_model,
                max_tokens=cfg.max_tokens,
                system=subagent_system,
                tools=subagent_tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if block.type == "text" and block.text:
                        return block.text
                return "Subagent completed with no text response"

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    result = execute_tool(
                        block.name, block.input,
                        session_id=session_id,
                        anthropic_client=anthropic_client,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
                messages.append({"role": "user", "content": tool_results})
                continue

            break

        return "Subagent reached iteration limit without completing"

    except Exception as e:
        return f"ERROR in subagent: {type(e).__name__}: {e}"


# ── Public wrapper (backward-compatible) ──────────────────────────────────────

def execute_tool(name: str, input_data: dict, session_id: str = None,
                 anthropic_client=None) -> str:
    """
    Execute a tool call. Thin wrapper around registry.execute().

    All output file operations are scoped to outputs/{session_id}/ so
    sessions cannot see each other's files. Skills are global by design.
    """
    try:
        return registry.execute(
            name, input_data,
            session_id=session_id,
            anthropic_client=anthropic_client,
        )
    except ValueError as e:
        return f"ERROR: Security violation — {e}"
    except subprocess.TimeoutExpired:
        return json.dumps({
            "error": f"Execution timed out after {cfg.run_code_timeout} seconds",
            "exit_code": -1,
        })
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


# ── Tool registration ──────────────────────────────────────────────────────────
# Schemas live here alongside their handlers. context_assembler calls
# registry.schemas() to get the full list — no hardcoded tool list elsewhere.

registry.register("read_file", _handle_read_file, {
    "name": "read_file",
    "description": "Read any file by path relative to backend/. "
                   "Use to load skills, uploaded files, or outputs.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "e.g. skills/docx/SKILL.md or uploads/policy.md",
            }
        },
        "required": ["path"],
    },
})

registry.register("write_file", _handle_write_file, {
    "name": "write_file",
    "description": "Write content to a file. "
                   "Outputs go to backend/outputs/{filename}. "
                   "New skills go to backend/skills/{name}/SKILL.md "
                   "— use filename like ../skills/{name}/SKILL.md",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["filename", "content"],
    },
})

registry.register("run_code", _handle_run_code, {
    "name": "run_code",
    "description": "Run a file from backend/outputs/. "
                   "Returns stdout, stderr, exit_code.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "filename only, not full path",
            },
            "runtime": {
                "type": "string",
                "enum": ["node", "python3"],
            },
        },
        "required": ["filename", "runtime"],
    },
})

registry.register("list_files", _handle_list_files, {
    "name": "list_files",
    "description": "List files in a directory. "
                   "Allowed: skills/, uploads/, outputs/",
    "input_schema": {
        "type": "object",
        "properties": {
            "directory": {"type": "string"},
        },
        "required": ["directory"],
    },
})

registry.register("scan_folder", _handle_scan_folder, {
    "name": "scan_folder",
    "description": (
        "Scan a folder recursively and list all files with metadata "
        "(name, path, size, modified date). Use before batch processing "
        "to discover what files are available. "
        "Allowed directories: uploads/, outputs/, skills/public/, skills/private/. "
        "Optionally filter by file extensions e.g. [\".pdf\", \".txt\"]."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "e.g. 'uploads/' or 'skills/public/'",
            },
            "extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional filter e.g. [\".pdf\", \".txt\"]",
            },
        },
        "required": ["directory"],
    },
})

registry.register("analyze_file", _handle_analyze_file, {
    "name": "analyze_file",
    "description": (
        "Read and understand any file — PDF, image, or plain text. "
        "Sends PDFs and images directly to Claude for native understanding "
        "— preserves tables, charts, layout, and works on scanned documents. "
        "Plain text files (TXT, CSV, MD, JSON, PY etc) are returned as-is "
        "without an extra API call. "
        "Use for any uploaded file. "
        "Optionally provide a specific question to focus the analysis. "
        "Path must be relative to backend/ "
        "e.g. 'uploads/report.pdf' or 'uploads/chart.png'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Path relative to backend/, "
                    "e.g. 'uploads/report.pdf' or 'uploads/chart.png'"
                ),
            },
            "question": {
                "type": "string",
                "description": (
                    "Optional. Specific question about the file. "
                    "e.g. 'What is the revenue for Q3 2023?' "
                    "Defaults to a general description if omitted."
                ),
            },
        },
        "required": ["path"],
    },
})

registry.register("spawn_agent", _handle_spawn_agent, {
    "name": "spawn_agent",
    "description": (
        "Spawn a focused subagent to handle one specific part of a "
        "larger task. The subagent gets a single skill loaded into "
        "its context and runs its own agentic loop to completion, "
        "then returns its result as text. "
        "Use this to delegate specialised steps: for example, spawn "
        "a pdf-analyst subagent to summarise each PDF in a batch, "
        "then synthesise all results yourself. "
        "The subagent shares your session so its output files are "
        "available in the same outputs folder. "
        "Use model='claude-haiku-4-5-20251001' for subagents doing "
        "straightforward extraction or summarisation to reduce cost. "
        "Use the default model for subagents doing reasoning or writing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": (
                    "Specific instruction for the subagent. "
                    "Be precise — the subagent only sees this task "
                    "and its one skill, not your full conversation."
                ),
            },
            "skill_name": {
                "type": "string",
                "description": (
                    "Folder name of the skill to give the subagent. "
                    "e.g. 'pdf-analyst', 'data-analyst', "
                    "'folder-summariser'. "
                    "The subagent will load this skill and follow "
                    "its instructions."
                ),
            },
            "input_data": {
                "type": "string",
                "description": (
                    "Data or context to pass to the subagent. "
                    "e.g. a filename, a snippet of text, a question "
                    "to answer. Truncated to 8000 chars."
                ),
            },
            "model": {
                "type": "string",
                "description": (
                    "Optional. Model for the subagent to use. "
                    "Defaults to the main model. "
                    "Use 'claude-haiku-4-5-20251001' for simple "
                    "extraction/summarisation tasks to reduce cost."
                ),
            },
        },
        "required": ["task", "skill_name"],
    },
})
