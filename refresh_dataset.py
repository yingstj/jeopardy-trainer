#!/usr/bin/env python3
"""
Incremental Jeopardy dataset refresh.

Scans the most recent J! Archive seasons, scrapes only games that are not
already present in data/all_jeopardy_clues.csv, appends the new clues,
validates the result, optionally uploads to Cloudflare R2 (when credentials
are configured), and invalidates the local parquet cache so the app serves
fresh data.

Usage:
    python refresh_dataset.py [--seasons N] [--dry-run] [--limit N]

Options:
    --seasons N   Number of most-recent seasons to scan (default: 2)
    --limit N     Max number of new games to scrape this run (default: no limit)
    --dry-run     List missing games without scraping/appending
"""
import argparse
import csv
import os
import shutil
import sys
import time
from pathlib import Path

import scraper

# Prefer HTTPS for all requests
scraper.BASE_URL = "https://www.j-archive.com/"
scraper.SEASON_LIST_URL = scraper.BASE_URL + "listseasons.php"

CSV_PATH = Path("data/all_jeopardy_clues.csv")


def clean_parse_game(game_url):
    """
    Parse a J! Archive game page without scraper.py's destructive HTML
    preprocessing (which breaks on the current site markup). Clue text lives
    in td.clue_text[id=clue_X] and the answer in td[id=clue_X_r] em.correct_response.
    """
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(game_url, timeout=30)
    if resp.status_code != 200:
        scraper.logger.error(f"Failed to fetch {game_url}")
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    game_id = game_url.split("game_id=")[-1]
    clues = []

    for round_name, div_id in [
        ("Jeopardy", "jeopardy_round"),
        ("Double Jeopardy", "double_jeopardy_round"),
        ("Final Jeopardy", "final_jeopardy_round"),
    ]:
        round_div = soup.find("div", id=div_id)
        if not round_div:
            continue

        if round_name == "Final Jeopardy":
            cat = round_div.select_one("td.category_name")
            clue_tag = round_div.select_one("td.clue_text#clue_FJ")
            resp_tag = round_div.select_one("#clue_FJ_r em.correct_response")
            if clue_tag:
                clues.append([
                    game_id,
                    cat.get_text(strip=True) if cat else "Final Jeopardy",
                    clue_tag.get_text(strip=True),
                    resp_tag.get_text(strip=True) if resp_tag else "UNKNOWN",
                    round_name,
                ])
            continue

        categories = [c.get_text(strip=True) for c in round_div.select("td.category_name")]
        for cell_idx, cell in enumerate(round_div.select("td.clue")):
            clue_text = None
            correct = None
            for tag in cell.select("td.clue_text[id]"):
                if tag["id"].endswith("_r"):
                    em = tag.find("em", class_="correct_response")
                    if em:
                        correct = em.get_text(strip=True)
                else:
                    clue_text = tag.get_text(strip=True)
            if not clue_text:
                continue
            cat_idx = cell_idx % 6
            category = categories[cat_idx] if cat_idx < len(categories) else "Unknown"
            clues.append([
                game_id,
                category,
                clue_text,
                correct or "UNKNOWN",
                round_name,
            ])
    return clues
PARQUET_CACHE = Path("/tmp/jeopardy_clues.parquet")
RATE_LIMIT_SECONDS = 1.2


def existing_game_ids(csv_path: Path) -> set:
    ids = set()
    if not csv_path.exists():
        return ids
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if row:
                ids.add(str(row[0]))
    return ids


def find_missing_games(num_seasons: int, known_ids: set):
    """Return list of (game_id, game_url) for games not yet in the CSV."""
    seasons = scraper.extract_season_links()
    if not seasons:
        raise RuntimeError("Could not fetch season list from J! Archive")
    missing = []
    for season_url in seasons[:num_seasons]:
        scraper.logger.info(f"Scanning season: {season_url}")
        game_links = scraper.extract_game_links(season_url)
        for game_url in game_links:
            game_id = game_url.split("game_id=")[-1]
            if game_id not in known_ids:
                missing.append((game_id, game_url))
        time.sleep(RATE_LIMIT_SECONDS)
    # De-duplicate (a game could appear twice) and keep stable order
    seen = set()
    unique = []
    for gid, url in missing:
        if gid not in seen:
            seen.add(gid)
            unique.append((gid, url))
    return unique


