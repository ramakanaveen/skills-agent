# Skills Agent — Claude Context

This file gives Claude Code full context on the project so it can assist
effectively without needing to re-explore the codebase each session.

> **Maintenance rule:** After any code change that affects architecture,
> tools, components, config keys, UI layout, or provider behaviour — update
> this file in the same commit. Treat CLAUDE.md as a living document, not
> an afterthought.

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

5. **Provider switching is config-only.** `cfg.provider` is either `"anthropic"`
   or `"vertex"`. `main.py` initialises `_provider` once at startup. Call
   `_provider.get_client()` and `_provider.model_name` at the start of each
   agent run — never construct the client inline. To add custom Vertex auth
   (e.g. internal token service), override `_get_token()` in `VertexProvider`;
   the client rebuilds automatically when the token changes.

6. **New tools require one place:** add a handler function and call
   `registry.register(name, handler, schema)` at the bottom of
   `tool_executor.py`. The registry feeds `context_assembler.build_tools()`
   automatically — no changes to `context_assembler.py` needed.
   MCP tools follow the same pattern: `mcp_manager.py` calls
   `registry.register()` at startup for each discovered server tool.

7. **Frontend config is centralised.** All API endpoint strings and UI
   constants live in `frontend/src/config.js`. Never hardcode `/api/...`
   in components.

8. **Markdown rendering uses remark-gfm.** All `<ReactMarkdown>` calls must
   include `remarkPlugins={[remarkGfm]}` to render tables correctly.

---

## Project layout

