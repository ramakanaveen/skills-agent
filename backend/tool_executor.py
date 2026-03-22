import os
import json
import subprocess

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


def execute_tool(name: str, input_data: dict, session_id: str = None) -> str:
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
