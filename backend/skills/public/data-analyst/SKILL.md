---
name: data-analyst
category: utility
description: >
  Analyse data files, generate statistics, create charts, and produce
  reports. Use when the user uploads a CSV, JSON, or Excel file and wants
  analysis, visualisation, or insights. Triggers on: "analyse this data",
  "plot", "chart", "statistics", "correlation", "trend", "visualise",
  "data analysis", "CSV", "run analysis on", "generate a report from
  this data", "what does this data show".
---

# Data Analyst

## When to use
Any task involving data analysis, visualisation, or statistical summary
of uploaded CSV, JSON, or similar files.

## Procedure

1. Discover the data file:
   - If filename is obvious from context, use it directly
   - Otherwise call scan_folder("uploads/", [".csv", ".json", ".xlsx"])

2. Write a Python analysis script to outputs/:
   - filename: "analysis_{timestamp}.py"
   - Use timestamp format: YYYYMMDD_HHMMSS

3. The script MUST follow this structure:
```python
import subprocess, sys

# Install dependencies silently if missing
subprocess.run(
    [sys.executable, "-m", "pip", "install",
     "pandas", "matplotlib", "seaborn", "tabulate", "--quiet"],
    capture_output=True
)

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # non-interactive backend — REQUIRED
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path
from datetime import datetime

# Load data — script runs from outputs/{session_id}/
# so uploads are at ../../uploads/ relative to script
data_path = Path(__file__).parent / "../../uploads/{filename}"

# Always inspect before assuming structure
df = pd.read_csv(data_path)  # or read_json, read_excel
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(df.head())
print(df.describe())

# ... analysis code ...

# Save chart — always save to same dir as script
plt.savefig(Path(__file__).parent / "chart_{timestamp}.png",
            dpi=100, bbox_inches='tight')
plt.close()

# Save text report
report = f"""# Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Dataset Overview
- Shape: {df.shape}
- Columns: {', '.join(df.columns.tolist())}

## Key Statistics

{df.describe().to_markdown()}

## Visual Analysis

![Data Visualisation](chart_{timestamp}.png)

## Insights
[key findings from the data]
"""
(Path(__file__).parent / "report_{timestamp}.md").write_text(report)
print("Done.")
```

4. Run: run_code("analysis_{timestamp}.py", "python3")

5. If exit_code != 0:
   - Read the stderr carefully
   - Fix the script (common issues: wrong path, missing column, import error)
   - Retry with fixed script — up to 3 attempts
   - Each retry: overwrite the same filename with write_file

6. Report findings to the user:
   - Summarise key statistics from stdout
   - Mention output files produced
   - Include `![Chart Description](chart_{timestamp}.png)` in the markdown report at the relevant section
   - In the chat response, include the same image reference so charts appear inline in the conversation
   - The image filename used in the markdown MUST exactly match the PNG file that was saved

## Output files (all in outputs/{session_id}/)
- analysis_{timestamp}.py  — the script
- report_{timestamp}.md    — text summary
- chart_{timestamp}.png    — chart (if visualisation was requested)

## Critical rules
- matplotlib MUST use Agg backend: matplotlib.use('Agg') BEFORE import pyplot
- File paths in the script: use Path(__file__).parent to anchor paths
  The script runs from outputs/{session_id}/ so uploads are at ../../uploads/
- Always call print() for results — run_code captures stdout
- Never use plt.show() — it will hang. Always plt.savefig() then plt.close()
- Install pandas/matplotlib inside the script — do not assume they are present
- If data has many columns, focus analysis on numeric columns first
