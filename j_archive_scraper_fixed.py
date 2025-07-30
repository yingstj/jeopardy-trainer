#!/usr/bin/env python3
"""
Fixed J-Archive scraper that properly extracts answers from hidden elements.
"""

import urllib.request
import json
import re
import time
import os
from database import JeopardyDatabase

class JArchiveScraperFixed:
    def __init__(self):
        self.base_url = "https://j-archive.com/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
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
            
    def clean_text(self, text):
        """Clean and normalize text."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&nbsp;', ' ')
        text = text.replace('\\', '')
        # Clean whitespace
        text = ' '.join(text.split())
        return text.strip()
        
    def extract_clue_data(self, html, round_name, base_value):
        """Extract clues from a round."""
        questions = []
        
        # Extract categories
        categories = re.findall(r'<td class="category_name">([^<]+)</td>', html)
        categories = [self.clean_text(cat) for cat in categories]
        
        # Find all clue pairs (visible question + hidden answer)
        # Pattern: question in one td, answer in the next td with display:none
        clue_pattern = r'<td id="clue_[^"]+" class="clue_text">([^<]+)</td>\s*<td[^>]+style="display:none;"[^>]*>.*?<em class="correct_response">([^<]+)</em>'
        
        clues = re.findall(clue_pattern, html, re.DOTALL)
        
        # Also extract clue positions to determine category and value
        position_pattern = r'<td id="clue_([JD])_(\d+)_(\d+)" class="clue_text">([^<]+)</td>'
        positions = re.findall(position_pattern, html)
        
        # Process clues with position information
        for match in positions:
            round_letter, col, row = match[0], int(match[1]), int(match[2])
            question_text = self.clean_text(match[3])
            
            # Find corresponding answer
            answer_id = f"clue_{round_letter}_{col}_{row}_r"
            answer_pattern = f'<td id="{answer_id}"[^>]*>.*?<em class="correct_response">([^<]+)</em>'
            answer_match = re.search(answer_pattern, html, re.DOTALL)
            
            if answer_match:
                answer_text = self.clean_text(answer_match.group(1))
                
                # Determine category (col-1 because it's 1-indexed)
                category = categories[col-1] if col-1 < len(categories) else 'UNKNOWN'
                
                # Calculate value
                value = base_value * row
                
                questions.append({
                    'category': category.upper(),
                    'question': question_text,
                    'answer': answer_text,
                    'value': value,
                    'round': round_name
                })
                
        return questions
        
    def scrape_game(self, game_id):
        """Scrape a single game."""
        url = f"{self.base_url}showgame.php?game_id={game_id}"
        html = self.fetch_page(url)
        if not html:
            return []
            
        questions = []
        
        # Extract game info
        title_match = re.search(r'<title>J! Archive - Show #(\d+), aired (\d{4}-\d{2}-\d{2})</title>', html)
        if title_match:
            show_number = title_match.group(1)
            air_date = title_match.group(2)
        else:
            show_number = str(game_id)
            air_date = ''
            
        # Extract Jeopardy! round
        j_round_match = re.search(r'<div id="jeopardy_round".*?</div>\s*</td>\s*</tr>\s*</table>', html, re.DOTALL)
        if j_round_match:
            j_questions = self.extract_clue_data(j_round_match.group(0), 'Jeopardy!', 200)
            for q in j_questions:
                q['show_number'] = show_number
                q['air_date'] = air_date
            questions.extend(j_questions)
            
        # Extract Double Jeopardy! round
        dj_round_match = re.search(r'<div id="double_jeopardy_round".*?</div>\s*</td>\s*</tr>\s*</table>', html, re.DOTALL)
        if dj_round_match:
            dj_questions = self.extract_clue_data(dj_round_match.group(0), 'Double Jeopardy!', 400)
            for q in dj_questions:
                q['show_number'] = show_number
                q['air_date'] = air_date
            questions.extend(dj_questions)
            
        # Extract Final Jeopardy!
        fj_pattern = r'<td class="category"[^>]*>([^<]+)</td>.*?<td id="clue_FJ" class="clue_text">([^<]+)</td>.*?<em class="correct_response">([^<]+)</em>'
        fj_match = re.search(fj_pattern, html, re.DOTALL)
        if fj_match:
            questions.append({
                'category': self.clean_text(fj_match.group(1)).upper(),
                'question': self.clean_text(fj_match.group(2)),
                'answer': self.clean_text(fj_match.group(3)),
                'value': 0,
                'round': 'Final Jeopardy!',
                'show_number': show_number,
                'air_date': air_date
            })
            
        return questions
        
    def get_game_ids_from_season(self, season_num):
        """Get game IDs from a specific season."""
        url = f"{self.base_url}showseason.php?season={season_num}"
        html = self.fetch_page(url)
        if not html:
            return []
            
        # Extract game IDs
        game_ids = re.findall(r'game_id=(\d+)', html)
        return list(set(int(gid) for gid in game_ids))
        
def main():
    """Main function."""
    scraper = JArchiveScraperFixed()
    
    print("J-Archive Fixed Scraper")
    print("=======================\n")
    
    # Test with a known game first
    print("Testing with game #7000...")
    test_questions = scraper.scrape_game(7000)
    print(f"Found {len(test_questions)} questions")
    
    if test_questions:
        print("\nSample questions:")
        for q in test_questions[:3]:
            print(f"  {q['category']}: {q['question'][:50]}...")
            print(f"  Answer: {q['answer']}")
            print()
            
    # Get games from recent seasons
    all_questions = []
    
    # Scrape games from seasons 38-40 (recent seasons)
    seasons_to_scrape = [40, 39, 38]
    games_per_season = 50  # Adjust as needed
    
    for season in seasons_to_scrape:
        print(f"\nGetting games from Season {season}...")
        game_ids = scraper.get_game_ids_from_season(season)
        print(f"Found {len(game_ids)} games")
        
        # Scrape games
        games_to_scrape = game_ids[:games_per_season]
        for i, game_id in enumerate(games_to_scrape):
            print(f"  Scraping game {i+1}/{len(games_to_scrape)} (ID: {game_id})...", end='', flush=True)
            
            questions = scraper.scrape_game(game_id)
            if questions:
                all_questions.extend(questions)
                print(f" ✓ ({len(questions)} questions)")
            else:
                print(" ✗")
                
            # Be polite
            time.sleep(0.5)
            
    # Save results
    output_file = 'data/j_archive_final.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_questions, f, indent=2)
        
    print(f"\n{'='*50}")
    print(f"Total questions scraped: {len(all_questions)}")
    print(f"Saved to: {output_file}")
    
    # Analyze categories
    if all_questions:
        categories = {}
        for q in all_questions:
            categories[q['category']] = categories.get(q['category'], 0) + 1
            
        print(f"\nUnique categories: {len(categories)}")
        print("\nTop 20 categories:")
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        for cat, count in sorted_cats[:20]:
            print(f"  {cat}: {count}")

if __name__ == "__main__":
    main()