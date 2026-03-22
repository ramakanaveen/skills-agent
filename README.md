# Skills Agent

A local AI agent where all task knowledge lives in Markdown files (`SKILL.md`), not in Python code. The Python backend is fully task-agnostic — teach it new capabilities by dropping in a new skill file.

## Stack

- **Backend**: Python + FastAPI + Anthropic SDK
- **Frontend**: React + Vite, multi-theme UI (Dark, Synthwave, Light, Terminal)
- **Streaming**: Server-Sent Events via `StreamingResponse`
- **Storage**: Local filesystem, JSONL session transcripts

## How to run

```bash
# 1. Add your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 2. Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## Project structure

```
skills-agent/
├── .env                          # ANTHROPIC_API_KEY (never committed)
├── .gitignore
├── backend/
│   ├── main.py                   # FastAPI routes + agentic loop (SSE streaming)
│   ├── context_assembler.py      # Builds system prompt from workspace/ + skills
│   ├── skill_loader.py           # Scans skills/public/ + skills/private/
│   ├── tool_executor.py          # Executes tools with path safety + session scoping
│   ├── session.py                # JSONL transcripts, load_history, list_sessions
│   ├── config.yaml               # All tunable values (model, limits, timeouts)
│   ├── config.py                 # Loads config.yaml with env var overrides
│   ├── requirements.txt
│   ├── workspace/
│   │   ├── SOUL.md               # Agent identity
│   │   ├── AGENTS.md             # Behavioural rules
│   │   └── TOOLS.md              # Tool descriptions
│   ├── skills/
│   │   ├── public/               # Committed to git — shared with everyone
│   │   │   ├── docx/SKILL.md
│   │   │   ├── skill-creator/SKILL.md
│   │   │   ├── scripture/SKILL.md
│   │   │   ├── travel-planner/SKILL.md
│   │   │   ├── pdf-analyst/SKILL.md
│   │   │   ├── folder-summariser/SKILL.md
│   │   │   └── data-analyst/SKILL.md
│   │   └── private/              # Gitignored — yours only
│   ├── outputs/{session_id}/     # Per-session generated files (gitignored)
│   ├── uploads/                  # User-uploaded files (gitignored)
│   ├── sessions/                 # JSONL audit trails (gitignored)
│   └── tests/                   # 95 pytest tests
│       ├── conftest.py
│       ├── test_api.py
│       ├── test_context_assembler.py
│       ├── test_session.py
│       ├── test_skill_loader.py
│       └── test_tool_executor.py
└── frontend/
    └── src/
        ├── App.jsx               # Chat state, session management, SSE stream handler
        ├── config.js             # API endpoints + UI constants (single source of truth)
        ├── themes.js             # 4 themes with CSS variable injection + localStorage
        ├── index2.css            # Global styles
        ├── main.jsx              # Entry point, theme applied before first render
        └── components/
            ├── ChatView.jsx      # Conversational UI with markdown + inline tool trace
            ├── ReplyBar.jsx      # Always-visible reply input, file upload
            ├── OutputPanel.jsx   # 4 tabs: Output Files, Sessions, Context, Transcript
            ├── SkillDirectory.jsx# Skill cards, category filters, usage stats
            ├── ThemeToggle.jsx   # Theme switcher dropdown
            ├── AgentTrace.jsx    # Collapsible tool call / result events
            └── ContextInspector.jsx
```

## Configuration

All backend tunable values live in `backend/config.yaml`. Every value can be overridden with an environment variable prefixed `SKILLS_AGENT_`:

```yaml
model:
  name: claude-sonnet-4-20250514   # SKILLS_AGENT_MODEL_NAME
  max_tokens: 8096                  # SKILLS_AGENT_MAX_TOKENS

agent:
  max_iterations: 20               # SKILLS_AGENT_AGENT_MAX_ITERATIONS
  context_budget: 150000           # SKILLS_AGENT_AGENT_CONTEXT_BUDGET

tools:
  run_code_timeout: 30             # SKILLS_AGENT_TOOLS_RUN_CODE_TIMEOUT
```

Frontend API endpoints and UI constants are centralised in `frontend/src/config.js` and can be overridden via `VITE_*` env vars:

```js
VITE_API_BASE=https://myserver.example.com
VITE_FILE_PREVIEW_CHARS=5000
```

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/upload` | Save file to `uploads/` |
| `GET` | `/api/skills` | List all skills (rescans on every call) |
| `GET` | `/api/skill-stats` | Usage count per skill derived from transcripts |
| `GET` | `/api/sessions` | List past sessions with preview + turn count |
| `POST` | `/api/run` | Start/continue agentic loop, returns SSE stream |
| `GET` | `/api/outputs/{session_id}` | List output files for a session |
| `GET` | `/api/download/{session_id}/{filename}` | Download a session output file |
| `GET` | `/api/session/{session_id}` | Full JSONL transcript |
| `GET` | `/api/health` | Health check |

## Skills

Skills live in `backend/skills/` and are plain Markdown files with YAML frontmatter.

```
backend/skills/
├── public/    ← committed to git, available to all deployments
└── private/   ← gitignored, local only
```

### Writing a skill

Every skill is a folder with a `SKILL.md`:

```
backend/skills/public/my-skill/SKILL.md
```

```markdown
---
name: my-skill
description: >
  Use this skill when the user asks to do X.
  Triggers on: "do X", "help me with X".
category: utility   # utility | creation | planning | development
---

# My Skill

## When to use
...

## Procedure
1. read_file("skills/public/my-skill/SKILL.md")
2. write_file("output.py", "...")
3. run_code("output.py", "python3")

## Output
Produces output.py in outputs/{session_id}/
```

### Available tools (inside skills)

| Tool | Purpose |
|---|---|
| `read_file(path)` | Read any text file relative to `backend/` |
| `write_file(filename, content)` | Write to `outputs/{session_id}/` or `skills/public\|private/` |
| `run_code(filename, runtime)` | Execute a script from `outputs/{session_id}/`, runtime = `python3` or `node` |
| `list_files(directory)` | Top-level listing of `skills/`, `uploads/`, or `outputs/` |
| `scan_folder(directory, extensions?)` | Recursive scan with file metadata; optional extension filter e.g. `[".pdf", ".csv"]` |
| `analyze_file(path, question?)` | Understand any file — PDFs and images sent to Claude natively (tables, charts, scanned pages all work); text files returned directly. Optional `question` focuses the analysis. |

### The meta-skill: skill-creator

The agent can write new skills itself. When no skill matches a task, it reads `skill-creator`, asks you **"public or private?"**, then writes the new skill to the correct path. The skill is immediately available for the current and all future sessions.

## Session isolation

Every session gets its own `outputs/{session_id}/` directory. Sessions cannot see each other's output files. Skills are intentionally global — a skill created in one session is available in all others.

## Themes

The UI supports 4 themes switchable from the top nav, persisted to `localStorage`:

| Theme | Description |
|---|---|
| Dark | Default dark terminal aesthetic |
| Synthwave | Purple/pink neon |
| Light | Clean light mode |
| Terminal | Green-on-black classic terminal |

## Running tests

```bash
cd backend
pytest tests/ -v
# 109 tests covering tool executor, skill loader, session, context assembler, and API
```

## What's planned

- **CI/CD pipeline**: GitHub Actions deploy workflow
- **Private skills repo**: `skills/private/` synced from a separate private GitHub repo on deploy
- **Skill sharing**: share a private skill with specific users
