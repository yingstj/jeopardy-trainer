#!/usr/bin/env python3
"""
Startup script that initializes database if needed before starting the app.
"""

import os
import sys
from database import JeopardyDatabase

def check_and_init_database():
    """Check if database is initialized, if not, initialize it."""
    try:
        db = JeopardyDatabase()
        
        # Check if we have any categories (indicates DB is initialized)
        categories = db.get_categories()
        
        if len(categories) == 0:
            print("Database is empty, initializing...")
            
            # Try to load sample data
            try:
                from data_processor import JeopardyDataProcessor
                processor = JeopardyDataProcessor()
                
                # Check for sample data file
                if os.path.exists('data/questions_sample.json'):
                    print("Loading sample questions...")
                    count = db.load_questions_from_json('data/questions_sample.json')
                    print(f"Loaded {count} questions")
                else:
                    print("No sample data found at data/questions_sample.json")
                    
            except Exception as e:
                print(f"Could not load sample data: {e}")
        else:
            print(f"Database already initialized with {len(categories)} categories")
            
    except Exception as e:
        print(f"Database check failed: {e}")
        # Don't exit - let the app start anyway

if __name__ == "__main__":
    print("Running startup checks...")
    check_and_init_database()
    
    # Now start the actual app
    from app import app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)