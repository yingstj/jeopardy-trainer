"""
R2 Jeopardy Data Loader
Loads Jeopardy data from Cloudflare R2 storage
"""
import os
from io import BytesIO
from typing import Optional

import boto3
import pandas as pd
import streamlit as st
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_jeopardy_data_from_r2() -> pd.DataFrame:
    """
    Load Jeopardy data from Cloudflare R2 storage or fallback sources.
    """
    df = _load_from_r2()
    if df is not None and not df.empty:
        return df

    df = _load_from_github()
    if df is not None and not df.empty:
        return df

    return _load_sample_data()


def _load_from_r2() -> Optional[pd.DataFrame]:
    """Attempt to load the dataset from Cloudflare R2 using S3-compatible API."""
    endpoint = _get_secret("R2_ENDPOINT_URL")
    access_key = _get_secret("R2_ACCESS_KEY")
    secret_key = _get_secret("R2_SECRET_KEY")
    bucket_name = _get_secret("R2_BUCKET_NAME") or "jeopardy-dataset"
    object_key = _get_secret("R2_FILE_KEY") or "all_jeopardy_clues.csv"
    region_name = _get_secret("R2_REGION_NAME") or os.getenv("R2_REGION_NAME", "auto")

    if not all([endpoint, access_key, secret_key, bucket_name, object_key]):
        return None

    try:
        session = boto3.session.Session()
        client = session.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name=region_name,
        )

        response = client.get_object(Bucket=bucket_name, Key=object_key)
        payload = response["Body"].read()
        return pd.read_csv(BytesIO(payload))
    except (ClientError, BotoCoreError, ValueError, pd.errors.ParserError):
        st.warning("Unable to load dataset from Cloudflare R2; falling back to public dataset.")
        return None


def _load_from_github() -> Optional[pd.DataFrame]:
    """Fallback to the public GitHub dataset."""
    sources = [
        "https://github.com/yingstj/jeopardy-trainer/raw/main/data/all_jeopardy_clues.csv",
        "https://raw.githubusercontent.com/yingstj/jeopardy-trainer/main/data/all_jeopardy_clues.csv",
    ]

    for url in sources:
        try:
            df = pd.read_csv(url)
            if not df.empty and len(df) > 100:
                return df
        except Exception:
            continue
    return None


def _load_sample_data() -> pd.DataFrame:
    """Return a small, static dataset suitable for local demos."""
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


def _get_secret(name: str) -> Optional[str]:
    """Fetch a secret value from Streamlit or environment variables."""
    if os.getenv(name):
        return os.getenv(name)
    try:
        return st.secrets[name]
    except (AttributeError, KeyError):
        return None
