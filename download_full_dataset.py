#!/usr/bin/env python3
"""
Download and load the full Jeopardy dataset with 200,000+ questions.
"""

import json
import requests
import os
import sys
from database import JeopardyDatabase

# The dataset URL - this is a well-known public dataset
DATASET_URL = "https://drive.google.com/uc?id=0BwT5wj_P7BKXUl9tOUJWYzVvUDQ&export=download"
ALTERNATE_URL = "https://raw.githubusercontent.com/BROWNPROTON/36e0c912f227d6546e425d1f77a77f96/raw/JEOPARDY_QUESTIONS1.json"
LOCAL_FILE = "data/jeopardy_full_200k.json"

def download_dataset():
    """Download the full Jeopardy dataset."""
    print("Downloading full Jeopardy dataset (200,000+ questions)...")
    print("This may take a few minutes...")
    
    # Try alternate URL first (GitHub gist)
    try:
        response = requests.get(ALTERNATE_URL, stream=True)
        response.raise_for_status()
        
        # Save to file
        os.makedirs(os.path.dirname(LOCAL_FILE), exist_ok=True)
        with open(LOCAL_FILE, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Downloaded to {LOCAL_FILE}")
        return True
        
    except Exception as e:
        print(f"Failed to download from primary source: {e}")
        print("Please download manually from: https://www.kaggle.com/datasets/tunguz/200000-jeopardy-questions")
        print("Or search for 'JEOPARDY_QUESTIONS1.json' online")
        return False

def load_dataset():
    """Load the dataset into the database."""
    if not os.path.exists(LOCAL_FILE):
        print(f"Dataset file not found at {LOCAL_FILE}")
        if not download_dataset():
            return False
    
    print("Loading dataset...")
    
    # Read the dataset
    with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Found {len(data)} questions in dataset")
    
    # Transform to our format
    questions = []
    for item in data[:100000]:  # Limit to first 100k for now
        # The dataset format is typically:
        # {
        #   "Show Number": "4680",
        #   "Air Date": "2004-12-31",
        #   "Round": "Jeopardy!",
        #   "Category": "HISTORY",
        #   "Value": "$200",
        #   "Question": "...",
        #   "Answer": "..."
        # }
        
        # Clean up value
        value_str = str(item.get('Value', '$0')).replace('$', '').replace(',', '')
        try:
            value = int(value_str) if value_str.isdigit() else 0
        except:
            value = 0
        
        question = {
            'category': item.get('Category', 'UNKNOWN').upper(),
            'question': item.get('Question', ''),
            'answer': item.get('Answer', ''),
            'value': value,
            'show_number': item.get('Show Number', 0),
            'air_date': item.get('Air Date', ''),
            'round': item.get('Round', 'Jeopardy!')
        }
        
        # Skip questions with empty answers or questions
        if question['answer'] and question['question']:
            questions.append(question)
    
    print(f"Processed {len(questions)} valid questions")
    
    # Save processed questions
    processed_file = 'data/jeopardy_processed_100k.json'
    with open(processed_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2)
    
    print(f"Saved processed questions to {processed_file}")
    
    # Load into database
    print("Loading into database...")
    db = JeopardyDatabase()
    
    # Clear existing questions
    print("Clearing old questions...")
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
    
    # Load new questions
    count = db.load_questions_from_json(processed_file)
    print(f"Loaded {count} questions into database")
    
    # Show statistics
    categories = db.get_categories()
    print(f"\nTotal categories: {len(categories)}")
    print("\nTop 20 categories:")
    for cat, count in categories[:20]:
        print(f"  {cat}: {count} questions")
    
    return True

if __name__ == "__main__":
    if not load_dataset():
        print("\nTo manually download the dataset:")
        print("1. Go to: https://www.kaggle.com/datasets/tunguz/200000-jeopardy-questions")
        print("2. Download 'jeopardy.csv' or 'JEOPARDY_QUESTIONS1.json'")
        print("3. Place it in the 'data/' directory")
        print("4. Run this script again")
        sys.exit(1)