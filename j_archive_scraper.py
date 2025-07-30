#!/usr/bin/env python3
"""
Scraper for J-Archive to get real Jeopardy questions.
J-Archive structure:
- Seasons list: https://j-archive.com/listseasons.php
- Each season has multiple games
- Each game has categories, clues, and answers
"""

import urllib.request
import urllib.parse
import json
import re
import time
from html.parser import HTMLParser
from database import JeopardyDatabase
import os

class JArchiveParser(HTMLParser):
    """Parser for J-Archive HTML pages."""
    
    def __init__(self):
        super().__init__()
        self.current_tag = None
        self.current_attrs = {}
        self.in_clue = False
        self.in_answer = False
        self.current_category = ""
        self.clues = []
        self.text_buffer = ""
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = dict(attrs)
        
        # Check for clue cells
        if tag == 'td' and 'class' in self.current_attrs:
            if 'clue_text' in self.current_attrs['class']:
                self.in_clue = True
                self.text_buffer = ""
                
    def handle_endtag(self, tag):
        if tag == 'td' and self.in_clue:
            self.in_clue = False
            # Store the clue text
            if hasattr(self, 'current_clue'):
                self.current_clue['question'] = self.text_buffer.strip()
                
        self.current_tag = None
        
    def handle_data(self, data):
        if self.in_clue:
            self.text_buffer += data
        elif self.current_tag == 'td' and 'category_name' in self.current_attrs.get('class', ''):
            self.current_category = data.strip()

