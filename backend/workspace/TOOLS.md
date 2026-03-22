Available tools and when to use them:

read_file(path)
  Read any file — a SKILL.md, an uploaded file, or a produced output.
  Use this FIRST before starting any task.
  Paths are relative to backend/ e.g. skills/public/docx/SKILL.md

write_file(filename, content)
  Write content to a file.
  Regular output files go to outputs/{session_id}/{filename}.
  New public skills: use filename "../skills/public/{name}/SKILL.md"
  New private skills: use filename "../skills/private/{name}/SKILL.md"
  ALWAYS ask the user public or private before creating a skill.

run_code(filename, runtime)
  Execute a file from outputs/{session_id}/.
  runtime is "node" or "python3".
  Returns: stdout, stderr, exit_code.
  If exit_code != 0, fix the error and retry.

list_files(directory)
  List files in a directory (not recursive, top level only).
  Use scan_folder for recursive listing with metadata.
  Allowed: skills/public/, skills/private/, uploads/, outputs/

scan_folder(directory, extensions)
  Recursively scan a folder and list all files with metadata.
  Use BEFORE batch processing to discover what files are available.
  extensions is optional e.g. [".pdf", ".csv"]
  Allowed: uploads/, outputs/, skills/public/, skills/private/

analyze_file(path, question)
  Read and understand any file — PDF, image, or plain text.
  PDFs and images are sent to Claude natively — tables, charts,
  and scanned pages all work correctly.
  Plain text files returned directly without extra API call.
  question is optional — use it to ask something specific.
  Supported: PDF, PNG, JPG, WEBP, GIF, TXT, MD, CSV, JSON,
             PY, JS, TS, YAML, HTML, CSS, XML
  Path relative to backend/ e.g. "uploads/report.pdf"
