import os
from datetime import datetime
from typing import List, Dict


def build_system_prompt(skills: List[Dict], uploaded_files: List[Dict] = None) -> str:
    if uploaded_files is None:
        uploaded_files = []

    backend_dir = os.path.dirname(__file__)

    soul = open(os.path.join(backend_dir, "workspace", "SOUL.md"), encoding="utf-8").read()
    agents = open(os.path.join(backend_dir, "workspace", "AGENTS.md"), encoding="utf-8").read()
    tools = open(os.path.join(backend_dir, "workspace", "TOOLS.md"), encoding="utf-8").read()

    if skills:
        skills_block = "\n".join([
            f"- **{s['name']}** [{s.get('visibility', 'public')}]: {s['description']}\n"
            f"  Read with: read_file(\"{s['skill_md_path']}\")"
            for s in skills
        ])
        skills_block += (
            "\n\n## Skill Visibility Rules\n"
            "When creating a new skill, ALWAYS ask the user first:\n"
            "  'Should this skill be **public** (shared with everyone, committed to git)\n"
            "   or **private** (only visible to you, never committed)?\n'\n"
            "Then write to the correct path:\n"
            "  Public skill:  write_file(\"../skills/public/{name}/SKILL.md\", content)\n"
            "  Private skill: write_file(\"../skills/private/{name}/SKILL.md\", content)"
        )
    else:
        skills_block = "(no skills available yet)"

    files_block = ""
    if uploaded_files:
        files_block = "## User-Uploaded Files (read with read_file)\n"
        files_block += "\n".join([
            f"- {f['name']}: read_file(\"uploads/{f['name']}\")"
            for f in uploaded_files
        ])

    return f"""{soul}

{agents}

{tools}

## Available Skills
{skills_block}

{files_block}

Current time: {datetime.utcnow().isoformat()}Z
"""


def build_tools() -> list:
    return [
        {
            "name": "read_file",
            "description": "Read any file by path relative to backend/. "
                           "Use to load skills, uploaded files, or outputs.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "e.g. skills/docx/SKILL.md or uploads/policy.md"
                    }
                },
                "required": ["path"]
            }
        },
        {
            "name": "write_file",
            "description": "Write content to a file. "
                           "Outputs go to backend/outputs/{filename}. "
                           "New skills go to backend/skills/{name}/SKILL.md "
                           "— use filename like ../skills/{name}/SKILL.md",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["filename", "content"]
            }
        },
        {
            "name": "run_code",
            "description": "Run a file from backend/outputs/. "
                           "Returns stdout, stderr, exit_code.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "filename only, not full path"
                    },
                    "runtime": {
                        "type": "string",
                        "enum": ["node", "python3"]
                    }
                },
                "required": ["filename", "runtime"]
            }
        },
        {
            "name": "list_files",
            "description": "List files in a directory. "
                           "Allowed: skills/, uploads/, outputs/",
            "input_schema": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"}
                },
                "required": ["directory"]
            }
        },
        {
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
                        "description": "e.g. 'uploads/' or 'skills/public/'"
                    },
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional filter e.g. [\".pdf\", \".txt\"]"
                    }
                },
                "required": ["directory"]
            }
        },
        {
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
                        )
                    },
                    "question": {
                        "type": "string",
                        "description": (
                            "Optional. Specific question about the file. "
                            "e.g. 'What is the revenue for Q3 2023?' "
                            "Defaults to a general description if omitted."
                        )
                    }
                },
                "required": ["path"]
            }
        },
    ]
