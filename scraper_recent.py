#!/usr/bin/env python3
"""Scrape recent seasons of J-Archive data"""

import sys
sys.path.append('.')
from scraper_v2 import *

def scrape_recent_seasons(num_seasons=5):
    """Scrape the most recent seasons"""
    write_header(OUTPUT_FILE)
    seasons = extract_season_links()
    
    if not seasons:
        logger.error("No seasons found")
        return
    
    logger.info(f"Found {len(seasons)} seasons total, scraping first {num_seasons}")
    
    total_clues = 0
    total_games = 0
    
    for i, season_url in enumerate(seasons[:num_seasons], 1):
        logger.info(f"Processing season {i}/{num_seasons}: {season_url}")
        game_links = extract_game_links(season_url)
        logger.info(f"  Found {len(game_links)} games in this season")
        
        for j, game_url in enumerate(game_links, 1):
            logger.info(f"  Game {j}/{len(game_links)}: {game_url}")
            try:
                clues = parse_game(game_url)
                if clues:
                    append_to_csv(clues, OUTPUT_FILE)
                    total_clues += len(clues)
                    total_games += 1
                    logger.info(f"    Extracted {len(clues)} clues")
            except Exception as e:
                logger.error(f"    Error: {e}")
            
            time.sleep(1.2)  # Be polite to the server
    
    logger.info(f"✅ Done! Scraped {total_clues} clues from {total_games} games")
    logger.info(f"Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    # Scrape 5 most recent seasons
    scrape_recent_seasons(5)