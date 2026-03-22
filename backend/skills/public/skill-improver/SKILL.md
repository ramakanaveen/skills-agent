---
name: skill-improver
category: utility
description: >
  Review an existing skill and improve it based on what was
  learned from a recent task. Use when a skill had gaps,
  produced errors, or could work better with additional guidance.
  Triggers on: "improve this skill", "update the skill",
  "the skill didn't handle X well", "learn from this",
  "refine the skill", "remember this for next time",
  "add this rule to the skill", "the skill needs updating".
---

# Skill Improver

## When to use
After completing a task where a skill had gaps, produced errors,
or where you discovered patterns the skill should know about.

## Procedure

1. Identify which skill to improve (ask if not obvious)
2. Read the current skill:
   read_file("skills/public/{name}/SKILL.md")
   or read_file("skills/private/{name}/SKILL.md")
3. Review what happened during the task:
   - What instruction was missing that caused the problem?
   - What pattern did you discover that should be captured?
   - What error occurred and how was it resolved?
   - What would have made the task faster or more reliable?
4. Write an improved version with write_file:
   - Preserve the YAML frontmatter (name + description)
   - Add a "## Lessons Learned" section at the bottom
     if it doesn't exist, or append to it if it does
   - Add specific, actionable rules — not vague advice
   - Do not remove existing working instructions
   - Keep under 500 lines total
5. Confirm to the user: "Updated {skill_name} skill. Changes:
   [bullet list of what was added and why]"

## What makes a good improvement

GOOD (specific and actionable):
  "If the CSV has no header row, add header=['col1','col2',...]
   to pd.read_csv() based on the first row's data shape"

BAD (vague):
  "Handle CSV edge cases better"

GOOD:
  "matplotlib must use Agg backend before any plt import:
   matplotlib.use('Agg') — forgetting this causes silent hang"

BAD:
  "Be careful with matplotlib"

## Rules

- Never overwrite a skill entirely — always evolve it
- Add a comment before new rule blocks:
  "# Added {date}: {one-line reason}"
- If the improvement is large (30+ lines), consider whether
  it belongs in the skill body or as a new separate skill
- If the skill already has the rule that was broken, the
  problem is Claude not reading the skill — note that and
  suggest adding the rule in a more prominent position
- Private skills: write_file("../skills/private/{name}/SKILL.md")
- Public skills:  write_file("../skills/public/{name}/SKILL.md")
