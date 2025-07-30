#!/usr/bin/env python3
"""
Batch loader for large J-Archive dataset.
Processes questions in chunks to avoid timeouts.
"""

import json
import sys
import os
from database import JeopardyDatabase

def load_in_batches(json_file, batch_size=10000):
    """Load questions in batches."""
    print(f"Loading questions from {json_file}...")
    
    # Read the JSON file
    with open(json_file, 'r', encoding='utf-8') as f:
        all_questions = json.load(f)
    
    print(f"Found {len(all_questions):,} questions in file")
    
    # Initialize database
    db = JeopardyDatabase()
    
    # Clear existing data
    print("Clearing existing questions...")
    with db.get_connection() as conn:
        conn.execute('DELETE FROM user_progress')
        conn.execute('DELETE FROM questions')
        conn.commit()
    
    # Load in batches
    total_loaded = 0
    for i in range(0, len(all_questions), batch_size):
        batch = all_questions[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        print(f"Loading batch {batch_num} ({i+1}-{min(i+batch_size, len(all_questions))})...")
        
        # Save batch to temporary file
        temp_file = f'data/temp_batch_{batch_num}.json'
        with open(temp_file, 'w') as f:
            json.dump(batch, f)
        
        # Load batch
        count = db.load_questions_from_json(temp_file)
        total_loaded += count
        
        print(f"  Loaded {count} questions (Total: {total_loaded:,})")
        
        # Clean up temp file
        os.remove(temp_file)
    
    # Final statistics
    print("\n" + "="*50)
    print(f"Loading complete!")
    print(f"Total questions loaded: {total_loaded:,}")
    
    # Get category stats
    categories = db.get_categories()
    print(f"Total categories: {len(categories):,}")
    
    print("\nTop 20 categories:")
    for cat, count in categories[:20]:
        print(f"  {cat}: {count} questions")
    
    # Verify total in database
    with db.get_connection() as conn:
        db_total = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
    
    print(f"\nVerified total in database: {db_total:,}")
    
    return total_loaded

if __name__ == "__main__":
    # Check if file is specified
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Default to J-Archive file
        json_file = 'data/jeopardy_github_100k.json'
    
    if not os.path.exists(json_file):
        print(f"Error: File {json_file} not found")
        sys.exit(1)
    
    # Load the questions
    total = load_in_batches(json_file, batch_size=5000)