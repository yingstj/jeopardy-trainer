---
name: GitHub dataset fallback & Git LFS
description: How the clue CSV is served from GitHub and the LFS/encoding pitfalls
---
The clue CSV in the GitHub source repo is Git LFS-tracked (`.gitattributes`).

**Why it matters:**
- `raw.githubusercontent.com` returns only the ~3-line LFS pointer, not the CSV. Use `github.com/<owner>/<repo>/raw/<branch>/...` or `media.githubusercontent.com/media/<owner>/<repo>/<branch>/...`, which resolve LFS content.
- GitHub omits a charset header on these downloads, so `requests`' `resp.text` mis-decodes non-ASCII clues (ESPAÑOL etc.). Decode `resp.content` explicitly as UTF-8.

**How to apply:** any new remote fetch of the dataset must use an LFS-resolving URL and explicit UTF-8 decode; verify parity against the bundled CSV with a full-frame compare, not just row count.
