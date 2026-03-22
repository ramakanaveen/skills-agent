---
name: docx
category: creation
description: >
  Use this skill when the user asks to create a Word document, .docx file,
  report, project status report, proposal, or any formatted document output.
  Triggers on: "write a report", "create a document", "make a .docx",
  "project status", "word document", "generate a report".
---

# DOCX Document Generator

Use this skill to create Word documents (.docx) using Node.js and the docx npm package.

## When to use
- User wants a Word document, report, proposal, or formatted document
- Any request for a .docx output file
- Project status reports, milestone tables, summaries

## Procedure

1. Read this skill file first (already done)
2. Write a Node.js script to outputs/ that uses the docx package
3. Run the script with run_code(filename, "node")
4. If it fails with "Cannot find module 'docx'", run: write a package setup script first
5. Report the output file location to the user

## The docx package API

```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, AlignmentType, WidthType } = require('docx');
const fs = require('fs');
const path = require('path');

const doc = new Document({
  sections: [{
    properties: {},
    children: [
      new Paragraph({
        text: "Title Here",
        heading: HeadingLevel.HEADING_1,
      }),
      new Paragraph({
        children: [
          new TextRun("Regular text. "),
          new TextRun({ text: "Bold text.", bold: true }),
        ],
      }),
    ],
  }],
});

const buffer = await Packer.toBuffer(doc);
fs.writeFileSync(path.join(__dirname, 'output.docx'), buffer);
console.log('Document written: output.docx');
```

## Creating a table

```javascript
new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  rows: [
    new TableRow({
      children: [
        new TableCell({ children: [new Paragraph("Header 1")] }),
        new TableCell({ children: [new Paragraph("Header 2")] }),
      ],
    }),
    new TableRow({
      children: [
        new TableCell({ children: [new Paragraph("Row 1 Col 1")] }),
        new TableCell({ children: [new Paragraph("Row 1 Col 2")] }),
      ],
    }),
  ],
})
```

## Rules
- Always use async/await with Packer.toBuffer()
- Save output to the same directory as the script (__dirname)
- Name output files descriptively with timestamp: `report_${Date.now()}.docx`
- If docx package missing, the script should install it first or note the error

## Setup for docx package

If the docx package is not installed, write a setup script:
```javascript
const { execSync } = require('child_process');
execSync('npm install docx', { cwd: __dirname, stdio: 'inherit' });
console.log('docx installed');
```
Run it first, then run the main script.

## Output
- A .docx file written to backend/outputs/
- Tell the user the filename so they can download it
