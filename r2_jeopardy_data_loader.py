"""
R2 Jeopardy Data Loader
Loads Jeopardy data from Cloudflare R2 storage, with a local Parquet cache
on disk so subsequent server restarts are near-instant.
"""
import os
import threading
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

LOCAL_CACHE_PATH = Path("/tmp/jeopardy_clues.parquet")
SOURCE_MARKER_PATH = Path("/tmp/jeopardy_clues.source")

# Human-readable labels for where the current dataset came from.
SOURCE_R2 = "R2 live"
SOURCE_GITHUB = "GitHub fallback"
SOURCE_SAMPLE = "Sample data"
SOURCE_UNKNOWN = "Unknown"

_data_source = SOURCE_UNKNOWN


def get_data_source() -> str:
    """Return a label describing which source the loaded dataset came from."""
    return _data_source


def _set_data_source(source: str):
    global _data_source
    _data_source = source


def _write_source_marker(source: str):
    try:
        SOURCE_MARKER_PATH.write_text(source)
    except Exception:
        pass


def _read_source_marker() -> str:
    try:
        text = SOURCE_MARKER_PATH.read_text().strip()
        if text in (SOURCE_R2, SOURCE_GITHUB, SOURCE_SAMPLE):
            return text
    except Exception:
        pass
    return SOURCE_UNKNOWN

# Coordinates the background prewarm thread with the foreground loader so
# they don't race on the parquet file or do duplicate network fetches.
_load_lock = threading.Lock()
_prewarm_started = False
_prewarm_done = threading.Event()
_warned_r2 = False  # one-shot flag for surfacing the R2 fallback warning safely


def _atomic_write_parquet(df: pd.DataFrame) -> bool:
    """Write parquet to a unique temp file then atomically rename into place."""
    try:
        LOCAL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = LOCAL_CACHE_PATH.with_name(
            f".{LOCAL_CACHE_PATH.name}.{uuid.uuid4().hex}.tmp"
        )
        df.to_parquet(tmp, index=False)
        os.replace(tmp, LOCAL_CACHE_PATH)
        return True
    except Exception:
        try:
            if 'tmp' in locals() and tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return False


def _fetch_dataset() -> Optional[pd.DataFrame]:
    """Network fetch with R2 → GitHub fallback. Safe to call from any thread."""
    df = _load_from_r2()
    source = SOURCE_R2
    if df is None or df.empty:
        df = _load_from_github()
        source = SOURCE_GITHUB
    if df is None or df.empty:
        return None
    _set_data_source(source)
    _write_source_marker(source)
    return df


def _prewarm_worker():
    """Background worker that downloads + writes the parquet cache."""
    global _prewarm_started
    try:
        with _load_lock:
            if LOCAL_CACHE_PATH.exists():
                return
            df = _fetch_dataset()
            if df is None or df.empty:
                # Allow a future call to retry prewarming this process.
                _prewarm_started = False
                return
            _atomic_write_parquet(df)
    finally:
        _prewarm_done.set()


def start_prewarm():
    """Kick off a one-time background download so the first user doesn't wait."""
    global _prewarm_started
    with _load_lock:
        if _prewarm_started or LOCAL_CACHE_PATH.exists():
            _prewarm_started = True
            _prewarm_done.set()
            return
        _prewarm_started = True
    t = threading.Thread(target=_prewarm_worker, daemon=True, name="jeopardy-prewarm")
    t.start()


@st.cache_resource(ttl=86400)
def load_jeopardy_data_from_r2() -> pd.DataFrame:
    """
    Load Jeopardy data with three tiers of caching:
      1. In-memory (Streamlit cache_resource — same process, no serialization)
      2. Local disk Parquet (survives server restarts, ~0.3s read)
      3. R2 / GitHub network fetch (slow, ~5s)
    """
    # If a prewarm is in flight, wait briefly so we don't double-fetch and
    # so we don't read a partially-written parquet file.
    if _prewarm_started and not _prewarm_done.is_set():
        _prewarm_done.wait(timeout=8)

    with _load_lock:
        if LOCAL_CACHE_PATH.exists():
            try:
                df = pd.read_parquet(LOCAL_CACHE_PATH)
                _set_data_source(_read_source_marker())
                _surface_pending_warnings()
                return df
            except Exception:
                try:
                    LOCAL_CACHE_PATH.unlink()
                except Exception:
                    pass

        df = _fetch_dataset()
        if df is None or df.empty:
            df = _load_sample_data()
            _set_data_source(SOURCE_SAMPLE)
        else:
            _atomic_write_parquet(df)

    _surface_pending_warnings()
    return df


def _surface_pending_warnings():
    """Emit any background-collected warnings on the foreground (Streamlit) thread."""
    global _warned_r2
    if _warned_r2:
        try:
            st.warning("Unable to load dataset from Cloudflare R2; using fallback source.")
        except Exception:
            pass
        _warned_r2 = False


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
        import boto3
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError

        session = boto3.session.Session()
        client = session.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                signature_version="s3v4",
                connect_timeout=10,
                read_timeout=45,
                retries={"max_attempts": 1},
            ),
            region_name=region_name,
        )

        response = client.get_object(Bucket=bucket_name, Key=object_key)
        payload = response["Body"].read()
        return pd.read_csv(BytesIO(payload))
    except Exception:
        # Defer UI notification — this may run on a background thread without
        # a Streamlit script context. The flag is consumed by the foreground
        # loader on its next run.
        global _warned_r2
        _warned_r2 = True
        return None


def _load_from_github() -> Optional[pd.DataFrame]:
    """Fallback to the public GitHub dataset."""
    import requests
    from io import StringIO

    sources = [
        "https://github.com/yingstj/jeopardy-trainer/raw/main/data/all_jeopardy_clues.csv",
        "https://raw.githubusercontent.com/yingstj/jeopardy-trainer/main/data/all_jeopardy_clues.csv",
    ]

    for url in sources:
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            df = pd.read_csv(StringIO(resp.text))
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
