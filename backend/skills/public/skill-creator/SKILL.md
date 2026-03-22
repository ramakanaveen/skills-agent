---
name: skill-creator
category: utility
description: >
  Use this skill whenever no existing skill matches the user's task,
  or when asked to "create a skill", "write a skill", "add a skill for",
  or "remember how to do X". This skill teaches the agent to author
  new SKILL.md files that extend its own capabilities permanently.
---

# Skill Creator

When no existing skill covers the task at hand, use this skill to write
one before proceeding.

## Visibility — ALWAYS ask before writing

Before writing any skill, ask the user:

  "Should this skill be **public** or **private**?
   - **Public**: shared with everyone, committed to the git repo
   - **Private**: only visible to you, never committed to git"

Wait for the user's answer, then write to the correct path:
  - Public:  write_file("../skills/public/{name}/SKILL.md", content)
  - Private: write_file("../skills/private/{name}/SKILL.md", content)

## What a skill is

A skill is a folder under backend/skills/public/ or backend/skills/private/
containing a SKILL.md file. The SKILL.md has two parts:
  1. YAML frontmatter (between --- delimiters): name + description
  2. Markdown body: instructions for how to do the task

The description is critical — it is the only part that is always in
context. Write it to clearly trigger on the right user phrases.

## How to write a good SKILL.md

The body should contain:
- When to use this skill (trigger conditions)
- Step-by-step procedure using available tools
- Any critical rules or gotchas
- What output to produce and where to save it

Keep the body under 500 lines. Be specific and procedural.
Write instructions for an AI agent, not for a human.

## Format

---
name: skill-name-here
description: >
  When to use this skill. List trigger phrases explicitly.
  Be specific so the agent knows when to load it.
---

# Skill Title

## When to use
[trigger conditions]

## Procedure
[numbered steps using read_file, write_file, run_code, list_files]

## Rules
[critical constraints the agent must follow]

## Output
[what gets written to outputs/ and in what format]

## How to create a new skill

1. Understand the task — what does the user want to do repeatedly?
2. Ask: "Should this skill be **public** or **private**?"
3. Write the SKILL.md body following the format above
4. Save to the correct path:
   - Public:  write_file("../skills/public/{name}/SKILL.md", content)
   - Private: write_file("../skills/private/{name}/SKILL.md", content)
5. Confirm: "I've created the {name} skill as {public/private}."
6. Immediately use the new skill to complete the current task —
   read it back with read_file, then proceed

## Example — if user says "help me write a resume"

No resume skill exists yet. Use skill-creator:
1. Read skill-creator skill (done)
2. Ask: "Should the resume skill be public or private?"
3. User replies: "private"
4. Write backend/skills/private/resume/SKILL.md with resume procedure
5. Confirm creation
6. Read the new skill back
7. Help the user with their resume using the new skill
