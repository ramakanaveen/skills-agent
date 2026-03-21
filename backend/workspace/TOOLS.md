Available tools and when to use them:

read_file(path)
  Read any file — a SKILL.md, an uploaded file, or a produced output.
  Use this FIRST before starting any task.
  Paths are relative to backend/ (e.g. skills/docx/SKILL.md)

write_file(filename, content)
  Write any content to backend/outputs/{filename}.
  Use for: code files, documents, reports, new skills.
  To create a new skill: write to skills/{name}/SKILL.md

run_code(filename, runtime)
  Execute a file from backend/outputs/.
  runtime is "node" or "python3".
  Returns: stdout, stderr, exit_code.

list_files(directory)
  List files in: skills/, uploads/, or outputs/.
  Use to discover what's available before acting.
