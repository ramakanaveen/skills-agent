import os
import json
import subprocess
from datetime import datetime

from config import cfg

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


def execute_tool(name: str, input_data: dict, session_id: str = None, anthropic_client=None) -> str:
    """
    Execute a tool call. All output file operations are scoped to
    outputs/{session_id}/ so sessions cannot see each other's files.
    Skills are global (shared across sessions by design).
    """
    try:
        if name == "read_file":
            path = resolve_safe_path(input_data["path"])
            if not os.path.exists(path):
                return f"ERROR: File not found: {input_data['path']}"
            with open(path, encoding="utf-8") as f:
                return f.read()

        elif name == "write_file":
            filename = input_data["filename"]
            content = input_data["content"]
            # Skill paths: ../skills/public/... or ../skills/private/...
            # (legacy ../skills/... also accepted, routed to public/)
            if filename.startswith("../skills/public/"):
                path = resolve_safe_path(filename.replace("../", "", 1))
            elif filename.startswith("../skills/private/"):
                path = resolve_safe_path(filename.replace("../", "", 1))
            elif filename.startswith("../skills/"):
                # Legacy path without visibility — default to public
                bare = filename.replace("../skills/", "", 1)
                path = resolve_safe_path(f"skills/public/{bare}")
            elif filename.startswith("skills/public/") or filename.startswith("skills/private/"):
                path = resolve_safe_path(filename)
            elif filename.startswith("skills/"):
                # Legacy — default to public
                bare = filename.replace("skills/", "", 1)
                path = resolve_safe_path(f"skills/public/{bare}")
            else:
                # All other outputs are scoped to this session
                if session_id:
                    path = resolve_safe_path(f"outputs/{session_id}/{filename}")
                else:
                    path = resolve_safe_path(f"outputs/{filename}")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Written: {os.path.basename(path)}"

        elif name == "run_code":
            filename = input_data["filename"]
            runtime = input_data["runtime"]  # "node" or "python3"
            if session_id:
                path = resolve_safe_path(f"outputs/{session_id}/{filename}")
                cwd = os.path.join(BASE, "outputs", session_id)
                os.makedirs(cwd, exist_ok=True)
            else:
                path = resolve_safe_path(f"outputs/{filename}")
                cwd = os.path.join(BASE, "outputs")
            if not os.path.exists(path):
                return json.dumps({
                    "error": f"File not found: {filename}",
                    "exit_code": 1
                })
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
                "exit_code": result.returncode
            })

        elif name == "list_files":
            directory = input_data["directory"].strip("/")
            # Scope outputs/ listing to current session only
            if directory == "outputs" and session_id:
                directory = f"outputs/{session_id}"
            path = resolve_safe_path(directory)
            if not os.path.isdir(path):
                # Return empty rather than error if session dir doesn't exist yet
                return "(empty)"
            entries = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    entries.append(f"{item}/")
                else:
                    entries.append(item)
            return "\n".join(sorted(entries)) if entries else "(empty)"

        elif name == "analyze_file":
            import base64

            raw_path = input_data["path"]
            question = input_data.get(
                "question",
                "Describe the contents of this file in detail."
            )

            if anthropic_client is None and os.path.splitext(raw_path)[1].lower() not in {
                ".txt", ".md", ".csv", ".json", ".py", ".js", ".ts",
                ".yaml", ".yml", ".html", ".css", ".xml"
            }:
                # Will be caught below — just need to check after path resolution
                pass

            try:
                path = resolve_safe_path(raw_path)
            except ValueError as e:
                return f"ERROR: Security violation — {e}"

            if not os.path.exists(path):
                return f"ERROR: File not found: {raw_path}"

            ext = os.path.splitext(path)[1].lower()

            TEXT_EXTENSIONS = {
                ".txt", ".md", ".csv", ".json",
                ".py", ".js", ".ts", ".yaml", ".yml",
                ".html", ".css", ".xml"
            }
            if ext in TEXT_EXTENSIONS:
                with open(path, encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return content[:cfg.text_file_limit]

            IMAGE_EXTENSIONS = {
                ".png":  "image/png",
                ".jpg":  "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".gif":  "image/gif",
            }

            if ext not in {".pdf"} | set(IMAGE_EXTENSIONS.keys()):
                return (
                    f"Unsupported file type: {ext}. "
                    f"Supported: PDF, images (PNG/JPG/WEBP/GIF), "
                    f"text files (TXT/MD/CSV/JSON/PY/JS/TS/YAML/HTML/CSS/XML)"
                )

            if anthropic_client is None:
                return "ERROR: anthropic_client not available for analyze_file"

            if ext == ".pdf":
                with open(path, "rb") as f:
                    file_bytes = f.read()
                b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
                try:
                    response = anthropic_client.messages.create(
                        model=cfg.model_name,
                        max_tokens=2048,
                        messages=[{
                            "role": "user",
                            "content": [
                                {
                                    "type": "document",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "application/pdf",
                                        "data": b64,
                                    }
                                },
                                {"type": "text", "text": question}
                            ]
                        }]
                    )
                    return response.content[0].text
                except Exception as e:
                    return f"ERROR analyzing PDF: {type(e).__name__}: {e}"

            if ext in IMAGE_EXTENSIONS:
                with open(path, "rb") as f:
                    file_bytes = f.read()
                b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
                try:
                    response = anthropic_client.messages.create(
                        model=cfg.model_name,
                        max_tokens=2048,
                        messages=[{
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": IMAGE_EXTENSIONS[ext],
                                        "data": b64,
                                    }
                                },
                                {"type": "text", "text": question}
                            ]
                        }]
                    )
                    return response.content[0].text
                except Exception as e:
                    return f"ERROR analyzing image: {type(e).__name__}: {e}"

        elif name == "spawn_agent":
            from context_assembler import build_tools as _build_tools

            task = input_data["task"]
            skill_name = input_data["skill_name"]
            input_context = input_data.get("input_data", "")
            subagent_model = input_data.get("model", cfg.model_name)

            if anthropic_client is None:
                return "ERROR: anthropic_client not available for spawn_agent"

            # Load the named skill — check public/ then private/
            skill_path = None
            for visibility in ["public", "private"]:
                candidate = os.path.join(BASE, "skills", visibility,
                                         skill_name, "SKILL.md")
                if os.path.exists(candidate):
                    skill_path = candidate
                    break

            if skill_path is None:
                return f"ERROR: Skill not found: {skill_name}"

            with open(skill_path, encoding="utf-8") as f:
                skill_body = f.read()

            # Load SOUL.md for subagent identity
            soul_path = os.path.join(BASE, "workspace", "SOUL.md")
            soul = open(soul_path, encoding="utf-8").read() \
                   if os.path.exists(soul_path) else ""

            # Lean system prompt — soul + one skill only
            subagent_system = f"""{soul}

## Your Skill
{skill_body}

## Important
You are a focused subagent. Complete the task given to you
using the skill above and the tools available. Be concise.
Return your findings clearly in plain text or markdown.
"""

            # Subagent gets a reduced set of tools — no spawn_agent
            # (no recursive spawning), no list_files complexity
            subagent_tools = [
                t for t in _build_tools()
                if t["name"] in {"read_file", "write_file",
                                 "run_code", "list_files",
                                 "scan_folder", "analyze_file"}
            ]

            # Initial user message
            user_message = task
            if input_context:
                user_message += f"\n\nContext / input data:\n{input_context[:8000]}"

            messages = [{"role": "user", "content": user_message}]

            # Run the subagent agentic loop (max 10 iterations)
            try:
                for iteration in range(10):
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
                        messages.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        tool_results = []
                        for block in response.content:
                            if block.type != "tool_use":
                                continue
                            result = execute_tool(
                                block.name,
                                block.input,
                                session_id=session_id,
                                anthropic_client=anthropic_client,
                            )
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })
                        messages.append({
                            "role": "user",
                            "content": tool_results
                        })
                        continue

                    break

                return "Subagent reached iteration limit without completing"

            except Exception as e:
                return f"ERROR in subagent: {type(e).__name__}: {e}"

        elif name == "scan_folder":
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
                        filename.lower().endswith(ext.lower())
                        for ext in extensions
                    ):
                        continue
                    filepath = os.path.join(root, filename)
                    stat = os.stat(filepath)
                    rel = os.path.relpath(filepath, BASE).replace(os.sep, "/")
                    results.append({
                        "name": filename,
                        "path": rel,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime
                        ).strftime("%Y-%m-%d %H:%M"),
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

        return f"ERROR: Unknown tool: {name}"

    except ValueError as e:
        return f"ERROR: Security violation — {e}"
    except subprocess.TimeoutExpired:
        return json.dumps({
            "error": f"Execution timed out after {cfg.run_code_timeout} seconds",
            "exit_code": -1
        })
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"
