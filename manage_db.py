#!/usr/bin/env python3
"""
Database management script for Jeopardy AI Trainer.
Provides easy commands for common database operations.
"""

import os
import sys
import argparse
from database import JeopardyDatabase
from data_processor import JeopardyDataProcessor

def init_database():
    """Initialize database tables."""
    print("Initializing database...")
    try:
        db = JeopardyDatabase()
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def load_sample_data():
    """Load sample questions from JSON file."""
    print("Loading sample data...")
    try:
        db = JeopardyDatabase()
        
        # Try different possible locations for sample data
        sample_files = [
            'data/questions_sample.json',
            'questions_sample.json',
            'data/jeopardy_questions.json'
        ]
        
        loaded = False
        for file_path in sample_files:
            if os.path.exists(file_path):
                print(f"Found sample file: {file_path}")
                count = db.load_questions_from_json(file_path)
                print(f"✓ Loaded {count} questions")
                loaded = True
                break
        
        if not loaded:
            print("✗ No sample data file found")
            print("Please ensure you have one of these files:")
            for f in sample_files:
                print(f"  - {f}")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def show_stats():
    """Display database statistics."""
    print("\nDatabase Statistics")
    print("=" * 50)
    try:
        db = JeopardyDatabase()
        categories = db.get_categories()
        
        total_questions = sum(count for _, count in categories)
        print(f"Total Questions: {total_questions}")
        print(f"Total Categories: {len(categories)}")
        
        if categories:
            print("\nTop 5 Categories:")
            for cat, count in categories[:5]:
                print(f"  - {cat}: {count} questions")
        
        # Get some performance stats
        hardest = db.get_hardest_questions(limit=3)
        if hardest:
            print("\nHardest Questions (by success rate):")
            for i, q in enumerate(hardest, 1):
                print(f"  {i}. {q['category']} (Success: {q.get('success_rate', 0)}%)")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def reset_database():
    """Reset database (WARNING: Deletes all data)."""
    response = input("⚠️  This will DELETE all data. Are you sure? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        return False
    
    try:
        # For PostgreSQL, we need to drop and recreate tables
        db = JeopardyDatabase()
        with db.get_connection() as conn:
            if db.db_type == 'postgresql':
                cursor = conn.cursor()
                # Drop tables in correct order (foreign keys)
                tables = [
                    'performance_snapshots',
                    'user_progress', 
                    'user_sessions',
                    'questions',
                    'users'
                ]
                for table in tables:
                    cursor.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
                cursor.close()
            else:
                # For SQLite, just drop tables
                conn.executescript('''
                    DROP TABLE IF EXISTS performance_snapshots;
                    DROP TABLE IF EXISTS user_progress;
                    DROP TABLE IF EXISTS user_sessions;
                    DROP TABLE IF EXISTS questions;
                    DROP TABLE IF EXISTS users;
                ''')
            conn.commit()
        
        # Reinitialize
        db.init_db()
        print("✓ Database reset successfully")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Manage Jeopardy AI Trainer database')
    parser.add_argument('command', choices=['init', 'load', 'stats', 'reset', 'check'],
                       help='Command to execute')
    
    args = parser.parse_args()
    
    # Show current database configuration
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///data/jeopardy.db')
    db_type = 'PostgreSQL' if db_url.startswith('postgresql://') else 'SQLite'
    print(f"Using {db_type} database")
    
    # Execute command
    if args.command == 'init':
        success = init_database()
    elif args.command == 'load':
        success = load_sample_data()
    elif args.command == 'stats':
        success = show_stats()
    elif args.command == 'reset':
        success = reset_database()
    elif args.command == 'check':
        # Import and run check_db
        from check_db import check_database
        success = check_database()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()