def scrape_and_append(missing, csv_path: Path):
    total_clues = 0
    scraped_games = 0
    for i, (game_id, game_url) in enumerate(missing, 1):
        scraper.logger.info(f"[{i}/{len(missing)}] Scraping game {game_id}: {game_url}")
        try:
            clues = clean_parse_game(game_url)
        except Exception as e:
            scraper.logger.error(f"  Error parsing game {game_id}: {e}")
            clues = []
        if clues:
            scraper.append_to_csv(clues, str(csv_path))
            total_clues += len(clues)
            scraped_games += 1
        else:
            scraper.logger.warning(f"  No clues extracted for game {game_id} (may not have aired yet)")
        time.sleep(RATE_LIMIT_SECONDS)
    return scraped_games, total_clues


def upload_to_r2(csv_path: Path) -> bool:
    """Upload refreshed CSV to R2 when credentials are configured; skip gracefully otherwise."""
    endpoint = os.getenv("R2_ENDPOINT_URL")
    access_key = os.getenv("R2_ACCESS_KEY")
    secret_key = os.getenv("R2_SECRET_KEY")
    bucket = os.getenv("R2_BUCKET_NAME", "jeopardy-dataset")
    key = os.getenv("R2_FILE_KEY", "all_jeopardy_clues.csv")

    if not all([endpoint, access_key, secret_key]):
        print("R2 credentials not configured — skipping R2 upload.")
        return False
    try:
        import boto3
        from botocore.config import Config

        client = boto3.session.Session().client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name=os.getenv("R2_REGION_NAME", "auto"),
        )
        client.upload_file(str(csv_path), bucket, key)
        print(f"✅ Uploaded {csv_path} to R2 bucket '{bucket}' as '{key}'")
        return True
    except Exception as e:
        print(f"❌ R2 upload failed: {e}")
        return False


def invalidate_parquet_cache():
    if PARQUET_CACHE.exists():
        try:
            PARQUET_CACHE.unlink()
            print(f"Removed stale parquet cache: {PARQUET_CACHE}")
        except Exception as e:
            print(f"⚠️  Could not remove parquet cache: {e}")
    else:
        print("No local parquet cache present — nothing to invalidate.")


def main():
    ap = argparse.ArgumentParser(description="Incrementally refresh the Jeopardy dataset")
    ap.add_argument("--seasons", type=int, default=2, help="Most-recent seasons to scan")
    ap.add_argument("--limit", type=int, default=0, help="Max new games to scrape (0 = no limit)")
    ap.add_argument("--dry-run", action="store_true", help="List missing games without scraping")
    args = ap.parse_args()

    known = existing_game_ids(CSV_PATH)
    print(f"Existing dataset: {len(known):,} games in {CSV_PATH}")

    missing = find_missing_games(args.seasons, known)
    print(f"Found {len(missing)} games on J! Archive not present in the dataset.")

    if args.dry_run:
        for gid, url in missing:
            print(f"  {gid}\t{url}")
        return 0

    if not missing:
        print("Dataset is already up to date.")
        return 0

    if args.limit and len(missing) > args.limit:
        missing = missing[: args.limit]
        print(f"Limiting this run to {args.limit} games.")

    # Back up the CSV before appending
    backup = CSV_PATH.with_suffix(".csv.bak")
    shutil.copy2(CSV_PATH, backup)
    print(f"Backed up CSV to {backup}")

    games, clues = scrape_and_append(missing, CSV_PATH)
    print(f"✅ Appended {clues:,} clues from {games} new games.")

    # Validate; restore backup on failure
    from validate_data import validate_csv

    if not validate_csv(str(CSV_PATH)):
        print("❌ Validation failed — restoring backup.")
        shutil.copy2(backup, CSV_PATH)
        return 1
    backup.unlink(missing_ok=True)

    upload_to_r2(CSV_PATH)
    invalidate_parquet_cache()
    print("Refresh complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
