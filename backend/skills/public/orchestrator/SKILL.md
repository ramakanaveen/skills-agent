---
name: orchestrator
category: utility
description: >
  Break a complex multi-step task into subagent calls using
  spawn_agent. Use when a task has clearly separable parts that
  each need focused attention. Triggers on: "process each file",
  "for every PDF", "analyse all then summarise", "pipeline",
  "batch process", "do X for each Y", "summarise all then write
  a combined report", any task requiring the same operation
  applied repeatedly across multiple inputs.
---

# Orchestrator

## When to use
When a task has multiple distinct steps where each step is
substantial enough to warrant focused attention, OR when the
same operation must be applied to many inputs (files, URLs,
items) and reading them all into context would overflow.

## The core pattern

Orchestration = you plan → subagents execute → you synthesise.

You are the coordinator. You never do the work yourself that
a subagent should do. You decompose, delegate, collect,
synthesise.

## Step-by-step procedure

1. Understand the full task before doing anything.
2. Decompose into discrete steps. Write them out explicitly
   in your response so the user can see your plan.
3. For each step, call spawn_agent with:
   - A precise task instruction
   - The right skill for that step
   - The relevant input data (filename, text snippet, etc.)
4. Collect all results. Do NOT pass them back raw.
5. Synthesise into a single coherent output.
6. Write the final output with write_file if it is substantial.

## Example: batch PDF summarisation

User: "Summarise each PDF in uploads and write a combined brief"

Step 1: scan_folder("uploads/", [".pdf"]) — get file list
Step 2: for each PDF filename, call:
  spawn_agent(
    task="Summarise this PDF. Return: 1-paragraph overview,
          key findings as bullet points, any important numbers.",
    skill_name="pdf-analyst",
    input_data=filename,
    model="claude-haiku-4-5-20251001"
  )
Step 3: collect all summaries (each is a string result)
Step 4: synthesise into executive brief
Step 5: write_file("executive_brief.md", combined_content)

## Example: multi-stage analysis pipeline

User: "Analyse all CSVs and write one trend report"

Step 1: scan_folder("uploads/", [".csv"])
Step 2: for each CSV:
  spawn_agent(
    task="Analyse this CSV. Return key statistics, trends,
          and notable patterns. Be concise — 3-5 bullet points.",
    skill_name="data-analyst",
    input_data=filename,
    model="claude-haiku-4-5-20251001"
  )
Step 3: synthesise findings into a trend report
Step 4: write_file("trend_report.md", report)

## When NOT to use orchestrator

- Single file tasks — just use the skill directly
- Tasks with fewer than 3 files — read them directly
- Tasks where each step heavily depends on the previous step's
  full output (sequential dependency makes spawning awkward)

## Model selection

- Haiku for subagents doing: extraction, summarisation,
  data reading, format conversion, simple Q&A over a document
- Default model for subagents doing: reasoning, writing,
  comparison across multiple sources, complex analysis

## Rules

- Always tell the user your decomposition plan before executing
- Always synthesise — never concatenate raw subagent outputs
- If a subagent returns an ERROR, note it and continue with
  the others rather than stopping the whole pipeline
- Cap batches at 10 subagent calls per orchestrator run to
  stay within the iteration limit
