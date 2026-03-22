---
name: folder-summariser
category: utility
description: >
  Scan a folder and summarise all files found in it. Use when the user
  wants to process multiple files at once or get an overview of uploaded
  content. Triggers on: "summarise everything in", "what's in this folder",
  "go through all files", "summarise all documents", "process all files",
  "read everything in uploads", "give me an overview of all uploaded files",
  "what did I upload".
---

# Folder Summariser

## When to use
When the user wants a summary or inventory of all files in a directory,
or wants every file in a folder processed in one go.

## Procedure
1. Call scan_folder("uploads/") to discover available files
   - Add extensions filter if user mentions specific types
   - e.g. scan_folder("uploads/", [".pdf", ".txt"])
2. For each file found, process by type:
   - .txt or .md  → read_file(path) then summarise in 2-3 sentences
   - .pdf         → analyze_file(path, 'summarise this document') then summarise in 2-3 sentences
   - .csv or .json → read_file(path), describe structure and key contents
   - .py or .js   → read_file(path), describe what the code does
   - other binary → note name + size, skip reading
3. Compile a master summary:
   - Header: total file count and type breakdown
   - One section per file: filename, type, 2-3 sentence summary
   - Footer: any patterns, themes, or relationships across files
4. Save with write_file:
   - filename: "folder_summary_{timestamp}.md"
   - Use timestamp format: YYYYMMDD_HHMMSS
5. Confirm to user: files processed, summary saved, offer deeper dive

## Rules
- Process one file at a time — never attempt to read multiple at once
- If a file errors or is unreadable, note it and move on gracefully
- Keep individual summaries to 2-3 sentences unless user asks for more
- If folder has 10+ files, warn the user it may take a moment
