#!/usr/bin/env python3
"""
Fix database by clearing bad questions and loading good ones.
"""

import os
from database import JeopardyDatabase

def fix_database():
    print("Fixing database...")
    
    db = JeopardyDatabase()
    print(f"Using {db.db_type} database")
    
    # Clear all questions
    print("Clearing old questions with bad answers...")
    with db.get_connection() as conn:
        if db.db_type == 'postgresql':
            cursor = conn.cursor()
            # Clear in correct order due to foreign keys
            cursor.execute('DELETE FROM user_progress')
            cursor.execute('DELETE FROM questions')
            conn.commit()
            cursor.close()
        else:
            conn.execute('DELETE FROM user_progress')
            conn.execute('DELETE FROM questions')
            conn.commit()
    
    print("Old questions cleared")
    
    # Load new questions
    print("Loading properly formatted questions...")
    try:
        count = db.load_questions_from_json('data/jeopardy_questions_fixed.json')
        print(f"Loaded {count} questions")
    except Exception as e:
        print(f"Error loading questions: {e}")
        return False
    
    # Verify
    print("\nVerifying...")
    questions = db.get_questions(count=5)
    print(f"Sample questions:")
    for q in questions[:3]:
        print(f"- {q['category']}: {q['question'][:50]}...")
        print(f"  Answer: {q['answer']}")
    
    return True

if __name__ == "__main__":
    fix_database()