```
skills-agent/
├── backend/
│   ├── main.py                 # FastAPI app, SSE agentic loop, lifespan startup/shutdown
│   ├── tool_registry.py        # ToolRegistry singleton — register(), execute(), schemas()
│   ├── tool_executor.py        # Built-in tool handlers + registration; execute_tool() wrapper
│   ├── mcp_manager.py          # MCP client (stdio + HTTP); connects servers at startup
│   ├── context_assembler.py    # build_system_prompt(), build_tools() → registry.schemas()
│   ├── skill_loader.py         # scan() — reads both public/ and private/
│   ├── session.py              # save_turn(), load_history(), list_sessions()
│   ├── config.yaml             # All tunable values (config, not secrets)
│   ├── config.py               # cfg object — import this everywhere
│   ├── requirements.txt
│   ├── providers/
│   │   ├── anthropic_provider.py  # Wraps anthropic.Anthropic; key from .env
│   │   └── vertex_provider.py     # Wraps AnthropicVertex; override _get_token()
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
│   │   │   ├── data-analyst/   # CSV/JSON analysis with matplotlib + tabulate
│   │   │   ├── orchestrator/   # Multi-step pipeline coordination via spawn_agent
│   │   │   └── skill-improver/ # Post-task skill evolution
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
        ├── App.jsx             # Root: chat state, session mgmt, SSE handler, panel resize
        ├── config.js           # API endpoints + UI constants
        ├── themes.js           # 4 themes via CSS variables + localStorage
        ├── index2.css          # Global styles
        ├── main.jsx            # Entry point
        └── components/
            ├── ChatView.jsx    # Chat bubbles, markdown + inline charts, collapsible trace
            ├── ReplyBar.jsx    # Input bar + file upload
            ├── OutputPanel.jsx # 2 tabs: Preview, Files — output-only right panel
            ├── SessionDrawer.jsx # Slide-in history drawer (search, date groups, + New)
            ├── SkillDirectory.jsx
            ├── ThemeToggle.jsx
            └── AgentTrace.jsx  # Collapsible tool call/result events
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
| `spawn_agent` | `task, skill_name, input_data?, model?` | Spin up an isolated subagent with one skill; runs its own agentic loop; returns final text. Requires `anthropic_client`. |

`analyze_file` requires `anthropic_client` to be passed into `execute_tool()`.
This is already done in `main.py`. Tests mock it with `MagicMock`.

---

## Frontend UI layout

Two panels with a draggable divider (20–80%, localStorage persisted):

- **Left panel**: Chat conversation, collapsible agent trace, inline chart images, ReplyBar pinned at bottom, session bar with ⏱ History button
- **Right panel**: 2 tabs — Preview (auto-activates on completion) + Files (with export); switches to Skill Directory when Skills nav active
- **Top nav**: `Workspace` (default chat) + `Skills` (toggles right panel to SkillDirectory, auto-returns to OutputPanel on task complete)

### Key frontend patterns

- **Markdown rendering**: Always use `<ReactMarkdown remarkPlugins={[remarkGfm]}>` — never omit `remarkGfm` or tables won't render
- **Inline images**: `ChatView.jsx` uses `makeComponents(sessionId)` to rewrite relative image src to `/api/download/{sessionId}/{filename}`
- **Preview tab**: `PreviewPanel` in `OutputPanel.jsx` — picks latest file by reverse-alpha sort, renders markdown/images, file dropdown for switching
- **Collapsible trace**: `AgentTurn` in `ChatView.jsx` — expands live during processing, auto-collapses when `turn.done === true`
- **Panel resize**: `App.jsx` uses `leftWidth` state + mouse drag handlers + `leftWidthRef` to avoid stale closure on save
- **Session drawer**: `SessionDrawer.jsx` — absolutely positioned over left panel (`position: relative` on parent), slides in via `translateX`, groups sessions by date, has search filter; triggered by ⏱ History button in session bar

---

## How to add a new tool

1. Add a handler function `_handle_my_tool(input_data, **ctx)` in `tool_executor.py`
   - Use `resolve_safe_path()` for any file access
   - Use `cfg.*` for any configurable limits
   - Pull `session_id = ctx.get("session_id")` and `anthropic_client = ctx.get("anthropic_client")` as needed

2. Register it at the bottom of `tool_executor.py`:
   ```python
   registry.register("my_tool", _handle_my_tool, { ...schema dict... })
   ```
   `context_assembler.build_tools()` picks it up automatically — no changes needed there.

3. Update `backend/workspace/TOOLS.md` with the new tool description

4. Add tests in `test_tool_executor.py` following the existing class pattern

5. Add icon to `TOOL_ICONS` in `frontend/src/components/AgentTrace.jsx`

   Note: `spawn_agent` is excluded from subagent tool lists via
   `registry.schemas(exclude={"spawn_agent"})`. Never remove this — it prevents recursive spawning.

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
  max_nudges: 1                    # nudges when Claude ends turn without tool calls

tools:
  result_preview_chars: 500        # chars of tool result shown in frontend trace
  run_code_timeout: 30             # seconds before subprocess killed
  text_file_limit: 50000           # max chars returned by analyze_file for text files

server:
  cors_origins:
    - http://localhost:5173

# MCP servers — leave empty to disable. See config.yaml for full schema.
# Tools registered as "{server_name}__{tool_name}" (e.g. github__create_issue)
mcp_servers: []
# mcp_servers:
#   - name: github
#     transport: stdio            # stdio | http
#     command: "npx -y @modelcontextprotocol/server-github"
#     env:
#       GITHUB_TOKEN: "${GITHUB_TOKEN}"   # resolved from .env
#     rate_limit: 30              # max tool calls per session (default 50)
#   - name: confluence
#     transport: http
#     url: "http://confluence-mcp.internal:3000"
#     headers:
#       Authorization: "Bearer ${CONFLUENCE_TOKEN}"
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

Committed: source code, `skills/public/`, `workspace/`, tests, config, `CLAUDE.md`
Not committed: `.env`, `outputs/`, `uploads/`, `sessions/`, `skills/private/`, `node_modules/`

---

## Current branch

Working branch: `issue5-add-spawn-agent-tool`
Main is stable and merged.
