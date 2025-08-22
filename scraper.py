# scripts/scraper.py

import requests
from bs4 import BeautifulSoup
import csv
import time
import os
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://www.j-archive.com/"
SEASON_LIST_URL = BASE_URL + "listseasons.php"
OUTPUT_FILE = "data/all_jeopardy_clues.csv"

def preprocess_html(raw_html):
    """Enhanced preprocessing to handle various answer storage formats"""
    # First, preserve the mouseover content before removing it
    # This helps with answer extraction later
    preserved_html = raw_html
    
    # Remove onmouseout events (these don't contain answers)
    raw_html = re.sub(r'onmouseout=".*?"', '', raw_html)
    
    # Replace various forms of correct response classes
    # Convert div tags with search_correct_response to simple td tags
    raw_html = re.sub(r'<div class=["\']?search_correct_response["\']?>', '<td>', raw_html)
    raw_html = raw_html.replace('</div>', '</td>')
    
    # Also handle cases where it's just a class attribute
    raw_html = raw_html.replace('class="search_correct_response">', '<td>')
    raw_html = raw_html.replace("class='search_correct_response'>", '<td>')
    raw_html = raw_html.replace('class=search_correct_response>', '<td>')
    
    # Normalize correct_response class attributes
    raw_html = raw_html.replace("class='correct_response'", 'class="correct_response"')
    
    return raw_html

def extract_answer_from_mouseover(cell_html):
    """
    Enhanced method to extract answers from various HTML formats.
    Tries multiple regex patterns and fallback methods.
    """
    if not cell_html:
        return None
    
    # Convert BeautifulSoup object to string if needed
    if hasattr(cell_html, 'prettify'):
        cell_html = str(cell_html)
    
    # Multiple regex patterns to catch different ways answers are stored
    patterns = [
        # Pattern for mouseover with stuck function - more specific
        r'''stuck\s*\([^)]*,\s*[^)]*,\s*['"]([^'"]+)['"]''',
        # Pattern for toggle function in mouseover
        r'''toggle\s*\([^)]*,\s*[^)]*,\s*['"]([^'"]+)['"]''',
        # Pattern for correct_response in various formats
        r'<em class=["\']?correct_response["\']?>(.+?)</em>',
        # Pattern for search_correct_response that might remain after preprocessing
        r'<div class=["\']?search_correct_response["\']?>(.+?)</div>',
        # Pattern for td elements that might contain answers (but not class attributes)
        r'<td>([^<]+)</td>',
        # Pattern for any onmouseover with quoted text
        r'onmouseover=["\'][^"\']*["\'][^>]*>([^<]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cell_html, re.IGNORECASE | re.DOTALL)
        if match:
            answer = match.group(1).strip()
            
            # Skip if this looks like an attribute value, not actual content
            if answer in ['clue', 'correct_response', 'search_correct_response']:
                continue
                
            # Clean up common HTML entities
            answer = answer.replace('&amp;', '&')
            answer = answer.replace('&lt;', '<')
            answer = answer.replace('&gt;', '>')
            answer = answer.replace('&quot;', '"')
            answer = answer.replace('&#39;', "'")
            answer = answer.replace('<i>', '').replace('</i>', '')
            answer = answer.replace('<em>', '').replace('</em>', '')
            
            if answer and answer != "UNKNOWN" and len(answer) > 1:
                return answer
    
    return None

def get_soup(url):
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"Failed to fetch {url}")
        return None
    clean_html = preprocess_html(response.text)
    return BeautifulSoup(clean_html, "html.parser")

def extract_game_links(season_url):
    soup = get_soup(season_url)
    if not soup:
        return []
    return [BASE_URL + a["href"] for a in soup.select("td a") if "showgame.php" in a["href"]]

def extract_season_links():
    soup = get_soup(SEASON_LIST_URL)
    if not soup:
        return []
    return [BASE_URL + a["href"] for a in soup.select("a") if "showseason.php" in a["href"]]

