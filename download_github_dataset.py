#!/usr/bin/env python3
"""
Download Jeopardy dataset from GitHub (523,000+ questions).
Source: https://github.com/jwolle1/jeopardy_clue_dataset
"""

import urllib.request
import json
import csv
import os
import sys
from database import JeopardyDatabase

# GitHub raw URLs for the dataset files
BASE_URL = "https://raw.githubusercontent.com/jwolle1/jeopardy_clue_dataset/main/"
COMBINED_FILE = "combined_season1-41.tsv"
SAMPLE_SIZE = 300000  # Load first 300k questions

def download_and_process():
    """Download and process the dataset."""
    print(f"Downloading Jeopardy dataset from GitHub...")
    print(f"This dataset contains 538,000+ questions from Seasons 1-41")
    
    # Download the combined file
    url = BASE_URL + COMBINED_FILE
    local_file = f"data/{COMBINED_FILE}"
    
    print(f"Downloading from: {url}")
    print("This may take a few minutes...")
    
    try:
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        
        # Download the file
        urllib.request.urlretrieve(url, local_file)
        
        print(f"Downloaded to {local_file}")
        
    except Exception as e:
        print(f"Error downloading: {e}")
        return False
    
    # Process the TSV file
    print(f"\nProcessing dataset...")
    questions = []
    
    with open(local_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        for i, row in enumerate(reader):
            if i % 10000 == 0:
                print(f"Processing row {i}...")
            
            # The format includes:
            # round, clue_value, daily_double_value, category, comments, 
            # answer, question, air_date, notes
            
            # Clean value
            value_str = str(row.get('clue_value', '0')).replace('$', '').replace(',', '')
            try:
                value = int(value_str) if value_str.isdigit() else 0
            except:
                value = 0
            
            # Skip invalid values
            if value > 2000:
                value = 2000
            
            # Determine round type
            round_num = row.get('round', '1')
            if round_num == '1':
                round_name = 'Jeopardy!'
            elif round_num == '2':
                round_name = 'Double Jeopardy!'
            elif round_num == '3':
                round_name = 'Final Jeopardy!'
            else:
                round_name = 'Jeopardy!'
            
            question = {
                'category': (row.get('category', 'UNKNOWN') or 'UNKNOWN').upper().strip(),
                'question': row.get('question', '').strip(),
                'answer': row.get('answer', '').strip(),
                'value': value,
                'show_number': 0,  # Not available in this format
                'air_date': row.get('air_date', ''),
                'round': round_name
            }
            
            # Skip questions with empty answers or questions
            if question['answer'] and question['question']:
                questions.append(question)
            
            # Limit to sample size
            if len(questions) >= SAMPLE_SIZE:
                print(f"Reached {SAMPLE_SIZE} questions limit")
                break
    
    print(f"Processed {len(questions)} valid questions")
    
    # Save processed questions
    output_file = 'data/jeopardy_github_100k.json'
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
    
    # Clean up large TSV file to save space
    if os.path.exists(local_file):
        os.remove(local_file)
        print(f"\nCleaned up temporary file: {local_file}")
    
    return True

if __name__ == "__main__":
    if not download_and_process():
        print("\nFailed to download dataset.")
        print("You can manually download from:")
        print("https://github.com/jwolle1/jeopardy_clue_dataset")
        sys.exit(1)
    else:
        print("\nSuccess! Database now contains 100,000+ Jeopardy questions.")
        print("To load more questions, modify SAMPLE_SIZE in the script.")