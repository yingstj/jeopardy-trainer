#!/usr/bin/env python3
"""
Load Jeopardy dataset from CSV file (Kaggle format).
Handles the 200,000+ questions dataset.
"""

import csv
import json
import os
import sys
import re
from datetime import datetime
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

def load_csv_dataset(csv_file):
    """Load Jeopardy dataset from CSV file."""
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found at {csv_file}")
        return False
    
    print(f"Loading dataset from {csv_file}...")
    
    questions = []
    
    # Read CSV file
    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
        # Try to detect delimiter
        sample = f.read(1024)
        f.seek(0)
        
        # Kaggle dataset typically uses comma delimiter
        delimiter = ','
        if '\t' in sample and sample.count('\t') > sample.count(','):
            delimiter = '\t'
        
        reader = csv.DictReader(f, delimiter=delimiter)
        
        for i, row in enumerate(reader):
            if i % 10000 == 0:
                print(f"Processing row {i}...")
            
            # Handle different column names
            question_text = clean_text(
                row.get('Question') or 
                row.get('question') or 
                row.get('Clue') or 
                row.get('clue') or ''
            )
            
            answer_text = clean_text(
                row.get('Answer') or 
                row.get('answer') or 
                row.get('Response') or 
                row.get('response') or ''
            )
            
            category = clean_text(
                row.get('Category') or 
                row.get('category') or 
                'UNKNOWN'
            ).upper()
            
            value = parse_value(
                row.get('Value') or 
                row.get('value') or 
                row.get('Dollar Value') or 
                '0'
            )
            
            # Skip invalid questions
            if not question_text or not answer_text:
                continue
            
            # Skip Daily Doubles with weird values
            if value > 2000 and 'Daily Double' not in str(row.get('Round', '')):
                value = 2000  # Cap at max normal value
            
            question = {
                'category': category,
                'question': question_text,
                'answer': answer_text,
                'value': value,
                'show_number': row.get('Show Number') or row.get('show_number') or 0,
                'air_date': row.get('Air Date') or row.get('air_date') or '',
                'round': row.get('Round') or row.get('round') or 'Jeopardy!'
            }
            
            questions.append(question)
            
            # Limit for testing
            if len(questions) >= 100000:
                print(f"Reached 100,000 questions limit")
                break
    
    print(f"Processed {len(questions)} valid questions")
    
    # Save processed questions
    output_file = 'data/jeopardy_100k.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2)
    
    print(f"Saved to {output_file}")
    
    # Load into database
    print("\nLoading into database...")
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
    count = db.load_questions_from_json(output_file)
    print(f"Loaded {count} questions into database")
    
    # Show statistics
    categories = db.get_categories()
    print(f"\nTotal categories: {len(categories)}")
    print("\nTop 20 categories:")
    for cat, count in categories[:20]:
        print(f"  {cat}: {count} questions")
    
    # Show total question count
    with db.get_connection() as conn:
        if db.db_type == 'postgresql':
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM questions')
            total = cursor.fetchone()[0]
            cursor.close()
        else:
            total = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
    
    print(f"\nTotal questions in database: {total:,}")
    
    return True

if __name__ == "__main__":
    # Check for CSV file argument
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        # Default locations to check
        possible_files = [
            'data/jeopardy.csv',
            'data/JEOPARDY_CSV.csv',
            'data/jeopardy_questions.csv',
            'jeopardy.csv',
            'JEOPARDY_CSV.csv'
        ]
        
        csv_file = None
        for f in possible_files:
            if os.path.exists(f):
                csv_file = f
                break
        
        if not csv_file:
            print("Usage: python load_jeopardy_csv.py <csv_file>")
            print("\nOr place your CSV file at one of these locations:")
            for f in possible_files:
                print(f"  - {f}")
            print("\nDownload from: https://www.kaggle.com/datasets/tunguz/200000-jeopardy-questions")
            sys.exit(1)
    
    if not load_csv_dataset(csv_file):
        sys.exit(1)