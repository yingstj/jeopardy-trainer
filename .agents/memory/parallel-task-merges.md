---
name: Parallel task merges can clobber app.py
description: Verify app.py integrity after merges; merges can reorder/revert recent edits
---
Parallel task merges into this project can silently rearrange or revert recent edits in app.py — one merge moved a function definition below its first call site (NameError at render) and reverted call-site argument changes back to their old form.

**Why:** multiple in-flight tasks touch app.py; auto-merge picks main's arrangement and reapplies hunks imperfectly.

**How to apply:** after any merge lands mid-task (watch for MERGED notices), re-grep app.py for your key symbols: confirm defs precede first use and call-site arguments still match your intended version. Compile-check alone is insufficient (NameError at runtime still parses).
