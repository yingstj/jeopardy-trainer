#!/usr/bin/env python3
"""Test Railway PostgreSQL connection"""
import os
import psycopg2

# Get DATABASE_URL from environment
db_url = os.environ.get('DATABASE_URL')
print(f"DATABASE_URL: {db_url[:50]}..." if db_url else "DATABASE_URL not set")

if db_url:
    try:
        # Try to connect
        print("Attempting to connect...")
        conn = psycopg2.connect(db_url)
        print("✓ Connected successfully!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"PostgreSQL version: {version[0][:50]}...")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"✗ Connection failed: {e}")
else:
    print("Please set DATABASE_URL environment variable")