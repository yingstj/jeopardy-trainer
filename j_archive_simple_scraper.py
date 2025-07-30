#!/usr/bin/env python3
"""
Simple J-Archive scraper using regex patterns.
More reliable than HTML parsing for J-Archive's structure.
"""

import urllib.request
import json
import re
import time
import os
from database import JeopardyDatabase

class JArchiveSimpleScraper:
    def __init__(self):
        self.base_url = "https://j-archive.com/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; JeopardyBot/1.0)'
        }
        
    def fetch_page(self, url):
        """Fetch a page with error handling."""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
            
    def clean_html(self, text):
        """Remove HTML tags and decode entities."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode common HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&nbsp;', ' ')
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()
        
    def get_recent_games(self, num_games=50):
        """Get IDs of recent games from the main archive."""
        html = self.fetch_page(self.base_url)
        if not html:
            return []
            
        # Find recent game IDs
        # Pattern: <a href="showgame.php?game_id=7883">#7883</a>
        game_ids = re.findall(r'showgame\.php\?game_id=(\d+)', html)
        
        # Convert to integers and remove duplicates
        game_ids = list(set(int(gid) for gid in game_ids))
        game_ids.sort(reverse=True)  # Most recent first
        
        return game_ids[:num_games]
        
    def scrape_game(self, game_id):
        """Scrape a single game."""
        url = f"{self.base_url}showgame.php?game_id={game_id}"
        html = self.fetch_page(url)
        if not html:
            return []
            
        questions = []
        
        # Extract game date
        date_match = re.search(r'<title>.*?aired (\d{4}-\d{2}-\d{2})', html)
        air_date = date_match.group(1) if date_match else ''
        
        # Extract show number
        show_match = re.search(r'Show #(\d+)', html)
        show_number = show_match.group(1) if show_match else str(game_id)
        
        # Process each round
        for round_name, round_id in [('Jeopardy!', 'jeopardy_round'), 
                                      ('Double Jeopardy!', 'double_jeopardy_round')]:
            
            # Find round section
            round_match = re.search(f'<div id="{round_id}".*?</table>', html, re.DOTALL)
            if not round_match:
                continue
                
            round_html = round_match.group(0)
            
            # Extract categories for this round
            cat_matches = re.findall(r'<td class="category_name">([^<]+)</td>', round_html)
            categories = [self.clean_html(cat) for cat in cat_matches]
            
            # Extract all clues in order
            clue_pattern = r'<td class="clue".*?</td>'
            clues = re.findall(clue_pattern, round_html, re.DOTALL)
            
            # Process clues
            base_value = 200 if round_name == 'Jeopardy!' else 400
            
            for idx, clue_html in enumerate(clues):
                # Skip empty clues
                if 'clue_text' not in clue_html:
                    continue
                    
                # Determine category and value
                cat_idx = idx % len(categories)
                row = idx // len(categories)
                category = categories[cat_idx] if cat_idx < len(categories) else 'UNKNOWN'
                value = base_value * (row + 1)
                
                # Extract clue text
                clue_match = re.search(r'<td class="clue_text[^"]*">(.+?)</td>', clue_html, re.DOTALL)
                if not clue_match:
                    continue
                    
                clue_text = self.clean_html(clue_match.group(1))
                
                # Extract answer - try multiple patterns
                answer = None
                
                # Pattern 1: onmouseover with correct_response
                answer_match = re.search(r'correct_response.*?&gt;(.+?)&lt;/em', clue_html)
                if answer_match:
                    answer = self.clean_html(answer_match.group(1))
                else:
                    # Pattern 2: In toggle section
                    answer_match = re.search(r'correct_response[^>]*>([^<]+)<', clue_html)
                    if answer_match:
                        answer = self.clean_html(answer_match.group(1))
                        
                if clue_text and answer:
                    questions.append({
                        'category': category.upper(),
                        'question': clue_text,
                        'answer': answer,
                        'value': value,
                        'round': round_name,
                        'air_date': air_date,
                        'show_number': show_number
                    })
                    
        # Extract Final Jeopardy
        fj_match = re.search(r'<table class="final_round".*?</table>', html, re.DOTALL)
        if fj_match:
            fj_html = fj_match.group(0)
            
            # Category
            cat_match = re.search(r'<td class="category"[^>]*>([^<]+)</td>', fj_html)
            category = self.clean_html(cat_match.group(1)) if cat_match else 'FINAL JEOPARDY'
            
            # Clue
            clue_match = re.search(r'<td class="clue_text">([^<]+)</td>', fj_html)
            if clue_match:
                clue_text = self.clean_html(clue_match.group(1))
                
                # Answer
                answer_match = re.search(r'correct_response.*?&gt;(.+?)&lt;', fj_html)
                if answer_match:
                    answer = self.clean_html(answer_match.group(1))
                    
                    questions.append({
                        'category': category.upper(),
                        'question': clue_text,
                        'answer': answer,
                        'value': 0,
                        'round': 'Final Jeopardy!',
                        'air_date': air_date,
                        'show_number': show_number
                    })
                    
        return questions
        
def main():
    """Main scraping function."""
    scraper = JArchiveSimpleScraper()
    
    print("J-Archive Simple Scraper")
    print("========================\n")
    
    # Get recent games
    print("Fetching recent games...")
    game_ids = scraper.get_recent_games(num_games=100)  # Get 100 recent games
    print(f"Found {len(game_ids)} recent games\n")
    
    all_questions = []
    successful_games = 0
    
    # Scrape games
    for i, game_id in enumerate(game_ids):
        print(f"Scraping game {i+1}/{len(game_ids)} (ID: {game_id})...", end='', flush=True)
        
        questions = scraper.scrape_game(game_id)
        if questions:
            all_questions.extend(questions)
            successful_games += 1
            print(f" ✓ ({len(questions)} questions)")
        else:
            print(" ✗ (failed)")
            
        # Be nice to the server
        time.sleep(0.5)
        
        # Save progress every 10 games
        if (i + 1) % 10 == 0:
            temp_file = f'data/j_archive_temp_{i+1}.json'
            with open(temp_file, 'w') as f:
                json.dump(all_questions, f, indent=2)
            print(f"  Saved progress: {len(all_questions)} questions")
            
    # Save final results
    output_file = 'data/j_archive_scraped.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_questions, f, indent=2)
        
    print(f"\n{'='*50}")
    print(f"Scraping complete!")
    print(f"Successfully scraped: {successful_games}/{len(game_ids)} games")
    print(f"Total questions: {len(all_questions)}")
    print(f"Saved to: {output_file}")
    
    # Analyze the data
    if all_questions:
        categories = {}
        for q in all_questions:
            cat = q['category']
            categories[cat] = categories.get(cat, 0) + 1
            
        print(f"\nFound {len(categories)} unique categories")
        print("\nTop 20 categories:")
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        for cat, count in sorted_cats[:20]:
            print(f"  {cat}: {count} questions")
            
    # Load into database
    if input("\nLoad into database? (y/n): ").lower() == 'y':
        db = JeopardyDatabase()
        
        # Clear old questions first
        with db.get_connection() as conn:
            if db.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_progress')
                cursor.execute('DELETE FROM questions')
                conn.commit()
                cursor.close()
            else:
                conn.execute('DELETE FROM user_progress')
                conn.execute('DELETE FROM questions')
                conn.commit()
                
        count = db.load_questions_from_json(output_file)
        print(f"\nLoaded {count} questions into database")

if __name__ == "__main__":
    main()