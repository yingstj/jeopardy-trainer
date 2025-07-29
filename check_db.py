#!/usr/bin/env python3
"""
Database status checker for Railway deployment.
This script helps verify database connection and content.
"""

import os
import sys
from database import JeopardyDatabase

def check_database():
    """Check database connection and display statistics."""
    print("=" * 60)
    print("Jeopardy AI Trainer - Database Status Check")
    print("=" * 60)
    
    try:
        # Get database URL
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            # Mask password in URL for display
            display_url = db_url.split('@')[0].rsplit(':', 1)[0] + ':***@' + db_url.split('@')[1] if '@' in db_url else db_url
            print(f"Database URL: {display_url}")
        else:
            print("Database URL: Using default SQLite database")
        
        # Initialize database
        print("\nInitializing database connection...")
        db = JeopardyDatabase(db_url)
        print("✓ Database connection successful")
        
        # Check categories
        print("\nChecking question categories...")
        categories = db.get_categories()
        print(f"✓ Found {len(categories)} categories")
        
        if categories:
            print("\nTop 10 categories:")
            for cat, count in categories[:10]:
                print(f"  - {cat}: {count} questions")
        
        # Get total question count
        total_questions = sum(count for _, count in categories)
        print(f"\n✓ Total questions in database: {total_questions}")
        
        # Check for users
        with db.get_connection() as conn:
            if db.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]
                cursor.close()
            else:
                user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        
        print(f"✓ Total users: {user_count}")
        
        # Test getting questions
        print("\nTesting question retrieval...")
        test_questions = db.get_questions(count=5)
        print(f"✓ Successfully retrieved {len(test_questions)} test questions")
        
        if test_questions:
            print("\nSample question:")
            q = test_questions[0]
            print(f"  Category: {q['category']}")
            print(f"  Question: {q['question'][:100]}...")
            print(f"  Answer: {q['answer']}")
            print(f"  Value: ${q['value']}")
        
        print("\n" + "=" * 60)
        print("✓ All database checks passed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure DATABASE_URL is set in Railway")
        print("2. Check that PostgreSQL addon is attached")
        print("3. Run 'python init_db.py' to initialize tables")
        print("4. Check Railway logs for more details")
        return False

if __name__ == '__main__':
    success = check_database()
    sys.exit(0 if success else 1)