def parse_game(game_url):
    soup = get_soup(game_url)
    if not soup:
        return []

    game_id = game_url.split("game_id=")[-1]
    clues = []
    missing_answers_count = 0

    rounds = {
        "Jeopardy": soup.find("div", id="jeopardy_round"),
        "Double Jeopardy": soup.find("div", id="double_jeopardy_round"),
        "Final Jeopardy": soup.find("div", id="final_jeopardy_round"),
    }

    for round_name, round_div in rounds.items():
        if not round_div:
            continue

        if round_name == "Final Jeopardy":
            # Final Jeopardy has a different structure
            category = round_div.select_one("td.category_name")
            category_text = category.get_text(strip=True) if category else "Final Jeopardy"
            
            clue_text_tag = round_div.select_one("td.clue_text")
            if not clue_text_tag:
                continue
            clue_text = clue_text_tag.get_text(strip=True)
            
            # Extract answer for Final Jeopardy
            correct_response = None
            correct_response_tag = round_div.find("em", class_="correct_response")
            if correct_response_tag:
                correct_response = correct_response_tag.get_text(strip=True)
            
            if not correct_response:
                correct_response = extract_answer_from_mouseover(str(round_div))
            
            if not correct_response:
                correct_response = "UNKNOWN"
                missing_answers_count += 1
                logger.warning(f"Missing answer for Final Jeopardy in game {game_id}: {clue_text[:50]}...")
            
            clues.append([
                game_id,
                category_text,
                clue_text,
                correct_response,
                round_name
            ])
            continue

        # Regular rounds (Jeopardy and Double Jeopardy)
        categories = [cat.get_text(strip=True) for cat in round_div.select("td.category_name")]
        clue_cells = round_div.select("td.clue")

        for i, cell in enumerate(clue_cells):
            # Look for clue text with the regular ID pattern (not the _r response version)
            clue_text_tags = cell.select("td.clue_text[id]")
            clue_text = None
            correct_response = None
            
            for tag in clue_text_tags:
                tag_id = tag.get('id', '')
                if not tag_id.endswith('_r'):  # This is the clue
                    clue_text = tag.get_text(strip=True)
                else:  # This is the response
                    response_em = tag.find("em", class_="correct_response")
                    if response_em:
                        correct_response = response_em.get_text(strip=True)
            
            if not clue_text:
                continue
            
            # If we didn't get the answer from the _r tag, try other methods
            if not correct_response:
                # Try extracting from mouseover
                correct_response = extract_answer_from_mouseover(str(cell))
            
            # Final fallback
            if not correct_response:
                correct_response = "UNKNOWN"
                missing_answers_count += 1
                logger.warning(f"Missing answer for clue in game {game_id}, round {round_name}: {clue_text[:50]}...")

            category_index = i // 5 if round_name != "Final Jeopardy" else 0
            category = categories[category_index] if category_index < len(categories) else "Unknown"

            clues.append([
                game_id,
                category,
                clue_text,
                correct_response,
                round_name
            ])
    
    if missing_answers_count > 0:
        logger.info(f"Game {game_id}: Found {len(clues)} clues, {missing_answers_count} with missing answers")
    
    return clues

def write_header(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["game_id", "category", "clue", "correct_response", "round"])

def append_to_csv(clues, filepath):
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(clues)

def main():
    write_header(OUTPUT_FILE)
    seasons = extract_season_links()
    logger.info(f"Found {len(seasons)} seasons.")
    
    total_clues = 0
    total_missing = 0
    games_with_missing = []

    for season_url in seasons:
        logger.info(f"Processing season: {season_url}")
        game_links = extract_game_links(season_url)
        for game_url in game_links:
            logger.info(f"  Scraping game: {game_url}")
            try:
                clues = parse_game(game_url)
                if clues:
                    append_to_csv(clues, OUTPUT_FILE)
                    total_clues += len(clues)
                    
                    # Count missing answers
                    missing_in_game = sum(1 for clue in clues if clue[3] == "UNKNOWN")
                    if missing_in_game > 0:
                        total_missing += missing_in_game
                        games_with_missing.append((game_url.split("game_id=")[-1], missing_in_game))
                        
            except Exception as e:
                logger.error(f"    Error parsing game: {e}")
            time.sleep(1.2)

    logger.info(f"✅ Done! All clues saved to {OUTPUT_FILE}")
    logger.info(f"Total clues scraped: {total_clues}")
    logger.info(f"Total missing answers: {total_missing} ({(total_missing/total_clues*100):.2f}%)" if total_clues > 0 else "Total missing answers: 0")
    
    if games_with_missing:
        logger.info(f"Games with missing answers: {len(games_with_missing)}")
        # Log top 10 games with most missing answers
        games_with_missing.sort(key=lambda x: x[1], reverse=True)
        logger.info("Top games with missing answers:")
        for game_id, count in games_with_missing[:10]:
            logger.info(f"  Game {game_id}: {count} missing answers")

if __name__ == "__main__":
    main()