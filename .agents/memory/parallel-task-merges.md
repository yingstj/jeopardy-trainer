---
name: Parallel task merges can clobber app.py
description: Verify file integrity after other tasks merge before marking a task complete
---
Rule: In this project, several tasks edit the single large `app.py`; when other tasks merge into main mid-session, the working copy can end up truncated/clobbered or hit big interstitial rebase conflicts.

**Why:** A stats-page task passed testing, then completion review found `app.py` missing the whole sidebar/game area — a merge had rewritten it. Resolution required rebuilding from `main-repl/main`'s copy and reapplying the task's edits.

**How to apply:** Before `markTaskComplete`, re-check `app.py` (line count, key markers like `with st.sidebar`). For rebase conflicts, prefer taking main's full `app.py` and reapplying the task's small additions rather than hand-merging huge hunks.
