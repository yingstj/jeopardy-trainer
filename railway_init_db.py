#!/usr/bin/env python3
"""
Simple database initialization script for Railway.
This runs directly on Railway to initialize PostgreSQL.
"""

import os
import sys

# Set DATABASE_URL environment variable for local testing if needed
if 'DATABASE_URL' not in os.environ:
    print("ERROR: DATABASE_URL not found in environment")
    sys.exit(1)

print(f"DATABASE_URL found: {os.environ['DATABASE_URL'][:30]}...")

try:
    from database import JeopardyDatabase
    
    print("Initializing database...")
    db = JeopardyDatabase()
    
    print("Database initialized successfully!")
    
    # Check if tables were created
    categories = db.get_categories()
    print(f"Found {len(categories)} categories in database")
    
except Exception as e:
    print(f"Error initializing database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)