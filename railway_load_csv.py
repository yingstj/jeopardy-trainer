#!/usr/bin/env python3
"""
Load the massive J-Archive CSV into Railway's PostgreSQL database
Run this locally with Railway environment variables
"""

import os
import sys

# Import the load script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Get Railway environment variables
os.system("railway run python3 -c \"import os; print('DATABASE_URL:', os.environ.get('DATABASE_URL', 'NOT SET'))\"")

print("\nTo load 1.1M questions into Railway's PostgreSQL database, run:")
print("railway run python3 load_massive_csv.py")
print("\nThis will:")
print("1. Connect to Railway's PostgreSQL using environment variables")
print("2. Clear existing questions")
print("3. Load all 1.1M questions from your CSV file")
print("4. Take about 30-60 seconds to complete")
print("\nMake sure you have the CSV file at:")
print("/Users/julieyingst/Documents/jeopardy_ai/data/all_jeopardy_clues.csv")