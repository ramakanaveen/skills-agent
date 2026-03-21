# Skills Agent

A local AI agent where all task knowledge lives in Markdown files (`SKILL.md`), not in Python code. The Python backend is fully task-agnostic — teach it new capabilities by dropping in a new skill file.

## Stack

- **Backend**: Python + FastAPI + Anthropic SDK (`claude-sonnet-4-20250514`)
- **Frontend**: React + Vite, dark terminal aesthetic
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
│   ├── main.py                   # FastAPI routes + 20-iteration agentic loop
│   ├── context_assembler.py      # Builds system prompt from workspace/ + skills
│   ├── skill_loader.py           # Scans skills/public/ + skills/private/
│   ├── tool_executor.py          # Executes tools with path safety + session scoping
│   ├── session.py                # JSONL transcripts, load_history, list_sessions
│   ├── requirements.txt
│   ├── workspace/
│   │   ├── SOUL.md               # Agent identity
│   │   ├── AGENTS.md             # Behavioral rules
│   │   └── TOOLS.md              # Tool descriptions
│   ├── skills/
│   │   ├── public/               # Committed to git — shared with everyone
│   │   │   ├── docx/SKILL.md
│   │   │   ├── skill-creator/SKILL.md
│   │   │   ├── scripture/SKILL.md
│   │   │   └── travel-planner/SKILL.md
│   │   └── private/              # Gitignored — yours only
│   │       └── resume/SKILL.md
│   ├── outputs/{session_id}/     # Per-session generated files (gitignored)
│   ├── uploads/                  # User-uploaded files (gitignored)
│   └── sessions/                 # JSONL audit trails (gitignored)
└── frontend/
    └── src/
        ├── App.jsx               # Chat state, session management
        └── components/
            ├── ChatView.jsx      # Conversational UI with inline tool trace
            ├── ReplyBar.jsx      # Always-visible reply input, file upload
            ├── OutputPanel.jsx   # 4 tabs: Output Files, Sessions, Context, Transcript
            └── ContextInspector.jsx
```

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/upload` | Save file to `uploads/` |
| `GET` | `/api/skills` | List all skills (rescans on every call) |
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

| Tool | What it does |
|---|---|
| `read_file(path)` | Read any file relative to `backend/` |
| `write_file(filename, content)` | Write to `outputs/{session_id}/` or `skills/public\|private/` |
| `run_code(filename, runtime)` | Execute from `outputs/{session_id}/`, runtime = `python3` or `node` |
| `list_files(directory)` | List `skills/`, `uploads/`, or `outputs/` (scoped to current session) |

### The meta-skill: skill-creator

The agent can write new skills itself. When no skill matches a task, it reads `skill-creator`, asks you **"public or private?"**, then writes the new skill to the correct path. The skill is immediately available for the current and all future sessions.

## Session isolation

Every session gets its own `outputs/{session_id}/` directory. Sessions cannot see each other's output files. Skills are intentionally global — a skill created in one session is available in all others.

## What's planned

- **CI/CD pipeline**: GitHub Actions deploy workflow
- **Private skills repo**: `skills/private/` synced from a separate private GitHub repo on deploy
- **Skill sharing**: share a private skill with specific users
- **Git repo**: push to GitHub
