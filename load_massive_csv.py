#!/usr/bin/env python3
"""
Load the massive J-Archive CSV (1.1M+ questions) into the database.
Optimized for large datasets with batch processing.
"""

import csv
import os
import sys
import re
from database import JeopardyDatabase

def clean_text(text):
    """Clean HTML and special characters from text."""
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Replace HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&quot;', '"')
    text = text.replace('&apos;', "'")
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('\\', '')
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text.strip()

def parse_value(value_str):
    """Parse dollar value from string."""
    if not value_str:
        return 0
    
    # Remove $ and commas
    value_str = str(value_str).replace('$', '').replace(',', '').strip()
    
    # Handle "None" or empty values
    if not value_str or value_str.lower() == 'none':
        return 0
    
    try:
        return int(value_str)
    except:
        return 0

def load_massive_csv():
    """Load the massive J-Archive CSV file."""
    csv_file = "/Users/julieyingst/Documents/jeopardy_ai/data/all_jeopardy_clues.csv"
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found at {csv_file}")
        return False
    
    print(f"Loading massive dataset from {csv_file}...")
    
    # Fix DATABASE_URL if it has line breaks
    db_url = os.environ.get('DATABASE_URL', '').strip().replace('\n', '').replace(' ', '')
    if db_url:
        os.environ['DATABASE_URL'] = db_url
    
    db = JeopardyDatabase()
    
    # Clear existing questions
    print("Clearing existing questions...")
    with db.get_connection() as conn:
        if db.db_type == 'postgresql':
            cursor = conn.cursor()
            cursor.execute('TRUNCATE TABLE user_progress CASCADE')
            cursor.execute('TRUNCATE TABLE questions CASCADE')
            conn.commit()
            cursor.close()
        else:
            conn.execute('DELETE FROM user_progress')
            conn.execute('DELETE FROM questions')
            conn.commit()
    
    # Process CSV in batches
    batch_size = 5000
    batch_questions = []
    total_loaded = 0
    
    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            if i % 10000 == 0:
                print(f"Processing row {i:,}...")
            
            # Extract fields - match CSV column names
            question_text = clean_text(row.get('clue', ''))
            answer_text = clean_text(row.get('correct_response', ''))
            category = clean_text(row.get('category', 'UNKNOWN')).upper()
            value = parse_value(row.get('value', '200'))  # Default to $200 if no value
            
            # Skip invalid questions
            if not question_text or not answer_text:
                continue
            
            # Skip if answer is just a number (bad data)
            if answer_text.isdigit():
                continue
            
            batch_questions.append((
                category,
                question_text,
                answer_text,
                value
            ))
            
            # Insert batch when full
            if len(batch_questions) >= batch_size:
                insert_batch(db, batch_questions)
                total_loaded += len(batch_questions)
                print(f"  Loaded {total_loaded:,} questions...")
                batch_questions = []
        
        # Insert remaining questions
        if batch_questions:
            insert_batch(db, batch_questions)
            total_loaded += len(batch_questions)
    
    print(f"\nSuccessfully loaded {total_loaded:,} questions!")
    
    # Show statistics
    with db.get_connection() as conn:
        if db.db_type == 'postgresql':
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM questions')
            total = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(DISTINCT category) FROM questions')
            categories = cursor.fetchone()[0]
            cursor.close()
        else:
            cursor = conn.cursor()
            total = cursor.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
            categories = cursor.execute('SELECT COUNT(DISTINCT category) FROM questions').fetchone()[0]
    
    print(f"\nDatabase statistics:")
    print(f"  Total questions: {total:,}")
    print(f"  Total categories: {categories:,}")
    
    return True

def insert_batch(db, batch_questions):
    """Insert a batch of questions into the database."""
    with db.get_connection() as conn:
        if db.db_type == 'postgresql':
            cursor = conn.cursor()
            cursor.executemany(
                'INSERT INTO questions (category, question, answer, value) VALUES (%s, %s, %s, %s)',
                batch_questions
            )
            conn.commit()
            cursor.close()
        else:
            conn.executemany(
                'INSERT INTO questions (category, question, answer, value) VALUES (?, ?, ?, ?)',
                batch_questions
            )
            conn.commit()

if __name__ == "__main__":
    print("J-Archive Massive CSV Loader")
    print("=" * 50)
    
    # Check database type
    db = JeopardyDatabase()
    print(f"Database type: {db.db_type}")
    if db.db_type == 'postgresql':
        print("Connected to PostgreSQL")
    else:
        print("Using SQLite (local)")
    
    if not load_massive_csv():
        sys.exit(1)