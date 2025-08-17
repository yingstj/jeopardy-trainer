#!/usr/bin/env python3
"""
Validate Jeopardy data for corrupted answers
"""
import pandas as pd
import sys
import re

def validate_csv(filepath):
    """Check CSV for data quality issues"""
    print(f"Validating {filepath}...")
    
    df = pd.read_csv(filepath)
    print(f"Total rows: {len(df):,}")
    
    # Check for dollar amounts as answers
    dollar_pattern = r'^\$\d+\s+\d+$'
    bad_answers = df[df['correct_response'].str.contains(dollar_pattern, na=False, regex=True)]
    
    if len(bad_answers) > 0:
        print(f"\n❌ FOUND {len(bad_answers)} CORRUPTED ANSWERS with dollar amounts:")
        print(bad_answers[['category', 'clue', 'correct_response']].head(10))
        return False
    
    # Check for NaN values
    null_clues = df['clue'].isna().sum()
    null_answers = df['correct_response'].isna().sum()
    
    if null_clues > 0:
        print(f"\n⚠️  Found {null_clues} missing clues")
    if null_answers > 0:
        print(f"\n⚠️  Found {null_answers} missing answers")
    
    # Check for specific known bad examples
    foot_clue = df[df['clue'].str.contains('foot care specialist', case=False, na=False)]
    if not foot_clue.empty:
        answer = foot_clue.iloc[0]['correct_response']
        if 'podiatrist' in answer.lower():
            print(f"\n✅ Foot care specialist answer is correct: {answer}")
        else:
            print(f"\n❌ Foot care specialist has wrong answer: {answer}")
            return False
    
    print(f"\n✅ Data validation passed! {len(df):,} clean clues.")
    return True

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/all_jeopardy_clues.csv"
    
    if not validate_csv(filepath):
        print("\n⚠️  DATA NEEDS TO BE RE-SCRAPED!")
        sys.exit(1)