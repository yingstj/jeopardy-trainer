---
name: J! Archive scraping
description: Pitfalls when scraping j-archive.com game pages for the clue dataset
---
- The legacy scraper's `preprocess_html` (replacing every `</div>` with `</td>`) corrupts the DOM on current J! Archive markup, yielding exactly 3 bogus clues per game (one repeated clue per round). Never reuse that preprocessing.
- **Why:** The site now wraps each clue in `<div onmouseover="toggle(...)">`; blanket div→td rewriting breaks nesting.
- **How to apply:** Parse raw HTML: clue text in `td.clue_text[id=clue_X]`, answer in `td[id=clue_X_r] em.correct_response`, Final Jeopardy in `#clue_FJ` / `#clue_FJ_r`. Category index for a `td.clue` cell is `cell_index % 6` (row-major). Use `python refresh_dataset.py` for incremental refreshes (idempotent, validates, backs up CSV, optional R2 upload, clears /tmp parquet cache).
- Sanity check after any scrape: every game should have ~61 clues (30+30+1); uniform tiny counts mean the parser broke.

## Air dates
Season list pages (showseason.php) link every game with text like "#9385, aired 2025-07-25" — one request per season yields a full game_id→air_date map, so backfilling dates for the whole dataset takes ~1 min instead of one request per game. `\s` must match `\xa0` (nbsp) in the "aired" text; Python str regex does this by default.
