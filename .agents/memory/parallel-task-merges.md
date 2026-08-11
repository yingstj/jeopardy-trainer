---
name: Parallel task merges can clobber app.py
description: Rebases/merges in this project have silently dropped whole blocks from app.py; verify integrity before completing a task.
---

Rebasing a task branch onto main (especially when several tasks merge in parallel) has more than once silently deleted large blocks from `app.py` — e.g. the `auth = AuthManager()` + session-state initialization block — even when no conflict was shown for that region.

**Why:** the auto-merge tool resolves structural conflicts at function granularity and can drop interstitial top-level code between functions.

**How to apply:** after any rebase/merge and before `markTaskComplete`, diff `app.py` against `main-repl/main` and confirm nothing was removed that the task didn't intend to remove; restore missing blocks from main's copy. A completion review that fails with `AttributeError: st.session_state has no attribute ...` is a symptom of this.
