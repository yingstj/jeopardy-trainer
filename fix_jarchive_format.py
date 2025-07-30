#!/usr/bin/env python3
"""
Fix J-Archive format where questions and answers are swapped.
In J-Archive format:
- 'answer' field contains the clue/question
- 'question' field contains the answer
"""

from database import JeopardyDatabase

def fix_question_answer_swap():
    """Swap question and answer fields in the database."""
    db = JeopardyDatabase()
    
    print("Fixing question/answer swap in J-Archive data...")
    
    with db.get_connection() as conn:
        # Get total count
        total = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
        print(f"Total questions to fix: {total:,}")
        
        # Swap question and answer fields
        print("Swapping question and answer fields...")
        conn.execute('''
            UPDATE questions 
            SET question = answer,
                answer = question
        ''')
        conn.commit()
        
        print("✓ Swap complete!")
        
        # Verify with samples
        print("\nVerifying with sample questions:")
        cursor = conn.execute('SELECT category, question, answer, value FROM questions LIMIT 5')
        
        for row in cursor:
            cat, q, a, val = row
            print(f"\nCategory: {cat}")
            print(f"Question: {q}")
            print(f"Answer: {a}")
            print(f"Value: ${val if val else 0}")

if __name__ == "__main__":
    fix_question_answer_swap()