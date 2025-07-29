
import requests
from bs4 import BeautifulSoup
import csv
import time
import os
import re

BASE_URL = "http://www.j-archive.com/"
SEASON_LIST_URL = BASE_URL + "listseasons.php"
OUTPUT_FILE = "data/all_jeopardy_clues.csv"

def preprocess_html(raw_html):
    raw_html = re.sub(r'onmouseover=".*?"', '', raw_html)
    raw_html = re.sub(r'onmouseout=".*?"', '', raw_html)
    raw_html = raw_html.replace('class="search_correct_response">', '<td>')
    return raw_html

def get_soup(url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch {url}")
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

    rounds = {
        "Jeopardy": soup.find("div", id="jeopardy_round"),
        "Double Jeopardy": soup.find("div", id="double_jeopardy_round"),
        "Final Jeopardy": soup.find("div", id="final_jeopardy_round"),
    }

    for round_name, round_div in rounds.items():
        if not round_div:
            continue

        categories = [cat.get_text() for cat in round_div.select("td.category_name")]
        clue_cells = round_div.select("td.clue")

        for i, cell in enumerate(clue_cells):
            clue_text_tag = cell.select_one("td.clue_text")
            if not clue_text_tag:
                continue
            clue_text = clue_text_tag.get_text().strip()

            correct_response_tag = cell.select_one("td")
            answer = correct_response_tag.get_text().strip() if correct_response_tag else "UNKNOWN"

            category_index = i // 5 if round_name != "Final Jeopardy" else 0
            category = categories[category_index] if category_index < len(categories) else "Unknown"

            clues.append([
                game_id,
                category,
                clue_text,
                answer,
                round_name
            ])

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
    print(f"Found {len(seasons)} seasons.")

    for season_url in seasons:
        print(f"Processing season: {season_url}")
        game_links = extract_game_links(season_url)
        for game_url in game_links:
            print(f"  Scraping game: {game_url}")
            try:
                clues = parse_game(game_url)
                if clues:
                    append_to_csv(clues, OUTPUT_FILE)
            except Exception as e:
                print(f"    Error parsing game: {e}")
            time.sleep(1.2)

    print(f"✅ Done! All clues saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
