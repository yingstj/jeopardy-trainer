import requests
from bs4 import BeautifulSoup
import csv
import time
import os
import re
import json

BASE_URL = "http://www.j-archive.com/"
SEASON_LIST_URL = BASE_URL + "listseasons.php"
OUTPUT_FILE = "data/jeopardy_with_answers.csv"

def get_soup(url):
    """Fetch and parse a webpage."""
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch {url}")
        return None
    return BeautifulSoup(response.text, "html.parser")

def extract_answer_from_onmouseover(onmouseover_text):
    """Extract the answer from the onmouseover attribute."""
    if not onmouseover_text:
        return "UNKNOWN"
    
    # Look for the answer in the onmouseover text
    # Pattern: stuck('ID', 'CLUE_TEXT', 'ANSWER')
    match = re.search(r"stuck\([^,]+,[^,]+,\s*'([^']+)'", onmouseover_text)
    if match:
        answer = match.group(1)
        # Clean up HTML entities
        answer = answer.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        answer = answer.replace('\\', '').replace("&quot;", '"')
        # Remove any <i> or </i> tags
        answer = re.sub(r'</?i>', '', answer)
        return answer.strip()
    
    return "UNKNOWN"

def parse_game(game_url):
    """Parse a single game and extract all clues with answers."""
    soup = get_soup(game_url)
    if not soup:
        return []

    game_id = game_url.split("game_id=")[-1]
    clues = []

    # Parse regular rounds
    for round_name, round_id in [("Jeopardy", "jeopardy_round"), ("Double Jeopardy", "double_jeopardy_round")]:
        round_div = soup.find("div", id=round_id)
        if not round_div:
            continue

        # Get categories
        categories = [cat.get_text().strip() for cat in round_div.select("td.category_name")]
        
        # Get all clue cells
        clue_cells = round_div.select("td.clue")
        
        for i, cell in enumerate(clue_cells):
            # Get clue text
            clue_text_div = cell.select_one("td.clue_text")
            if not clue_text_div:
                continue
                
            clue_text = clue_text_div.get_text().strip()
            
            # Get dollar value
            value_div = cell.select_one("td.clue_value") or cell.select_one("td.clue_value_daily_double")
            if value_div:
                value_text = value_div.get_text().strip()
                try:
                    value = int(value_text.replace('$', '').replace(',', ''))
                except:
                    value = 0
            else:
                # Try to determine from position (row-based values)
                row = i // 5
                value = (row + 1) * (200 if round_name == "Jeopardy" else 400)
            
            # Get answer from onmouseover
            onmouseover = cell.get('onmouseover', '')
            answer = extract_answer_from_onmouseover(onmouseover)
            
            # Get category
            category_index = i % 6
            category = categories[category_index] if category_index < len(categories) else "Unknown"
            
            clues.append({
                'game_id': game_id,
                'category': category,
                'clue': clue_text,
                'answer': answer,
                'value': value,
                'round': round_name
            })

    # Parse Final Jeopardy
    final_div = soup.find("div", id="final_jeopardy_round")
    if final_div:
        category_div = final_div.select_one("td.category_name")
        category = category_div.get_text().strip() if category_div else "Final Jeopardy"
        
        clue_div = final_div.select_one("td.clue_text")
        if clue_div:
            clue_text = clue_div.get_text().strip()
            
            # Get answer - Final Jeopardy answer is often in a different format
            answer_div = final_div.find("div", onmouseover=True)
            if answer_div:
                answer = extract_answer_from_onmouseover(answer_div.get('onmouseover', ''))
            else:
                # Try alternate method
                correct_div = final_div.select_one("em.correct_response")
                answer = correct_div.get_text().strip() if correct_div else "UNKNOWN"
            
            clues.append({
                'game_id': game_id,
                'category': category,
                'clue': clue_text,
                'answer': answer,
                'value': 0,  # Final Jeopardy doesn't have a fixed value
                'round': 'Final Jeopardy'
            })

    return clues

def scrape_sample_games(num_games=5):
    """Scrape a small sample of games to test."""
    print(f"Scraping {num_games} sample games...")
    
    # Get recent games
    soup = get_soup(BASE_URL + "showseason.php?season=40")  # Season 40
    if not soup:
        print("Failed to get season page")
        return
    
    game_links = [BASE_URL + a["href"] for a in soup.select("td a") if "showgame.php" in a.get("href", "")][:num_games]
    
    all_clues = []
    for i, game_url in enumerate(game_links):
        print(f"Scraping game {i+1}/{num_games}: {game_url}")
        clues = parse_game(game_url)
        all_clues.extend(clues)
        time.sleep(1)  # Be polite to the server
    
    # Save to JSON for easy viewing
    with open('data/sample_questions_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(all_clues, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(all_clues)} clues to data/sample_questions_fixed.json")
    
    # Also save as CSV
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        if all_clues:
            writer = csv.DictWriter(f, fieldnames=all_clues[0].keys())
            writer.writeheader()
            writer.writerows(all_clues)
    
    print(f"Also saved to {OUTPUT_FILE}")
    
    # Show some examples
    print("\nSample questions with answers:")
    for clue in all_clues[:5]:
        print(f"\nCategory: {clue['category']}")
        print(f"Question: {clue['clue'][:100]}...")
        print(f"Answer: {clue['answer']}")
        print(f"Value: ${clue['value']}")

if __name__ == "__main__":
    scrape_sample_games(5)  # Scrape 5 games as a test