import json
import re
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse

from database import JeopardyDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JeopardyDataProcessor:
    def __init__(self, db_url: Optional[str] = None):
        self.db = JeopardyDatabase(db_url)
        
        # Difficulty rating factors
        self.difficulty_weights = {
            'value': 0.3,           # Monetary value weight
            'word_count': 0.2,      # Question length weight
            'proper_nouns': 0.15,   # Proper noun count weight
            'dates': 0.15,          # Date/year presence weight
            'technical': 0.2        # Technical/specialized terms weight
        }
        
        # Keywords that indicate higher difficulty
        self.technical_keywords = {
            'scientific', 'mathematical', 'chemical', 'biological', 'anatomical',
            'philosophical', 'theoretical', 'quantum', 'molecular', 'constitutional',
            'parliamentary', 'ecclesiastical', 'archaeological', 'astronomical',
            'geological', 'meteorological', 'psychological', 'sociological'
        }
    
    def calculate_difficulty_rating(self, question_data: Dict) -> float:
        """Calculate a difficulty rating (0-10) based on multiple factors."""
        scores = {}
        
        # 1. Value-based score (normalized to 0-10)
        value = question_data.get('value', 0)
        if value <= 200:
            scores['value'] = 2
        elif value <= 400:
            scores['value'] = 4
        elif value <= 600:
            scores['value'] = 6
        elif value <= 800:
            scores['value'] = 8
        else:
            scores['value'] = 10
        
        # 2. Question length score
        question_text = question_data.get('question', '')
        word_count = len(question_text.split())
        if word_count < 10:
            scores['word_count'] = 3
        elif word_count < 20:
            scores['word_count'] = 5
        elif word_count < 30:
            scores['word_count'] = 7
        else:
            scores['word_count'] = 9
        
        # 3. Proper noun count (indicates specific knowledge required)
        proper_nouns = len(re.findall(r'\b[A-Z][a-z]+\b', question_text))
        scores['proper_nouns'] = min(proper_nouns * 2, 10)
        
        # 4. Date/year presence (historical questions often harder)
        dates = re.findall(r'\b(1[0-9]{3}|20[0-9]{2})\b', question_text)
        scores['dates'] = 8 if dates else 4
        
        # 5. Technical terminology score
        question_lower = question_text.lower()
        technical_count = sum(1 for keyword in self.technical_keywords 
                            if keyword in question_lower)
        scores['technical'] = min(technical_count * 3, 10)
        
        # Calculate weighted average
        total_score = sum(scores[factor] * self.difficulty_weights[factor] 
                         for factor in scores)
        
        return round(total_score, 2)
    
    def process_question(self, question_data: Dict) -> Dict:
        """Process a single question, adding difficulty rating and cleaning data."""
        # Clean and normalize the data
        processed = {
            'category': question_data.get('category', '').strip().upper(),
            'question': self.clean_text(question_data.get('question', '')),
            'answer': self.clean_text(question_data.get('answer', '')),
            'value': int(question_data.get('value', 0)) if question_data.get('value') else 0,
            'air_date': question_data.get('air_date', ''),
            'round': question_data.get('round', ''),
            'show_number': int(question_data.get('show_number', 0)) if question_data.get('show_number') else 0
        }
        
        # Add difficulty rating
        processed['difficulty_rating'] = self.calculate_difficulty_rating(question_data)
        
        return processed
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ''
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Fix common HTML entities
        replacements = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' ',
            '\\': ''
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def validate_question(self, question_data: Dict) -> bool:
        """Validate that a question has all required fields and is valid."""
        required_fields = ['question', 'answer', 'category']
        
        for field in required_fields:
            if not question_data.get(field):
                return False
        
        # Check for placeholder or invalid content
        question = question_data.get('question', '').lower()
        answer = question_data.get('answer', '').lower()
        
        invalid_patterns = [
            'unrevealed', 'no question', 'missing', 'unknown',
            '=', 'null', 'none', 'n/a'
        ]
        
        for pattern in invalid_patterns:
            if pattern in question or pattern in answer:
                return False
        
        # Ensure minimum length
        if len(question) < 10 or len(answer) < 2:
            return False
        
        return True
    
    def fetch_and_process_data(self, 
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             seasons: Optional[List[int]] = None) -> Tuple[int, int]:
        """Fetch data from scraper and process it."""
        logger.info("Web scraping not implemented in this version")
        logger.info("Please use --load-file option to load questions from a JSON file")
        return 0, 0
    
    def load_to_database(self, questions: List[Dict]) -> int:
        """Load processed questions into the database."""
        logger.info("Loading questions into database...")
        
        loaded_count = 0
        duplicate_count = 0
        
        # Process each question
        for question in questions:
            try:
                # Create a temporary JSON file for the database loader
                temp_data = [question]
                
                # Check if question already exists using database method
                existing_questions = self.db.get_questions(
                    category=question['category'],
                    count=1
                )
                
                # Check for duplicates
                is_duplicate = any(
                    q['question'] == question['question'] and 
                    q['answer'] == question['answer'] 
                    for q in existing_questions
                )
                
                if not is_duplicate:
                    # Save to temp file and use database's load method
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(temp_data, f)
                        temp_path = f.name
                    
                    try:
                        result = self.db.load_questions_from_json(temp_path)
                        loaded_count += result
                    finally:
                        os.unlink(temp_path)
                else:
                    duplicate_count += 1
                    
            except Exception as e:
                logger.error(f"Error loading question: {e}")
                continue
        
        logger.info(f"Loaded {loaded_count} new questions, "
                   f"skipped {duplicate_count} duplicates")
        
        return loaded_count
    
    def load_from_file(self, file_path: str) -> int:
        """Load questions from an existing JSON file."""
        logger.info(f"Loading questions from {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        # Process each question if not already processed
        processed_questions = []
        for question in questions:
            if 'difficulty_rating' not in question:
                processed = self.process_question(question)
            else:
                processed = question
            
            if self.validate_question(processed):
                processed_questions.append(processed)
        
        loaded_count = self.load_to_database(processed_questions)
        return loaded_count
    
    def update_difficulty_ratings(self):
        """Update difficulty ratings for existing questions based on performance."""
        logger.info("Updating difficulty ratings based on performance...")
        
        # Get hardest questions (which have been asked enough times)
        hard_questions = self.db.get_hardest_questions(limit=1000)
        
        updated_count = 0
        with self.db.get_connection() as conn:
            for q in hard_questions:
                if q['times_asked'] >= 10:
                    # Calculate performance-based difficulty
                    success_rate = q['times_correct'] / q['times_asked']
                    
                    # Invert success rate (lower success = higher difficulty)
                    performance_difficulty = (1 - success_rate) * 10
                    
                    # Get current calculated difficulty
                    question_data = {
                        'question': q['question'],
                        'value': q['value']
                    }
                    calculated_difficulty = self.calculate_difficulty_rating(question_data)
                    
                    # Weighted average of calculated and performance-based difficulty
                    # Give more weight to actual performance
                    new_difficulty = (calculated_difficulty * 0.3 + 
                                    performance_difficulty * 0.7)
                    
                    # Update using database-agnostic query
                    if self.db.db_type == 'postgresql':
                        cursor = conn.cursor()
                        cursor.execute(
                            'UPDATE questions SET difficulty_rating = %s WHERE id = %s',
                            (round(new_difficulty, 2), q['id'])
                        )
                        cursor.close()
                    else:
                        conn.execute(
                            'UPDATE questions SET difficulty_rating = ? WHERE id = ?',
                            (round(new_difficulty, 2), q['id'])
                        )
                    
                    updated_count += 1
            
            conn.commit()
            logger.info(f"Updated difficulty ratings for {updated_count} questions")
    
    def generate_stats_report(self):
        """Generate a statistics report about the question database."""
        with self.db.get_connection() as conn:
            # Total questions - use database helper method
            query1 = 'SELECT COUNT(*) as total FROM questions'
            total_result = self.db._execute_select(conn, query1)
            total = total_result[0]['total'] if total_result else 0
            
            # Questions by category - use get_categories method
            categories = self.db.get_categories()
            
            # Difficulty distribution
            query2 = '''SELECT 
                           CASE 
                               WHEN difficulty_rating < 3 THEN 'Easy (0-3)'
                               WHEN difficulty_rating < 6 THEN 'Medium (3-6)'
                               WHEN difficulty_rating < 8 THEN 'Hard (6-8)'
                               ELSE 'Very Hard (8-10)'
                           END as level,
                           COUNT(*) as count
                       FROM questions
                       WHERE difficulty_rating IS NOT NULL
                       GROUP BY level'''
            difficulty_dist = self.db._execute_select(conn, query2)
            
            # Value distribution
            query3 = '''SELECT value, COUNT(*) as count
                       FROM questions
                       WHERE value > 0
                       GROUP BY value
                       ORDER BY value'''
            value_dist = self.db._execute_select(conn, query3)
            
            print("\n=== Jeopardy Question Database Statistics ===")
            print(f"\nTotal Questions: {total:,}")
            
            print("\nTop Categories:")
            for cat, count in categories[:10]:
                print(f"  {cat}: {count:,}")
            
            print("\nDifficulty Distribution:")
            for diff in difficulty_dist:
                print(f"  {diff['level']}: {diff['count']:,}")
            
            print("\nValue Distribution:")
            for val in value_dist:
                print(f"  ${val['value']}: {val['count']:,}")

def main():
    parser = argparse.ArgumentParser(description='Process Jeopardy questions')
    parser.add_argument('--fetch', action='store_true', 
                       help='Fetch new data from web')
    parser.add_argument('--seasons', type=int, nargs='+',
                       help='Specific seasons to fetch')
    parser.add_argument('--start-date', type=str,
                       help='Start date for fetching (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='End date for fetching (YYYY-MM-DD)')
    parser.add_argument('--load-file', type=str,
                       help='Load questions from JSON file')
    parser.add_argument('--update-difficulty', action='store_true',
                       help='Update difficulty ratings based on performance')
    parser.add_argument('--stats', action='store_true',
                       help='Generate statistics report')
    parser.add_argument('--db-url', type=str,
                       help='Database URL (defaults to DATABASE_URL env var or sqlite)')
    
    args = parser.parse_args()
    processor = JeopardyDataProcessor(db_url=args.db_url)
    
    if args.fetch:
        processed, loaded = processor.fetch_and_process_data(
            start_date=args.start_date,
            end_date=args.end_date,
            seasons=args.seasons
        )
        print(f"Processed {processed} questions, loaded {loaded} into database")
    
    elif args.load_file:
        loaded = processor.load_from_file(args.load_file)
        print(f"Loaded {loaded} questions from file")
    
    elif args.update_difficulty:
        processor.update_difficulty_ratings()
    
    elif args.stats:
        processor.generate_stats_report()
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()