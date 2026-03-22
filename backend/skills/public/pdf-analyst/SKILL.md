---
name: pdf-analyst
category: utility
description: >
  Read, summarise, and extract information from PDF files. Use when the
  user uploads a PDF or references a document. Triggers on: "summarise
  this PDF", "read this document", "extract from PDF", "what does this
  report say", "analyse this paper", "read the PDF I uploaded",
  any task involving an uploaded .pdf file.
---

# PDF Analyst

## When to use
When the user uploads a PDF or asks about the contents of a document.

## Procedure
1. If filename not obvious, call scan_folder("uploads/", [".pdf"])
   to find available PDFs
2. Call analyze_file("uploads/{filename}", "summarise this document")
3. Structure the response:
   - **Overview**: 1 paragraph summary
   - **Key Points**: bullet list of main findings
   - **Important Data**: notable numbers, dates, decisions
   - **Action Items**: recommendations or next steps if present
4. If user wants a saved copy, write summary with write_file:
   filename: "pdf_summary_{original_name}_{timestamp}.md"

## Rules
- Always use analyze_file for PDFs — never read_file (returns binary)
- Use the question parameter to focus analysis:
  analyze_file("uploads/report.pdf", "What are the revenue figures?")
- For multiple PDFs, use folder-summariser skill instead
- If file is too large for the API (over ~32MB), tell the user
