# Skills Agent — Claude Context

This file gives Claude Code full context on the project so it can assist
effectively without needing to re-explore the codebase each session.

---

## What this project is

A local AI agent where **all task knowledge lives in SKILL.md files**, not in
Python code. The Python backend is fully task-agnostic. New capabilities are
added by dropping a new `SKILL.md` into `backend/skills/public/` or
`backend/skills/private/`.

**Stack:**
- Backend: Python + FastAPI + Anthropic SDK (streaming via SSE)
- Frontend: React + Vite (single page, no router)
- Storage: Local filesystem + JSONL session transcripts

---

## Key architectural rules — never break these

1. **Tool executor is the security boundary.** All file access goes through
   `resolve_safe_path()` in `tool_executor.py`. Never bypass it.

2. **Session isolation.** All output files go to `outputs/{session_id}/`.
   The `execute_tool()` function takes `session_id` and scopes file writes.

3. **Skills are global, outputs are per-session.** A skill written in one
   session is available to all. Output files in `outputs/` are not.

4. **Config values are never hardcoded.** All tunable values (model name,
   timeouts, limits) live in `backend/config.yaml` and are loaded via
   `backend/config.py`. Import `from config import cfg` to use them.

5. **New tools require two changes:** add an `elif` branch in
   `tool_executor.py` AND add a tool definition dict in
   `context_assembler.py` `build_tools()`. Missing either = tool silently
   not available to the agent.

6. **Frontend config is centralised.** All API endpoint strings and UI
   constants live in `frontend/src/config.js`. Never hardcode `/api/...`
   in components.

---

## Project layout

```
skills-agent/
├── backend/
│   ├── main.py                 # FastAPI app, SSE agentic loop
│   ├── tool_executor.py        # execute_tool(name, input, session_id, anthropic_client)
│   ├── context_assembler.py    # build_system_prompt(), build_tools()
│   ├── skill_loader.py         # scan() — reads both public/ and private/
│   ├── session.py              # save_turn(), load_history(), list_sessions()
│   ├── config.yaml             # All tunable values
│   ├── config.py               # cfg object — import this everywhere
│   ├── requirements.txt
│   ├── workspace/
│   │   ├── SOUL.md             # Agent identity/persona
│   │   ├── AGENTS.md           # Behavioural rules injected into every prompt
│   │   └── TOOLS.md            # Tool reference injected into every prompt
│   ├── skills/
│   │   ├── public/             # Committed to git
│   │   │   ├── docx/           # Create Word documents (Node.js)
│   │   │   ├── skill-creator/  # Meta-skill: write new skills
│   │   │   ├── scripture/      # Bible verse lookup
│   │   │   ├── travel-planner/ # Trip planning
│   │   │   ├── pdf-analyst/    # PDF summarisation via analyze_file
│   │   │   ├── folder-summariser/ # Batch-process all files in a folder
│   │   │   └── data-analyst/   # CSV/JSON analysis with matplotlib
│   │   └── private/            # Gitignored — local only
│   ├── outputs/                # Gitignored — per-session subdirs
│   ├── uploads/                # Gitignored — user uploads
│   ├── sessions/               # Gitignored — JSONL transcripts
│   └── tests/
│       ├── conftest.py         # tmp_backend fixture, patches BASE/SESSIONS_DIR
│       ├── test_tool_executor.py
│       ├── test_skill_loader.py
│       ├── test_session.py
│       ├── test_context_assembler.py
│       └── test_api.py
└── frontend/
    └── src/
        ├── App.jsx             # Root: chat state, session mgmt, SSE handler
        ├── config.js           # API endpoints + UI constants
        ├── themes.js           # 4 themes via CSS variables + localStorage
        ├── index2.css          # Global styles
        ├── main.jsx            # Entry point
        └── components/
            ├── ChatView.jsx    # Chat bubbles + markdown rendering
            ├── ReplyBar.jsx    # Input bar + file upload
            ├── OutputPanel.jsx # 4 tabs: Files, Sessions, Context, Transcript
            ├── SkillDirectory.jsx
            ├── ThemeToggle.jsx
            ├── AgentTrace.jsx  # Collapsible tool call/result events
            └── ContextInspector.jsx
```

---

## The 6 tools

| Tool | Signature | What it does |
|---|---|---|
| `read_file` | `path` | Read any text file relative to `backend/` |
| `write_file` | `filename, content` | Write file — routes to `outputs/{session_id}/` or `skills/public\|private/` |
| `run_code` | `filename, runtime` | Execute script from `outputs/{session_id}/`; runtime = `python3` or `node` |
| `list_files` | `directory` | Non-recursive directory listing |
| `scan_folder` | `directory, extensions?` | Recursive scan with file metadata + optional extension filter |
| `analyze_file` | `path, question?` | PDFs/images → sent to Claude API natively; text files → returned directly |

`analyze_file` requires `anthropic_client` to be passed into `execute_tool()`.
This is already done in `main.py`. Tests mock it with `MagicMock`.

---

## How to add a new tool

1. Add `elif name == "new_tool":` block in `tool_executor.py`
   - Use `resolve_safe_path()` for any file access
   - Use `cfg.*` for any configurable limits
   - Accept `session_id` and `anthropic_client` as needed

2. Add tool dict to `build_tools()` in `context_assembler.py`

3. Update `backend/workspace/TOOLS.md` with the new tool description

4. Add tests in `test_tool_executor.py` following the existing class pattern

5. Add icon to `TOOL_ICONS` in `frontend/src/components/AgentTrace.jsx`

---

## How to add a new skill

Create `backend/skills/public/{name}/SKILL.md` with YAML frontmatter:

```markdown
---
name: my-skill
category: utility   # utility | creation | planning | development
description: >
  One or two sentences. Include trigger phrases.
  Triggers on: "phrase 1", "phrase 2".
---

# My Skill

## When to use
...

## Procedure
1. read_file("skills/public/my-skill/SKILL.md")
2. ...

## Output
...
```

No code changes needed — `skill_loader.py` auto-discovers it.

---

## Config reference

`backend/config.yaml` — all overridable via `SKILLS_AGENT_<KEY>` env vars:

```yaml
model:
  name: claude-sonnet-4-20250514   # SKILLS_AGENT_MODEL_NAME
  max_tokens: 8096

agent:
  max_iterations: 20               # hard cap on agentic loop
  context_budget: 150000           # trim messages when exceeded
  context_trim_keep: 16

tools:
  result_preview_chars: 500        # chars of tool result shown in frontend trace
  run_code_timeout: 30             # seconds before subprocess killed
  text_file_limit: 50000           # max chars returned by analyze_file for text files

server:
  cors_origins:
    - http://localhost:5173
```

---

## Running tests

```bash
cd backend
pytest tests/ -v          # 109 tests, should all pass
pytest tests/ -k "scan"   # run a specific subset
```

The `tmp_backend` fixture in `conftest.py` creates an isolated temp dir
mirroring the real backend structure and patches `BASE`, `SESSIONS_DIR`,
`PUBLIC_DIR`, `PRIVATE_DIR` so tests never touch real files.

---

## Gitignore summary

Committed: source code, `skills/public/`, `workspace/`, tests, config
Not committed: `.env`, `outputs/`, `uploads/`, `sessions/`, `skills/private/`, `node_modules/`

---

## Current branch

Working branch: `skill-101-102-103`
Main is stable and merged.