class JArchiveScraper:
    """Scraper for J-Archive website."""
    
    def __init__(self):
        self.base_url = "https://j-archive.com/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
    def fetch_page(self, url):
        """Fetch a page from J-Archive."""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
            
    def get_seasons(self):
        """Get list of all seasons from J-Archive."""
        html = self.fetch_page(f"{self.base_url}listseasons.php")
        if not html:
            return []
            
        # Extract season links
        # Pattern: <a href="showseason.php?season=40">Season 40</a>
        season_pattern = r'<a href="showseason\.php\?season=(\d+)">Season (\d+)</a>'
        seasons = re.findall(season_pattern, html)
        
        return [(int(s[0]), int(s[1])) for s in seasons]
        
    def get_games_in_season(self, season_num):
        """Get all games in a season."""
        html = self.fetch_page(f"{self.base_url}showseason.php?season={season_num}")
        if not html:
            return []
            
        # Extract game links
        # Pattern: <a href="showgame.php?game_id=7000">
        game_pattern = r'<a href="showgame\.php\?game_id=(\d+)"[^>]*>([^<]+)</a>'
        games = re.findall(game_pattern, html)
        
        game_list = []
        for game_id, game_text in games:
            # Extract date if present
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', game_text)
            date = date_match.group(1) if date_match else ""
            
            game_list.append({
                'game_id': int(game_id),
                'date': date,
                'text': game_text.strip()
            })
            
        return game_list
        
    def parse_game(self, game_id):
        """Parse a single game and extract all questions."""
        html = self.fetch_page(f"{self.base_url}showgame.php?game_id={game_id}")
        if not html:
            return []
            
        questions = []
        
        # Extract categories
        category_pattern = r'<td class="category_name">([^<]+)</td>'
        categories = re.findall(category_pattern, html)
        
        # Extract round information
        rounds = ['Jeopardy!', 'Double Jeopardy!', 'Final Jeopardy!']
        
        # Parse Jeopardy! and Double Jeopardy! rounds
        for round_idx, round_name in enumerate(rounds[:2]):
            round_id = f"jeopardy_round" if round_idx == 0 else "double_jeopardy_round"
            
            # Find the round section
            round_start = html.find(f'<div id="{round_id}"')
            if round_start == -1:
                continue
                
            round_end = html.find('</div>', round_start)
            round_html = html[round_start:round_end]
            
            # Extract clues for this round
            # Pattern for clue with value, question, and answer
            clue_pattern = r'<td class="clue_value[^"]*"[^>]*>\$?(\d+)</td>.*?<td class="clue_text[^"]*"[^>]*>([^<]+(?:<[^>]+>[^<]+)*)</td>'
            
            # Also need to extract the answer from the hover or link
            answer_pattern = r'correct_response&quot;&gt;([^&]+)&lt;/em&gt;'
            
            # Process clues by category
            base_value = 200 if round_idx == 0 else 400
            
            # Extract all clue cells
            clue_cells = re.findall(r'<td class="clue">.*?</td>', round_html, re.DOTALL)
            
            for idx, clue_cell in enumerate(clue_cells):
                # Determine category (6 categories per round)
                cat_idx = idx % 6
                if cat_idx < len(categories):
                    category = categories[cat_idx] if round_idx == 0 else categories[cat_idx + 6]
                else:
                    category = "UNKNOWN"
                    
                # Determine value
                row = idx // 6
                value = base_value * (row + 1)
                
                # Extract clue text
                clue_match = re.search(r'<td class="clue_text[^"]*"[^>]*>(.+?)</td>', clue_cell, re.DOTALL)
                if not clue_match:
                    continue
                    
                clue_text = clue_match.group(1)
                # Clean HTML from clue text
                clue_text = re.sub(r'<[^>]+>', '', clue_text).strip()
                
                # Extract answer
                answer_match = re.search(r'correct_response.*?>([^<]+)</em>', clue_cell, re.DOTALL)
                if not answer_match:
                    # Try alternate pattern
                    answer_match = re.search(r'correct_response[^>]*>([^<]+)<', clue_cell, re.DOTALL)
                    
                if answer_match:
                    answer = answer_match.group(1).strip()
                    
                    # Clean up answer
                    answer = answer.replace('&quot;', '"').replace('&amp;', '&')
                    answer = answer.replace('\\', '').strip()
                    
                    if clue_text and answer:
                        questions.append({
                            'game_id': game_id,
                            'round': round_name,
                            'category': category.upper(),
                            'value': value,
                            'question': clue_text,
                            'answer': answer,
                            'air_date': '',  # Will be filled from game info
                            'show_number': game_id
                        })
                        
        # Parse Final Jeopardy!
        final_pattern = r'<td class="category"[^>]*>([^<]+)</td>.*?<td class="clue_text"[^>]*>([^<]+)</td>.*?correct_response.*?>([^<]+)</em>'
        final_match = re.search(final_pattern, html, re.DOTALL)
        
        if final_match:
            questions.append({
                'game_id': game_id,
                'round': 'Final Jeopardy!',
                'category': final_match.group(1).strip().upper(),
                'value': 0,
                'question': final_match.group(2).strip(),
                'answer': final_match.group(3).strip(),
                'air_date': '',
                'show_number': game_id
            })
            
        return questions
        
    def scrape_season(self, season_num, max_games=10):
        """Scrape all games from a season."""
        print(f"\nScraping Season {season_num}...")
        
        games = self.get_games_in_season(season_num)
        print(f"Found {len(games)} games in season {season_num}")
        
        all_questions = []
        
        for i, game in enumerate(games[:max_games]):
            print(f"  Scraping game {i+1}/{min(len(games), max_games)}: {game['text']}")
            
            questions = self.parse_game(game['game_id'])
            
            # Add air date to questions
            for q in questions:
                q['air_date'] = game['date']
                
            all_questions.extend(questions)
            
            # Be polite to the server
            time.sleep(0.5)
            
        return all_questions
        
def main():
    """Main function to scrape J-Archive."""
    scraper = JArchiveScraper()
    
    print("J-Archive Scraper")
    print("=================")
    
    # Get list of seasons
    print("Fetching seasons list...")
    seasons = scraper.get_seasons()
    print(f"Found {len(seasons)} seasons")
    
    # Scrape recent seasons (e.g., seasons 38-40)
    all_questions = []
    
    # You can modify these to scrape different seasons
    seasons_to_scrape = [40, 39, 38]  # Recent seasons
    games_per_season = 20  # Limit games per season for testing
    
    for season_num in seasons_to_scrape:
        questions = scraper.scrape_season(season_num, max_games=games_per_season)
        all_questions.extend(questions)
        print(f"  Total questions so far: {len(all_questions)}")
        
    # Save to JSON
    output_file = 'data/j_archive_questions.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_questions, f, indent=2)
        
    print(f"\nSaved {len(all_questions)} questions to {output_file}")
    
    # Load into database
    if input("\nLoad into database? (y/n): ").lower() == 'y':
        db = JeopardyDatabase()
        count = db.load_questions_from_json(output_file)
        print(f"Loaded {count} questions into database")
        
        # Show statistics
        categories = db.get_categories()
        print(f"\nTotal categories: {len(categories)}")
        print("\nTop 10 categories:")
        for cat, count in categories[:10]:
            print(f"  {cat}: {count} questions")

if __name__ == "__main__":
    main()