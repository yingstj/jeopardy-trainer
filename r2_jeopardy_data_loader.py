"""
R2 Jeopardy Data Loader
Loads Jeopardy data from Cloudflare R2 storage
"""
import pandas as pd
import requests
from typing import Optional
import streamlit as st

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_jeopardy_data_from_r2() -> pd.DataFrame:
    """
    Load Jeopardy data from R2 storage or fallback sources
    """
    # Try primary sources in order
    sources = [
        "https://github.com/yingstj/jeopardy-trainer/raw/main/data/all_jeopardy_clues.csv",
        "https://raw.githubusercontent.com/yingstj/jeopardy-trainer/main/data/all_jeopardy_clues.csv",
    ]
    
    for url in sources:
        try:
            df = pd.read_csv(url)
            if not df.empty and len(df) > 100:
                return df
        except Exception as e:
            continue
    
    # If all sources fail, return sample data
    return pd.DataFrame({
        'category': ['HISTORY'] * 10 + ['SCIENCE'] * 10 + ['MOVIES'] * 10,
        'clue': [
            'This Founding Father invented the lightning rod',
            'Year the Declaration of Independence was signed',
            'The Louisiana Purchase doubled the size of the U.S. in this year',
            'This president was known as "The Great Communicator"',
            'The Battle of Gettysburg took place in this state',
            'This ship brought the Pilgrims to America in 1620',
            'He was the first person to sign the Declaration of Independence',
            'This city served as the first capital of the United States',
            'The California Gold Rush began in this year',
            'This purchase from Russia added 586,412 square miles to the U.S.',
            'This element has the atomic number 1',
            'The speed of light in a vacuum is approximately this many meters per second',
            'This scientist developed the theory of evolution by natural selection',
            'Water boils at this temperature in Celsius',
            'This planet is known as the Red Planet',
            'The human body has this many chromosomes',
            'This is the largest organ in the human body',
            'Photosynthesis converts carbon dioxide and water into glucose and this gas',
            'This force keeps planets in orbit around the sun',
            'DNA stands for this',
            'This movie won Best Picture at the 2020 Academy Awards',
            'This director helmed Jaws, E.T., and Jurassic Park',
            'This actor played Jack in Titanic',
            '"May the Force be with you" is from this film series',
            'This 1939 film features Dorothy and her dog Toto',
            'This actor played the Joker in The Dark Knight',
            'This film won 11 Oscars including Best Picture in 2004',
            'This Pixar film features a clownfish searching for his son',
            'This actor portrayed Iron Man in the Marvel Cinematic Universe',
            'This film features the line "I\'ll be back"'
        ],
        'correct_response': [
            'Benjamin Franklin', '1776', '1803', 'Ronald Reagan', 'Pennsylvania',
            'Mayflower', 'John Hancock', 'New York City', '1849', 'Alaska',
            'Hydrogen', '299,792,458', 'Charles Darwin', '100', 'Mars',
            '46', 'Skin', 'Oxygen', 'Gravity', 'Deoxyribonucleic acid',
            'Parasite', 'Steven Spielberg', 'Leonardo DiCaprio', 'Star Wars', 'The Wizard of Oz',
            'Heath Ledger', 'The Lord of the Rings: The Return of the King', 'Finding Nemo', 
            'Robert Downey Jr.', 'The Terminator'
        ],
        'round': ['Jeopardy'] * 15 + ['Double Jeopardy'] * 15,
        'game_id': [str(i//5) for i in range(30)],
        'value': [200, 400, 600, 800, 1000] * 6
    })