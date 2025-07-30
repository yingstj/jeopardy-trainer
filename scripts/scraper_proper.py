import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import os
import re

BASE_URL = "http://www.j-archive.com/"

def get_soup(url):
    """Fetch and parse a webpage without preprocessing."""
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch {url}")
        return None
    # Parse HTML without removing onmouseover attributes
    return BeautifulSoup(response.text, "html.parser")

def extract_answer(clue_div):
    """Extract answer from a clue div by checking multiple possible locations."""
    # Method 1: Look for onmouseover attribute
    onmouseover = clue_div.get('onmouseover', '')
    if onmouseover:
        # The answer is typically in the format: stuck('clue_id', 'clue_text', 'ANSWER')
        match = re.search(r"stuck\([^,]+,[^,]+,\s*'([^']*)'", onmouseover)
        if match:
            answer = match.group(1)
            # Clean HTML entities
            answer = answer.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
            answer = answer.replace('\\', '').replace("&quot;", '"').replace("&#39;", "'")
            answer = re.sub(r'</?i>', '', answer)  # Remove italic tags
            return answer.strip()
    
    # Method 2: Look for the answer in a div with class correct_response
    parent = clue_div.parent
    if parent:
        # Check siblings and children
        answer_div = parent.find('em', class_='correct_response')
        if not answer_div:
            answer_div = parent.find('div', class_='correct_response')
        if answer_div:
            return answer_div.get_text().strip()
    
    # Method 3: Check if answer is in the onmouseover of parent
    if parent and parent.get('onmouseover'):
        return extract_answer(parent)
    
    return None

def parse_game(game_url):
    """Parse a single game and extract all clues with answers."""
    soup = get_soup(game_url)
    if not soup:
        return []

    game_id = game_url.split("game_id=")[-1]
    clues = []
    
    # Show number and air date
    title_div = soup.find('div', id='game_title')
    show_info = {}
    if title_div:
        show_text = title_div.get_text()
        # Extract show number
        show_match = re.search(r'#(\d+)', show_text)
        show_info['show_number'] = show_match.group(1) if show_match else ''
        # Extract air date
        date_match = re.search(r'- (\w+, \w+ \d+, \d+)', show_text)
        show_info['air_date'] = date_match.group(1) if date_match else ''

    # Parse Jeopardy and Double Jeopardy rounds
    for round_name, round_id in [("Jeopardy!", "jeopardy_round"), ("Double Jeopardy!", "double_jeopardy_round")]:
        round_div = soup.find("div", id=round_id)
        if not round_div:
            continue

        # Get categories
        categories = []
        category_divs = round_div.find_all("td", class_="category_name")
        for cat_div in category_divs:
            categories.append(cat_div.get_text().strip())

        # Process each clue
        clue_divs = round_div.find_all("td", class_="clue")
        
        for i, clue_div in enumerate(clue_divs):
            # Get clue text
            clue_text_div = clue_div.find("td", class_="clue_text")
            if not clue_text_div:
                continue
                
            clue_text = clue_text_div.get_text().strip()
            
            # Get answer
            answer = extract_answer(clue_div)
            if not answer:
                # Try looking in the table cell directly
                answer_match = re.search(r'correct_response">([^<]+)<', str(clue_div))
                if answer_match:
                    answer = answer_match.group(1).strip()
                else:
                    answer = "UNKNOWN"
            
            # Get value
            value_div = clue_div.find("td", class_=["clue_value", "clue_value_daily_double"])
            if value_div:
                value_text = value_div.get_text().strip()
                # Handle Daily Double
                if "DD:" in value_text:
                    value_text = value_text.replace("DD:", "").strip()
                try:
                    value = int(value_text.replace('$', '').replace(',', ''))
                except:
                    # Estimate based on position
                    row = i // 6
                    value = (row + 1) * (200 if round_name == "Jeopardy!" else 400)
            else:
                # Estimate based on position
                row = i // 6
                value = (row + 1) * (200 if round_name == "Jeopardy!" else 400)
            
            # Get category (6 categories per round)
            category_index = i % 6
            category = categories[category_index] if category_index < len(categories) else "Unknown"
            
            clue_data = {
                'game_id': game_id,
                'show_number': show_info.get('show_number', ''),
                'air_date': show_info.get('air_date', ''),
                'category': category,
                'question': clue_text,
                'answer': answer,
                'value': value,
                'round': round_name
            }
            
            clues.append(clue_data)

    # Parse Final Jeopardy
    final_div = soup.find("div", id="final_jeopardy_round")
    if final_div:
        category_div = final_div.find("td", class_="category_name")
        category = category_div.get_text().strip() if category_div else "FINAL JEOPARDY"
        
        clue_div = final_div.find("td", class_="clue_text")
        if clue_div:
            clue_text = clue_div.get_text().strip()
            
            # Final Jeopardy answer is often in a different location
            answer = None
            # Check parent table
            final_table = final_div.find("table", class_="final_round")
            if final_table:
                answer_match = re.search(r'correct_response">([^<]+)<', str(final_table))
                if answer_match:
                    answer = answer_match.group(1).strip()
                else:
                    # Try onmouseover
                    answer = extract_answer(final_table)
            
            if not answer:
                answer = "UNKNOWN"
            
            clue_data = {
                'game_id': game_id,
                'show_number': show_info.get('show_number', ''),
                'air_date': show_info.get('air_date', ''),
                'category': category,
                'question': clue_text,
                'answer': answer,
                'value': 0,  # Final Jeopardy has no fixed value
                'round': 'Final Jeopardy!'
            }
            
            clues.append(clue_data)

    return clues

def test_scraper():
    """Test the scraper on a few games."""
    print("Testing scraper on sample games...")
    
    # Test on a specific game
    test_url = "http://www.j-archive.com/showgame.php?game_id=8998"
    print(f"\nTesting on: {test_url}")
    
    clues = parse_game(test_url)
    
    # Save results
    os.makedirs('data', exist_ok=True)
    
    with open('data/test_questions.json', 'w', encoding='utf-8') as f:
        json.dump(clues, f, indent=2, ensure_ascii=False)
    
    print(f"\nScraped {len(clues)} clues")
    print("\nFirst 5 clues:")
    for i, clue in enumerate(clues[:5]):
        print(f"\n{i+1}. Category: {clue['category']}")
        print(f"   Question: {clue['question'][:80]}...")
        print(f"   Answer: {clue['answer']}")
        print(f"   Value: ${clue['value']}")
    
    # Count how many have proper answers
    answered = sum(1 for c in clues if c['answer'] != 'UNKNOWN' and c['answer'])
    print(f"\nClues with answers: {answered}/{len(clues)} ({answered/len(clues)*100:.1f}%)")
    
    return clues

if __name__ == "__main__":
    test_scraper()