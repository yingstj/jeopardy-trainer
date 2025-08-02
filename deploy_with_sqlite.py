#!/usr/bin/env python3
"""
Deploy to Railway with SQLite database included
"""
import shutil
import os

print("Preparing SQLite deployment...")

# Copy the populated database
if os.path.exists('data/jeopardy.db'):
    size = os.path.getsize('data/jeopardy.db') / (1024 * 1024)
    print(f"Database size: {size:.1f} MB")
    print("Note: Large SQLite databases may have performance issues on Railway")
    
    # Create a backup
    shutil.copy2('data/jeopardy.db', 'data/jeopardy_backup.db')
    print("Created backup at data/jeopardy_backup.db")
    
    print("\nTo deploy with SQLite:")
    print("1. Remove DATABASE_URL from Railway variables")
    print("2. Run: railway up")
    print("\nWarning: SQLite is not recommended for production!")
else:
    print("No database found. Run load_massive_csv.py first.")