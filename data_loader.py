"""
Consolidated data loader for Jaypardy
Prefers CSV (577k questions) then falls back to JSON samples
"""
import os
import json
import pandas as pd
from typing import Optional

try:
    import streamlit as st
    cache = st.cache_data
except Exception:
    def cache(func): 
        return func

@cache
def load_questions_prefer_csv(csv_path: str = "data/all_jeopardy_clues.csv") -> pd.DataFrame:
    """
    Load Jeopardy questions with CSV priority (577k dataset) and JSON fallbacks
    """
    # First try CSV (577k questions)
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            # Normalize expected columns for app.py usage
            cols = {c.lower(): c for c in df.columns}
            # Attempt to map common fields
            category = cols.get('category') or 'category'
            clue = cols.get('clue') or cols.get('question') or 'question'
            answer = cols.get('answer') or cols.get('correct_response') or 'answer'
            value = cols.get('value') or 'value'
            
            out = pd.DataFrame({
                'category': df[category] if category in df.columns else 'GENERAL',
                'question': df[clue] if clue in df.columns else df.iloc[:, 0],
                'answer': df[answer] if answer in df.columns else df.iloc[:, 1],
                'value': df[value] if value in df.columns else 200
            }).dropna(subset=['question','answer'])
            
            print(f"Loaded {len(out)} questions from CSV")
            return out
        except Exception as e:
            print(f"CSV loading failed: {e}, trying JSON fallbacks")
    
    # JSON fallbacks
    candidates = [
        "data/jeopardy_questions_fixed.json",
        "data/questions_sample.json",
        "data/comprehensive_questions.json",
        "data/jeopardy_questions.json",
        "jeopardy_questions.json",
        "data/questions.json",
        "questions.json"
    ]
    
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                print(f"Loaded {len(df)} questions from {p}")
                return df
            except Exception as e:
                print(f"Failed to load {p}: {e}")
                continue
    
    # Minimal sample fallback
    print("Warning: Using minimal sample dataset")
    return pd.DataFrame([
        {"category": "SCIENCE", "question": "This planet is known as the Red Planet", "answer": "Mars", "value": 200},
        {"category": "HISTORY", "question": "This president was the first President of the United States", "answer": "George Washington", "value": 200},
        {"category": "LITERATURE", "question": "This Shakespeare play features Romeo and Juliet", "answer": "Romeo and Juliet", "value": 200}
    ])