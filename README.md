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
├── CLAUDE.md                     # Claude Code context file
├── backend/
│   ├── main.py                   # FastAPI routes + agentic loop (SSE streaming)
│   ├── context_assembler.py      # Builds system prompt from workspace/ + skills
│   ├── skill_loader.py           # Scans skills/public/ + skills/private/
│   ├── tool_executor.py          # Executes tools with path safety + session scoping
│   ├── session.py                # JSONL transcripts, load_history, list_sessions
│   ├── config.yaml               # All tunable values — config (not secrets) lives here
│   ├── config.py                 # Loads config.yaml with env var overrides
│   ├── providers/
│   │   ├── anthropic_provider.py # Direct Anthropic API client
│   │   └── vertex_provider.py    # Vertex AI client — override _get_token() for custom auth
│   ├── requirements.txt
│   ├── workspace/
│   │   ├── SOUL.md               # Agent identity
│   │   ├── AGENTS.md             # Behavioural rules
│   │   └── TOOLS.md              # Tool descriptions
│   ├── skills/
│   │   ├── public/               # Committed to git — shared with everyone
│   │   │   ├── docx/SKILL.md           # Create Word documents (Node.js)
│   │   │   ├── skill-creator/SKILL.md  # Meta-skill: write new skills
│   │   │   ├── scripture/SKILL.md      # Bible verse lookup
│   │   │   ├── travel-planner/SKILL.md # Trip planning
│   │   │   ├── pdf-analyst/SKILL.md    # PDF summarisation via analyze_file
│   │   │   ├── folder-summariser/SKILL.md # Batch-process all files in a folder
│   │   │   └── data-analyst/SKILL.md   # CSV/JSON analysis with matplotlib charts
│   │   └── private/              # Gitignored — yours only
│   ├── outputs/{session_id}/     # Per-session generated files (gitignored)
│   ├── uploads/                  # User-uploaded files (gitignored)
│   ├── sessions/                 # JSONL audit trails (gitignored)
│   └── tests/                    # 109 pytest tests
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
            ├── ChatView.jsx      # Chat bubbles, markdown + inline charts, collapsible trace
            ├── ReplyBar.jsx      # Always-visible reply input, file upload
            ├── OutputPanel.jsx   # 2 tabs: Preview, Files — output-only right panel
            ├── SessionDrawer.jsx # Slide-in history drawer with search + date grouping
            ├── SkillDirectory.jsx# Skill cards, category filters, usage stats
            ├── ThemeToggle.jsx   # Theme switcher dropdown
            └── AgentTrace.jsx    # Collapsible tool call / result events
```

## UI Layout

The interface is split into two independently scrollable panels with a **draggable divider**:

```
┌─────────────────────┬─┬──────────────────────┐
│   Chat (left)       │ │   Right panel        │
│                     │◄►│                      │
│ [▶ Agent processing]│ │ [Preview][Files]...  │
│ Markdown response   │ │                      │
│ Inline charts       │ │ Rendered output      │
│                     │ │ File dropdown        │
├─────────────────────┤ │                      │
│ [Reply bar]         │ │                      │
└─────────────────────┴─┴──────────────────────┘
```

- Drag the divider to resize panels (20–80% range, persisted to localStorage)
- Left panel: conversation, collapsible agent trace, inline chart images, session bar with History button
- Right panel: output-focused (Preview + Files); switches to Skill Directory when Skills nav is active

## Top navigation

| Item | Purpose |
|---|---|
| **Workspace** | Default view — chat panel with the agent |
| **Skills** | Toggles right panel to show the Skill Directory; auto-returns to output when a task completes |

## Right panel tabs

| Tab | Purpose |
|---|---|
| **Preview** | Auto-activates when task completes. Renders the latest output file (markdown with tables/charts, images). File dropdown to switch between outputs. |
| **Files (n)** | List all generated files with inline preview and download. Export to PDF or combined Markdown. |

## Session History drawer

Clicking **⏱ History** in the session bar slides a drawer over the left panel:
- Search bar — filter by session ID or first message
- Sessions grouped by date: Today / Yesterday / This week / Older
- Each card shows session ID, relative timestamp, first message preview, turn count
- Active session highlighted with accent border
- **+ New Session** pinned at the bottom

## Configuration

All backend tunable values live in `backend/config.yaml`. Every value can be overridden with an environment variable prefixed `SKILLS_AGENT_`:

```yaml
provider: anthropic                  # SKILLS_AGENT_PROVIDER — "anthropic" or "vertex"

vertex:
  project_id: ""                     # SKILLS_AGENT_VERTEX_PROJECT_ID
  region: us-east5                   # SKILLS_AGENT_VERTEX_REGION
  base_url: ""                       # SKILLS_AGENT_VERTEX_BASE_URL (optional, corp proxy)

model:
  name: claude-sonnet-4-20250514     # SKILLS_AGENT_MODEL_NAME
  vertex_name: claude-sonnet-4@20250514  # SKILLS_AGENT_MODEL_VERTEX_NAME
  max_tokens: 8096                   # SKILLS_AGENT_MAX_TOKENS

agent:
  max_iterations: 20                 # SKILLS_AGENT_AGENT_MAX_ITERATIONS
  context_budget: 150000             # SKILLS_AGENT_AGENT_CONTEXT_BUDGET

tools:
  run_code_timeout: 30               # SKILLS_AGENT_TOOLS_RUN_CODE_TIMEOUT
  text_file_limit: 50000             # SKILLS_AGENT_TOOLS_TEXT_FILE_LIMIT
```

### Switching providers

**Personal machine (Anthropic direct):**
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
# provider defaults to "anthropic" — nothing else needed
```

**Work machine (Vertex AI):**
```bash
# .env
SKILLS_AGENT_PROVIDER=vertex
SKILLS_AGENT_VERTEX_PROJECT_ID=my-gcp-project
SKILLS_AGENT_VERTEX_REGION=us-east5
# Auth via Google ADC: run once → gcloud auth application-default login
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

No code changes needed — `skill_loader.py` auto-discovers it on the next run.

### Available tools (inside skills)

| Tool | Purpose |
|---|---|
| `read_file(path)` | Read any text file relative to `backend/` |
| `write_file(filename, content)` | Write to `outputs/{session_id}/` or `skills/public\|private/` |
| `run_code(filename, runtime)` | Execute a script from `outputs/{session_id}/`, runtime = `python3` or `node` |
| `list_files(directory)` | Top-level listing of `skills/`, `uploads/`, or `outputs/` |
| `scan_folder(directory, extensions?)` | Recursive scan with file metadata; optional extension filter e.g. `[".pdf", ".csv"]` |
| `analyze_file(path, question?)` | Understand any file — PDFs and images sent to Claude natively (tables, charts, scanned pages); text files returned directly. Optional `question` focuses the analysis. |

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
