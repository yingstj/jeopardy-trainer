import streamlit as st
import pandas as pd
import random
import re
import os
import datetime
import json
from collections import defaultdict
from typing import Dict, List
import numpy as np

# Import the R2 data loader
from r2_jeopardy_data_loader import (
    load_jeopardy_data_from_r2,
    start_prewarm,
    get_data_source,
    SOURCE_SAMPLE,
)

# Kick off background dataset download at server startup so the first user
# (often a guest) doesn't wait 20s for the R2 fetch.
start_prewarm()
from scheduled_refresh import start_scheduler
start_scheduler()
from auth_manager import AuthManager, stash_guest_progress
from category_analyzer import JeopardyCategoryAnalyzer
from database import (
    initialize_database,
    get_db_connection,
    save_bookmark,
    load_bookmarks,
    delete_bookmark,
)
from utils import apply_era_filter

# Sentinel value written into the answer input by the JS countdown's
# auto-submit handler. The Python grader uses this to distinguish a
# timer-triggered submit from a user-clicked submit. Must match the
# string used in the JS in the countdown component below.
AUTO_SUBMIT_TIMEOUT_SENTINEL = "__JPY_AUTO_SUBMIT_TIMEOUT__"

# Initialize the database (wrapped so a DB outage doesn't blank the app)
try:
    initialize_database()
except Exception as _db_init_err:
    import sys
    print(f"[startup] DB init warning: {_db_init_err}", file=sys.stderr)

class ChallengeManager:
    """SQLite-backed challenge manager using database.py schema."""
    def __init__(self):
        pass

    def _get_or_create_user(self, username: str) -> int:
        """Ensure a user exists in sqlite users table and return id."""
        if not username:
            return 0
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row:
            user_id = row["id"]
        else:
            cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, ""))
            user_id = cur.lastrowid
            # Initialize stats row
            cur.execute("INSERT INTO user_stats (user_id) VALUES (?)", (user_id,))
            conn.commit()
        conn.close()
        return int(user_id)

    def create_challenge(self, challenger_name: str, opponent_name: str, categories: list, num_questions: int = 10) -> int:
        challenger_id = self._get_or_create_user(challenger_name)
        opponent_id = self._get_or_create_user(opponent_name)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO challenges (challenger_id, opponent_id, status, num_questions, categories) VALUES (?, ?, 'pending', ?, ?)",
            (challenger_id, opponent_id, int(num_questions), json.dumps(categories or [])),
        )
        challenge_id = cur.lastrowid
        conn.commit()
        conn.close()
        return int(challenge_id)

    def accept_challenge(self, challenge_id: int, username: str) -> bool:
        user_id = self._get_or_create_user(username)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE challenges SET status = 'active' WHERE id = ? AND opponent_id = ?", (challenge_id, user_id))
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def complete_challenge(self, challenge_id: int, username: str, score: int) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        # Fetch current challenge
        cur.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,))
        ch = cur.fetchone()
        if not ch:
            conn.close()
            return False
        # Determine which side completed
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        user_id = row["id"]

        # Update scores and completed flags
        if ch["challenger_id"] == user_id:
            cur.execute("UPDATE challenges SET challenger_score = ?, challenger_completed = 1 WHERE id = ?", (int(score), challenge_id))
        elif ch["opponent_id"] == user_id:
            cur.execute("UPDATE challenges SET opponent_score = ?, opponent_completed = 1 WHERE id = ?", (int(score), challenge_id))
        else:
            conn.close()
            return False

        # If both completed, compute winner and mark completed
        cur.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,))
        ch2 = cur.fetchone()
        if ch2 and ch2["challenger_completed"] and ch2["opponent_completed"]:
            winner_id = None
            if ch2["challenger_score"] > ch2["opponent_score"]:
                winner_id = ch2["challenger_id"]
            elif ch2["opponent_score"] > ch2["challenger_score"]:
                winner_id = ch2["opponent_id"]
            cur.execute("UPDATE challenges SET status = 'completed', winner_id = ? WHERE id = ?", (winner_id, challenge_id))
        conn.commit()
        conn.close()
        return True

    def _by_user(self, username: str, where_clause: str):
        user_id = self._get_or_create_user(username)
        conn = get_db_connection()
        cur = conn.cursor()
        query = f"""
            SELECT c.*, u1.username as challenger, u2.username as opponent
            FROM challenges c
            JOIN users u1 ON u1.id = c.challenger_id
            JOIN users u2 ON u2.id = c.opponent_id
            WHERE (c.challenger_id = ? OR c.opponent_id = ?) AND {where_clause}
            ORDER BY c.created_at DESC
        """
        cur.execute(query, (user_id, user_id))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_active_challenges(self, username: str):
        return self._by_user(username, "c.status = 'active'")

    def get_pending_challenges(self, username: str):
        return self._by_user(username, "c.status = 'pending'")

    def get_completed_challenges(self, username: str):
        return self._by_user(username, "c.status = 'completed'")

# Page configuration with custom icon
st.set_page_config(
    page_title="Jayopardy!",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="auto"
)

# Custom CSS — Sophisticated editorial design system
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:ital,opsz,wght,SOFT@0,9..144,300..700,0..100;1,9..144,300..700,0..100&display=swap" rel="stylesheet">
<style>
    /* ── DESIGN TOKENS ───────────────────────────────────────────── */
    :root {
        /* Palette */
        --ink:        #1a1625;
        --ink-soft:   #3d3654;
        --muted:      #7c7492;
        --muted-2:    #a99fba;
        --bg:         #f9f7f4;
        --surface:    #ffffff;
        --surface-2:  #f4f1ed;
        --line:       #e8e3dc;
        --line-soft:  #f0ece6;

        /* Indigo sidebar / header */
        --indigo:     #1e1b4b;
        --indigo-mid: #312e81;
        --indigo-soft:#4338ca;

        /* Gold accent */
        --gold:       #92681d;
        --gold-light: #c9964a;
        --gold-bg:    #fdf8ef;
        --gold-line:  #e8d5a8;

        /* Feedback */
        --success:    #166534;
        --success-bg: #f0fdf4;
        --success-ln: #bbf7d0;
        --error:      #9b1c1c;
        --error-bg:   #fef2f2;
        --error-ln:   #fecaca;
        --warn-bg:    #fffbeb;
        --warn-ln:    #fde68a;
        --info-bg:    #eff6ff;
        --info-ln:    #bfdbfe;

        /* Ring / shadow */
        --ring:       rgba(146,104,29,0.22);
        --shadow-xs:  0 1px 3px rgba(26,22,37,0.06);
        --shadow-sm:  0 2px 8px rgba(26,22,37,0.08);
        --shadow-md:  0 4px 20px rgba(26,22,37,0.10);
    }

    /* ── BASE ────────────────────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--ink);
        background: var(--bg);
        -webkit-font-smoothing: antialiased;
    }
    .stApp { background: var(--bg); }

    /* ── LAYOUT ──────────────────────────────────────────────────── */
    .main { padding: 0 1rem; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; max-width: 860px; }

    /* ── TYPOGRAPHY ──────────────────────────────────────────────── */
    h1, h2, h3 {
        font-family: 'Fraunces', Georgia, serif !important;
        font-weight: 500 !important;
        color: var(--ink) !important;
        letter-spacing: -0.02em;
        font-variation-settings: "opsz" 72, "SOFT" 30;
    }

    /* ── MASTHEAD ────────────────────────────────────────────────── */
    .main-header {
        padding: 1.75rem 0 1.5rem;
        margin-bottom: 2rem;
        border-bottom: 1px solid var(--line);
        text-align: center;
    }
    .main-header::before {
        content: "TRIVIA TRAINING";
        display: block;
        color: var(--gold);
        font: 600 0.65rem 'Inter', sans-serif;
        letter-spacing: 0.25em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
    }
    .main-header h1 {
        font-family: 'Fraunces', Georgia, serif !important;
        font-size: clamp(2rem, 5vw, 3rem) !important;
        font-weight: 400 !important;
        font-style: italic;
        color: var(--indigo) !important;
        margin: 0 !important;
        letter-spacing: -0.03em;
        font-variation-settings: "opsz" 96, "SOFT" 50;
    }
    .main-header p {
        color: var(--muted);
        font-size: 0.88rem;
        margin-top: 0.4rem;
        font-style: italic;
    }
    .header-stats {
        display: flex;
        justify-content: center;
        gap: 2.5rem;
        margin-top: 1.5rem;
    }
    .header-stat { text-align: center; }
    .header-stat-value {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.75rem;
        font-weight: 400;
        color: var(--indigo);
        letter-spacing: -0.02em;
        line-height: 1;
        font-variation-settings: "opsz" 48;
    }
    .header-stat-label {
        font-size: 0.65rem;
        font-weight: 600;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.18em;
        margin-top: 0.3rem;
    }

    /* ── CATEGORY LABEL ──────────────────────────────────────────── */
    .theme-card {
        color: var(--gold);
        background: var(--gold-bg);
        border: 1px solid var(--gold-line);
        padding: 0.45rem 0.9rem 0.4rem;
        margin-bottom: 0.75rem;
        font: 600 0.7rem 'Inter', sans-serif;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        border-radius: 3px;
        display: inline-block;
    }

    /* ── CLUE CARD ───────────────────────────────────────────────── */
    .clue-card {
        background: var(--surface);
        border: 1px solid var(--line);
        padding: clamp(1.75rem,4vw,2.5rem) clamp(1.5rem,4vw,2.25rem);
        border-radius: 8px;
        margin: 1rem 0 1.25rem;
        box-shadow: var(--shadow-sm);
        position: relative;
    }
    .clue-card::before {
        content: "";
        position: absolute;
        left: 0; top: 0;
        width: 3px; height: 100%;
        background: var(--indigo-soft);
        border-radius: 8px 0 0 8px;
    }
    .clue-text {
        font-family: 'Fraunces', Georgia, serif;
        font-weight: 400;
        font-size: clamp(1.2rem, 2.5vw, 1.6rem);
        color: var(--ink);
        line-height: 1.6;
        letter-spacing: -0.01em;
        text-align: center;
        font-variation-settings: "opsz" 48, "SOFT" 20;
    }

    /* ── SCORE / STAT CARDS ──────────────────────────────────────── */
    .score-container, .stat-card {
        background: var(--surface);
        border: 1px solid var(--line);
        padding: 1rem 0.9rem;
        border-radius: 6px;
        text-align: center;
        box-shadow: var(--shadow-xs);
    }
    .score-label, .stat-label {
        font-size: 0.63rem;
        font-weight: 600;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.18em;
        margin-bottom: 0.3rem;
    }
    .score-value {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.9rem;
        font-weight: 400;
        color: var(--indigo);
        letter-spacing: -0.025em;
        font-variation-settings: "opsz" 48;
    }
    .stat-number {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.65rem;
        font-weight: 400;
        color: var(--indigo);
        letter-spacing: -0.025em;
    }

    /* ── TIMER ───────────────────────────────────────────────────── */
    .timer-container {
        background: var(--surface);
        border: 1px solid var(--line);
        padding: 0.7rem 1rem;
        border-radius: 6px;
        text-align: center;
        margin-bottom: 1rem;
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--ink);
    }

    /* ── PROGRESS BAR ────────────────────────────────────────────── */
    .progress-bar {
        background: var(--surface-2);
        border: 1px solid var(--line);
        height: 5px;
        border-radius: 99px;
        overflow: hidden;
        margin: 0.65rem 0;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--indigo-soft), var(--indigo));
        transition: width 0.45s ease;
        font-size: 0;
    }

    /* ── BUTTONS ─────────────────────────────────────────────────── */
    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        background: var(--indigo);
        color: #ffffff !important;
        border: 1px solid var(--indigo);
        padding: 0.55rem 1.4rem;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em;
        border-radius: 5px;
        box-shadow: none;
        transition: background 0.15s ease, transform 0.1s ease;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover {
        background: var(--indigo-mid);
        border-color: var(--indigo-mid);
        transform: translateY(-1px);
        box-shadow: var(--shadow-sm);
    }
    .stButton > button:active,
    .stFormSubmitButton > button:active { transform: translateY(0); box-shadow: none; }
    .stButton > button:focus,
    .stFormSubmitButton > button:focus { box-shadow: 0 0 0 3px var(--ring) !important; }

    /* Gold variant for primary actions */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {
        background: var(--gold);
        border-color: var(--gold);
    }
    .stButton > button[kind="primary"]:hover { background: #7a571a; border-color: #7a571a; }

    /* ── INPUTS ──────────────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stNumberInput input,
    .stSelectbox [data-baseweb="select"] > div {
        background: var(--surface) !important;
        border: 1px solid var(--line) !important;
        border-radius: 5px !important;
        color: var(--ink) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.93rem !important;
        transition: border-color 0.15s, box-shadow 0.15s;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus,
    .stNumberInput input:focus {
        border-color: var(--indigo-soft) !important;
        box-shadow: 0 0 0 3px rgba(67,56,202,0.12) !important;
    }
    input::placeholder, textarea::placeholder { color: var(--muted-2) !important; }

    /* ── TABS ────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] { gap: 1.75rem; border-bottom: 1px solid var(--line); }
    .stTabs [data-baseweb="tab"] {
        padding: 0.6rem 0;
        font-weight: 500;
        color: var(--muted);
        font-size: 0.9rem;
        letter-spacing: 0.005em;
    }
    .stTabs [aria-selected="true"] { color: var(--indigo) !important; font-weight: 600; }
    .stTabs [data-baseweb="tab-highlight"] { background: var(--indigo) !important; height: 2px !important; }

    /* ── SIDEBAR ─────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: var(--indigo) !important;
        border-right: none;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12); }
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] li { color: rgba(255,255,255,0.85) !important; }
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--gold-light) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.2em;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] .stTextInput > div > div > input,
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.08) !important;
        border-color: rgba(255,255,255,0.18) !important;
        color: #fff !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.12);
        border-color: rgba(255,255,255,0.2);
        color: #fff !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.2);
        transform: none;
        box-shadow: none;
    }
    [data-testid="stCheckbox"] label { color: rgba(255,255,255,0.85) !important; }
    [data-testid="stSidebar"] [data-testid="stCheckbox"] span { border-color: rgba(255,255,255,0.35) !important; }
    [data-testid="stSlider"] [role="slider"] { background: var(--gold-light) !important; border-color: var(--gold-light) !important; }
    [data-testid="stSlider"] [data-testid="stSlider"] div[role="progressbar"] { background: var(--gold-light) !important; }

    /* ── ALERTS ──────────────────────────────────────────────────── */
    [data-testid="stAlert"] { border-radius: 6px !important; }
    div[data-testid="stAlertContentSuccess"] {
        background: var(--success-bg) !important;
        border: 1px solid var(--success-ln) !important;
        color: var(--success) !important;
    }
    div[data-testid="stAlertContentError"] {
        background: var(--error-bg) !important;
        border: 1px solid var(--error-ln) !important;
        color: var(--error) !important;
    }
    div[data-testid="stAlertContentWarning"] {
        background: var(--warn-bg) !important;
        border: 1px solid var(--warn-ln) !important;
        color: #78350f !important;
    }
    div[data-testid="stAlertContentInfo"] {
        background: var(--info-bg) !important;
        border: 1px solid var(--info-ln) !important;
        color: #1e40af !important;
    }

    /* ── EXPANDER / FORM / DATAFRAME ─────────────────────────────── */
    [data-testid="stExpander"],
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] details summary {
        background: var(--surface) !important;
        border: 1px solid var(--line) !important;
        border-radius: 6px !important;
        color: var(--ink) !important;
    }
    [data-testid="stForm"] {
        border: 1px solid var(--line) !important;
        border-radius: 8px !important;
        background: var(--surface);
    }
    [data-testid="stDataFrame"], .stDataFrame {
        border: 1px solid var(--line) !important;
        border-radius: 6px;
        overflow: hidden;
    }
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [data-baseweb="list"] { background: var(--surface) !important; color: var(--ink) !important; }
    [data-baseweb="menu"] li:hover,
    [data-baseweb="menu"] li[aria-selected="true"] { background: var(--surface-2) !important; }

    /* ── OVERLINE ────────────────────────────────────────────────── */
    .overline {
        font-size: 0.65rem;
        font-weight: 700;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.2em;
    }

    /* ── MISC ────────────────────────────────────────────────────── */
    .stMarkdown, .stText, p, li { color: var(--ink); }
    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--muted) !important;
        font-style: italic;
        font-size: 0.83rem !important;
    }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    /* Signed-in badge */
    .signed-in-badge {
        display: inline-block;
        padding: 0.22rem 0.55rem;
        background: rgba(201,150,74,0.15);
        border: 1px solid rgba(201,150,74,0.35);
        border-radius: 3px;
        color: var(--gold-light);
        font: 600 0.63rem 'Inter', sans-serif;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }

    /* ── BUZZER PANEL (AI mode) ──────────────────────────────────── */
    .buzzer-panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-top: 2px solid var(--gold);
        border-radius: 6px;
        padding: 1rem 1.25rem 0.9rem;
        text-align: center;
        margin: 0.5rem 0 1rem;
        box-shadow: var(--shadow-xs);
    }
    .buzzer-panel .bp-title {
        font: 600 0.65rem 'Inter', sans-serif;
        color: var(--gold);
        letter-spacing: 0.22em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .buzzer-panel .bp-text {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.15rem;
        font-weight: 500;
        color: var(--ink);
        letter-spacing: -0.01em;
    }

    @media (max-width: 700px) {
        .block-container { padding-top: 1.25rem; }
        .header-stats { gap: 1.25rem; }
        .main-header { margin-bottom: 1.25rem; }
        .main-header { padding: 1.25rem 0 1rem; }
        .header-stat-value { font-size: 1.4rem; }
        .clue-text { font-size: 1.1rem; }
        .clue-card { margin: 0.75rem 0 1rem; }
        .score-value { font-size: 1.6rem; }
        .stat-number { font-size: 1.35rem; }
        .buzzer-panel .bp-text { font-size: 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# Load and filter data
def load_data():
    """Public entry point; keys the cached load to the bundled CSV revision
    so a running app serves freshly refreshed clues without a restart."""
    from r2_jeopardy_data_loader import _dataset_version
    return _load_data_cached(_dataset_version())

@st.cache_data
def _load_data_cached(dataset_version: float):
    # Check if we're in a GitHub Actions environment (for CI testing)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        # Return a small sample dataset for testing
        return pd.DataFrame({
            'category': ['HISTORY', 'SCIENCE', 'MOVIES', 'LITERATURE', 'GEOGRAPHY'],
            'clue': ['First president of the US', 'Element with symbol H', 'This film won Best Picture in 2020', 
                    'Author of Romeo and Juliet', 'Capital of France'],
            'correct_response': ['George Washington', 'Hydrogen', 'Parasite', 'William Shakespeare', 'Paris'],
            'round': ['Jeopardy', 'Jeopardy', 'Double Jeopardy', 'Jeopardy', 'Final Jeopardy'],
            'game_id': ['1', '1', '2', '2', '3']
        })
    
    try:
        # Load from R2 (with GitHub / sample fallbacks handled inside the loader)
        with st.spinner("📚 Loading clue library… this can take a few seconds on a fresh start."):
            df = load_jeopardy_data_from_r2()

        if df.empty:
            st.error("The clue library couldn't be loaded. Please check your connection and try again.")
            return pd.DataFrame()
        
        df = df.dropna(subset=["clue", "correct_response"])
        return df
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Initialize auth manager
auth = AuthManager()

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "user_data" not in st.session_state:
    st.session_state.user_data = None

if "history" not in st.session_state:
    st.session_state.history = []

if "score" not in st.session_state:
    st.session_state.score = 0
    st.session_state.total = 0

if "start_time" not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()

if "current_clue" not in st.session_state:
    st.session_state.current_clue = None

if "progress_data" not in st.session_state:
    st.session_state.progress_data = []

if "streak" not in st.session_state:
    st.session_state.streak = 0
    st.session_state.best_streak = 0

if "bookmarks" not in st.session_state:
    st.session_state.bookmarks = []

if "notes" not in st.session_state:
    st.session_state.notes = {}

if "daily_double_used" not in st.session_state:
    st.session_state.daily_double_used = False

if "achievements" not in st.session_state:
    st.session_state.achievements = []

if "study_mode" not in st.session_state:
    st.session_state.study_mode = False

if "weak_themes" not in st.session_state:
    st.session_state.weak_themes = {}

if "viewing_bookmark" not in st.session_state:
    st.session_state.viewing_bookmark = None

if "is_signed_in" not in st.session_state:
    st.session_state.is_signed_in = False

def check_signed_in_status():
    # All signed-in (non-guest) users have full access.
    st.session_state.is_signed_in = not st.session_state.get("is_guest", True)

def _bookmark_key(b: dict):
    return (b.get("category"), b.get("clue"), b.get("correct_response"))

def bookmark_identity():
    """Stable, unique identity for bookmark ownership: the authenticated
    email (normalized to lowercase). Never a display name, which is not
    unique across accounts. Returns None for guests or unauthenticated
    sessions."""
    if not st.session_state.get("is_signed_in"):
        return None
    email = (st.session_state.get("user_email") or "").strip().lower()
    if not email or email == "guest@jayopardy.app":
        return None
    return email

def restore_bookmarks_from_db():
    """Load a signed-in player's bookmarks from the database into session
    state (once per sign-in). The database copy is authoritative — session
    bookmarks are replaced, never migrated into another account. Guests are
    untouched — their bookmarks stay session-only."""
    identity = bookmark_identity()
    if not identity or st.session_state.get("bookmarks_loaded_for") == identity:
        return
    try:
        st.session_state.bookmarks = load_bookmarks(identity)
        st.session_state.bookmarks_loaded_for = identity
    except Exception as e:
        import sys
        print(f"[bookmarks] restore failed: {e}", file=sys.stderr)

def guest_sign_in_button(key: str, label: str = "🔑 Sign in", use_container_width: bool = True):
    """Render a button that ends the guest session and returns to the login page."""
    if st.button(label, key=key, use_container_width=use_container_width):
        # Keep the guest's in-progress game so it survives sign-up,
        # then show the login page
        stash_guest_progress()
        st.session_state.bookmarks = []
        st.session_state.bookmarks_loaded_for = None
        st.session_state.authenticated = False
        st.session_state.is_guest = False
        st.session_state.is_signed_in = False
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.rerun()

if "ai_mode" not in st.session_state:
    st.session_state.ai_mode = False
    st.session_state.ai_difficulty = "Medium"
    st.session_state.ai_personality = "Balanced"
    st.session_state.ai_score = 0
    st.session_state.ai_streak = 0
    st.session_state.current_turn = "player"
    st.session_state.buzzer_winner = None
    st.session_state.ai_thinking = False
    st.session_state.match_history = []

# AI Personalities with different strengths
AI_PERSONALITIES = {
    "Ken Jennings": {
        "description": "All-around expert, especially strong in History and Literature",
        "strengths": ["HISTORY", "LITERATURE", "GEOGRAPHY", "WORDPLAY"],
        "weaknesses": ["POP CULTURE", "SPORTS"],
        "base_accuracy": 0.85,
        "speed": "fast"
    },
    "Watson": {
        "description": "Computer-like precision, excels at facts and data",
        "strengths": ["SCIENCE", "TECHNOLOGY", "BUSINESS", "MEDICINE"],
        "weaknesses": ["WORDPLAY", "POP CULTURE"],
        "base_accuracy": 0.90,
        "speed": "very fast"
    },
    "Brad Rutter": {
        "description": "Strategic player, strong in Entertainment and Pop Culture",
        "strengths": ["ENTERTAINMENT", "POP CULTURE", "SPORTS", "MUSIC"],
        "weaknesses": ["SCIENCE", "TECHNOLOGY"],
        "base_accuracy": 0.82,
        "speed": "medium"
    },
    "James Holzhauer": {
        "description": "Aggressive player, sports and gambling expert",
        "strengths": ["SPORTS", "GEOGRAPHY", "BUSINESS", "POLITICS"],
        "weaknesses": ["ART", "LITERATURE"],
        "base_accuracy": 0.88,
        "speed": "very fast"
    },
    "Balanced": {
        "description": "Average player with no particular strengths",
        "strengths": [],
        "weaknesses": [],
        "base_accuracy": 0.75,
        "speed": "medium"
    }
}

# AI Difficulty Settings
AI_DIFFICULTY = {
    "Easy": {
        "accuracy_modifier": -0.20,
        "buzzer_speed": 10.0,  # 10 seconds to buzz in
        "daily_double_aggression": 0.3
    },
    "Medium": {
        "accuracy_modifier": 0,
        "buzzer_speed": 5.0,  # 5 seconds to buzz in
        "daily_double_aggression": 0.5
    },
    "Hard": {
        "accuracy_modifier": 0.10,
        "buzzer_speed": 2.0,  # 2 seconds to buzz in
        "daily_double_aggression": 0.8
    }
}

@st.cache_resource
def load_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")

def normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"^(what|who|where|when|why|how)\s+(is|are|was|were)\s+", "", text)
    text = re.sub(r"^(a|an|the)\s+", "", text)  # Remove articles
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()

def fuzzy_match(user_answer: str, correct_answer: str, threshold: int = 70) -> bool:
    user_norm = normalize(user_answer)
    correct_norm = normalize(correct_answer)
    if user_norm == correct_norm:
        return True

    correct_words = correct_norm.split()
    user_words = user_norm.split()

    if len(correct_words) >= 2 and len(user_words) == 1:
        if user_norm == correct_words[-1]:
            return True
        for word in correct_words:
            if len(word) > 4 and user_norm == word:
                return True

    if len(user_words) > 1 and len(correct_words) > 1:
        if user_words[-1] == correct_words[-1]:
            return True

    if len(user_norm) > 3 and len(correct_norm) > 3:
        if user_norm in correct_norm and len(user_norm) / len(correct_norm) > 0.4:
            return True
        if correct_norm in user_norm:
            return True

    if len(user_norm) <= 3 or len(correct_norm) <= 3:
        return user_norm == correct_norm

    if len(correct_words) > 1 and len(user_words) > 0:
        matching_words = sum(1 for word in user_words if word in correct_words)
        if matching_words / len(correct_words) >= 0.5:
            return True

    max_len = max(len(user_norm), len(correct_norm))
    if max_len == 0:
        return False
    differences = abs(len(user_norm) - len(correct_norm))
    min_len = min(len(user_norm), len(correct_norm))
    for i in range(min_len):
        if user_norm[i] != correct_norm[i]:
            differences += 1
    similarity = ((max_len - differences) / max_len) * 100
    return similarity >= threshold

def find_similar_clues(df: pd.DataFrame, target_clue: str, top_k: int = 3) -> pd.DataFrame:
    try:
        if df.empty or not target_clue:
            return pd.DataFrame()
        working_df = df.copy()
        if len(working_df) > 1000:
            working_df = working_df.sample(n=1000, random_state=42)
        texts = working_df["clue"].astype(str).tolist()
        embeddings = compute_embeddings_for_texts(texts)
        target_vec = load_model().encode(target_clue).reshape(1, -1)
        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity(target_vec, embeddings)[0]
        working_df = working_df.assign(_sim=sims)
        results = working_df[working_df["clue"] != target_clue].sort_values("_sim", ascending=False).head(top_k)
        return results[["category", "clue", "correct_response"]]
    except Exception:
        return pd.DataFrame()

@st.cache_data
def compute_embeddings_for_texts(texts: List[str]) -> np.ndarray:
    m = load_model()
    return np.vstack([m.encode(t) for t in texts])

def parse_clue_value(value) -> int:
    """Parse clue value like 200 or '$1,000' to an int. Fallback to 200."""
    try:
        if value is None:
            return 200
        if isinstance(value, (int, float)):
            return int(value)
        s = str(value)
        s = s.replace("$", "").replace(",", "").strip()
        if s.isdigit():
            return int(s)
        return int(float(s))
    except Exception:
        return 200

def simulate_ai_response(clue, category, difficulty, personality):
    """Simulate AI response based on difficulty and personality"""
    import time
    
    personality_data = AI_PERSONALITIES[personality]
    difficulty_data = AI_DIFFICULTY[difficulty]
    
    # Calculate accuracy based on personality and difficulty
    base_accuracy = personality_data["base_accuracy"]
    
    # Adjust for category strengths/weaknesses
    themes = analyzer.categorize_single(category)
    theme = themes[0] if isinstance(themes, list) and themes else (themes if isinstance(themes, str) else "MISCELLANEOUS")
    if theme in personality_data["strengths"]:
        base_accuracy += 0.15
    elif theme in personality_data["weaknesses"]:
        base_accuracy -= 0.20
    
    # Apply difficulty modifier
    final_accuracy = min(0.99, max(0.20, base_accuracy + difficulty_data["accuracy_modifier"]))
    
    # Determine if AI gets it right
    is_correct = random.random() < final_accuracy
    
    # Simulate thinking time based on personality speed
    speed_map = {
        "very fast": (0.5, 1.5),
        "fast": (1.0, 2.0),
        "medium": (1.5, 3.0),
        "slow": (2.0, 4.0)
    }
    min_time, max_time = speed_map[personality_data["speed"]]
    thinking_time = random.uniform(min_time, max_time)
    
    return is_correct, thinking_time

def simulate_buzzer_race(difficulty):
    """Simulate who wins the buzzer"""
    difficulty_data = AI_DIFFICULTY[difficulty]
    
    # Player reaction time (random between 0.5 and buzzer_speed seconds)
    max_player_time = difficulty_data["buzzer_speed"]
    player_time = random.uniform(0.5, max_player_time)
    
    # AI reaction time based on difficulty (will try to buzz somewhere in the time window)
    if difficulty == "Easy":
        # AI buzzes slowly on easy mode (7-10 seconds)
        ai_time = random.uniform(7.0, 10.0)
    elif difficulty == "Medium":
        # AI buzzes moderately on medium (3-5 seconds)
        ai_time = random.uniform(3.0, 5.0)
    else:  # Hard
        # AI buzzes quickly on hard (1-2 seconds)
        ai_time = random.uniform(1.0, 2.0)
    
    if player_time < ai_time:
        return "player", player_time
    else:
        return "ai", ai_time

def get_ai_daily_double_wager(ai_score, player_score, difficulty):
    """Determine AI's wager on Daily Double"""
    difficulty_data = AI_DIFFICULTY[difficulty]
    aggression = difficulty_data["daily_double_aggression"]
    
    # Base wager calculation
    if ai_score <= 0:
        max_wager = 1000
    else:
        max_wager = ai_score
    
    # Adjust based on game situation
    if ai_score < player_score:
        # Behind - more aggressive
        wager_percent = min(1.0, aggression + 0.2)
    elif ai_score > player_score * 2:
        # Way ahead - conservative
        wager_percent = max(0.2, aggression - 0.3)
    else:
        # Close game - normal aggression
        wager_percent = aggression
    
    wager = int(max_wager * wager_percent)
    return max(100, min(wager, max_wager))

if "selected_categories" not in st.session_state:
    st.session_state.selected_categories = None

if "time_limit" not in st.session_state:
    st.session_state.time_limit = 30
if "use_timer" not in st.session_state:
    st.session_state.use_timer = True
if "time_limit_slider" not in st.session_state:
    st.session_state.time_limit_slider = 30
if "speed_round" not in st.session_state:
    st.session_state.speed_round = False

# Login Screen via AuthManager (email/guest and optional Google OAuth)
if not st.session_state.get("authenticated", False):
    auth.show_login_page()
    st.stop()

# Loading data (only after authentication)
df = load_data()

if df.empty:
    st.error("❌ Failed to load Jeopardy dataset.")
    st.info("Check your internet connection or contact the administrator.")
    st.stop()

if get_data_source() == SOURCE_SAMPLE:
    st.warning(
        "⚠️ The full clue library couldn't be reached, so you're playing with a "
        "small built-in sample set. Refresh in a minute to try again."
    )

# Database health check (cached briefly so we don't ping the DB on every rerun)
@st.cache_data(ttl=60, show_spinner=False)
def is_database_available() -> bool:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        conn.close()
        return True
    except Exception:
        return False

# Initialize analyzer and categories (cached so this only runs once per server lifetime)
@st.cache_resource
def get_analyzer():
    return JeopardyCategoryAnalyzer()

@st.cache_data
def get_all_categories(_df_id: int):
    return df["category"].unique()

@st.cache_data
def get_theme_groups(_df_id: int):
    return get_analyzer().analyze_categories(get_all_categories(_df_id))

analyzer = get_analyzer()
_df_signature = len(df)
all_categories = get_all_categories(_df_signature)
theme_groups = get_theme_groups(_df_signature)

@st.cache_data
def get_era_metadata(_df_sig: int):
    """Detect an air-date or season column and summarize the eras available.

    Returns None when the dataset has neither, so the era filter can be
    hidden gracefully. Mirrors the column-detection pattern used by
    compute_catalogue_stats.
    """
    date_col = next((c for c in ("air_date", "airdate", "date") if c in df.columns), None)
    if date_col is not None:
        years = pd.to_datetime(df[date_col], errors="coerce").dt.year.dropna()
        if not years.empty:
            decades = sorted((years.astype(int) // 10 * 10).unique().tolist())
            return {"kind": "year", "col": date_col, "decades": decades}
    season_col = next((c for c in ("season", "season_number") if c in df.columns), None)
    if season_col is not None:
        seasons = pd.to_numeric(df[season_col], errors="coerce").dropna()
        if not seasons.empty:
            svals = sorted(seasons.astype(int).unique().tolist())
            return {"kind": "season", "col": season_col, "seasons": svals}
    return None

era_metadata = get_era_metadata(_df_signature)

# SIDEBAR FOR SETTINGS
with st.sidebar:
    st.markdown("## Jayopardy")
    # Derive username from AuthManager
    current_username = st.session_state.get("user_name") or st.session_state.get("username") or "Player"
    st.session_state.username = current_username
    st.markdown(f"👤 **Player:** {current_username}")

    check_signed_in_status()
    restore_bookmarks_from_db()

    if st.session_state.is_signed_in:
        st.markdown('<span class="signed-in-badge">Signed in</span>', unsafe_allow_html=True)

    st.markdown("---")
    
    # Score display in sidebar
    st.markdown(f"""
    <div class="score-container">
        <div class="score-label">Score</div>
        <div class="score-value">{st.session_state.score} / {st.session_state.total}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Progress bar
    if st.session_state.total > 0:
        accuracy = (st.session_state.score / st.session_state.total) * 100
        st.markdown(f"""
        <div class="progress-bar">
            <div class="progress-fill" style="width: {accuracy}%">
                {accuracy:.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Streak display
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{st.session_state.streak}</div>
            <div class="stat-label">Streak</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{st.session_state.best_streak}</div>
            <div class="stat-label">Best</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Theme selection
    st.markdown("### 📚 Theme Selection")
    
    # Quick picks - default to All (all themes)
    quick_pick = st.selectbox(
        "Quick Pick:",
        ["📚 All", "Custom Selection", "🎓 Academic", "🎬 Entertainment", "🌍 World"],
        key="quick_pick",
        index=0  # Default to All
    )
    
    if quick_pick == "📚 All":
        selected_categories = list(all_categories)
    elif quick_pick == "Custom Selection":
        # Theme selector - show ALL themes
        theme_options = []
        theme_mapping = {}
        
        # Sort themes by number of categories (most first)
        sorted_themes = sorted(theme_groups.items(), key=lambda x: len(x[1]), reverse=True)
        
        for theme, cats in sorted_themes:
            # Show all themes, even with 1 category
            display_name = f"{theme} ({len(cats)} categories)"
            theme_options.append(display_name)
            theme_mapping[display_name] = theme
        
        # Show total available
        st.caption(f"📊 {len(theme_groups)} themes available from {len(all_categories)} total categories")
        
        selected_theme_displays = st.multiselect(
            "Select themes:",
            theme_options,
            default=theme_options[:5] if len(theme_options) >= 5 else theme_options,  # Default to top 5
            help="Select multiple themes to include their categories"
        )
        
        selected_categories = []
        for display in selected_theme_displays:
            theme_name = theme_mapping.get(display)
            if theme_name and theme_name in theme_groups:
                selected_categories.extend(theme_groups[theme_name])
        
        # Remove duplicates (some categories might be in multiple themes)
        selected_categories = list(set(selected_categories))
    elif quick_pick == "🎓 Academic":
        selected_categories = []
        for theme in ["HISTORY", "SCIENCE", "LITERATURE", "GEOGRAPHY"]:
            if theme in theme_groups:
                selected_categories.extend(theme_groups[theme])
    elif quick_pick == "🎬 Entertainment":
        selected_categories = []
        for theme in ["ENTERTAINMENT", "POP CULTURE", "SPORTS"]:
            if theme in theme_groups:
                selected_categories.extend(theme_groups[theme])
    elif quick_pick == "🌍 World":
        selected_categories = []
        for theme in ["GEOGRAPHY", "HISTORY", "RELIGION & MYTHOLOGY"]:
            if theme in theme_groups:
                selected_categories.extend(theme_groups[theme])
    
    if selected_categories:
        st.session_state.selected_categories = selected_categories
        st.success(f"✅ {len(selected_categories)} categories selected")
        
        # Show sample categories in an expander
        with st.expander("View selected categories", expanded=False):
            # Show a random, representative sample — sorted alphabetically the
            # list leads with punctuation-only categories ("!", "&", etc.) which
            # looks like noise. A random sample better reflects the selection.
            import random
            sample_size = min(20, len(selected_categories))
            sample_cats = sorted(
                random.sample(selected_categories, sample_size),
                key=lambda c: c.lower()
            )

            for i in range(0, sample_size, 2):
                col1, col2 = st.columns(2)
                with col1:
                    if i < len(sample_cats):
                        st.caption(f"• {sample_cats[i]}")
                with col2:
                    if i+1 < len(sample_cats):
                        st.caption(f"• {sample_cats[i+1]}")

            if len(selected_categories) > sample_size:
                st.caption(f"... and {len(selected_categories) - sample_size:,} more categories")
    
    st.markdown("---")
    
    # AI Opponent Settings
    st.markdown("### 🤖 AI Opponent")
    st.session_state.ai_mode = st.checkbox(
        "Play against AI",
        value=st.session_state.ai_mode,
        help="Enable AI opponent for competitive play"
    )
    
    if st.session_state.ai_mode:
        # AI Personality selector
        st.session_state.ai_personality = st.selectbox(
            "Choose Opponent:",
            list(AI_PERSONALITIES.keys()),
            index=list(AI_PERSONALITIES.keys()).index(st.session_state.ai_personality)
        )
        
        personality = AI_PERSONALITIES[st.session_state.ai_personality]
        st.caption(f"*{personality['description']}*")
        
        # Difficulty selector
        difficulties = ["Easy", "Medium", "Hard"]
        # Handle if user had Impossible selected before
        if st.session_state.ai_difficulty not in difficulties:
            st.session_state.ai_difficulty = "Medium"
        
        st.session_state.ai_difficulty = st.selectbox(
            "Difficulty:",
            difficulties,
            index=difficulties.index(st.session_state.ai_difficulty)
        )
        
        # Show AI stats
        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            st.metric("AI Score", st.session_state.ai_score)
        with col_ai2:
            st.metric("AI Streak", st.session_state.ai_streak)
    
    st.markdown("---")
    
    # Game settings
    st.markdown("### ⚙️ Settings")
    
    # Timer toggle - default to on (state initialized via key="use_timer")
    use_timer = st.checkbox(
        "⏱️ Use Timer",
        help="Enable/disable time limit for answers",
        key="use_timer"
    )
    
    # Time limit (only show if timer is enabled)
    if use_timer:
        chosen_time = st.slider(
            "Time (seconds):",
            10, 60,
            key="time_limit_slider"
        )
        speed_round = st.checkbox(
            "⚡ Speed Round",
            help="5-second timer, 2x points",
            key="speed_round"
        )
        st.session_state.time_limit = 5 if speed_round else chosen_time
    else:
        st.session_state.speed_round = False
        st.session_state.time_limit = 999999  # Very large number instead of infinity
    
    # Study Mode
    st.session_state.study_mode = st.checkbox(
        "📚 Study Mode",
        value=st.session_state.study_mode,
        help="No timer, see answers immediately"
    )
    
    # Round selector (difficulty)
    if 'round' in df.columns:
        rounds = df['round'].dropna().unique().tolist()
        round_options = ['All Rounds'] + sorted(rounds)
        selected_round = st.selectbox(
            "📈 Difficulty (Round):",
            round_options,
            help="Filter by Jeopardy round"
        )
        st.session_state.selected_round = selected_round

    # Era / season filter (hidden gracefully when the dataset has no
    # air-date or season data).
    if era_metadata is not None:
        prev_era = st.session_state.get("era_filter")
        if era_metadata["kind"] == "year":
            era_options = ["All Eras"] + [f"{d}s" for d in era_metadata["decades"]]
            selected_era_label = st.selectbox(
                "🕰️ Era:",
                era_options,
                help="Practice clues only from episodes that aired in this decade"
            )
            if selected_era_label == "All Eras":
                st.session_state.era_filter = None
            else:
                st.session_state.era_filter = ("year", int(selected_era_label[:-1]))
        else:
            seasons = era_metadata["seasons"]
            if len(seasons) > 1:
                season_lo, season_hi = st.select_slider(
                    "🕰️ Seasons:",
                    options=seasons,
                    value=(seasons[0], seasons[-1]),
                    help="Practice clues only from this range of seasons"
                )
                if (season_lo, season_hi) == (seasons[0], seasons[-1]):
                    st.session_state.era_filter = None
                else:
                    st.session_state.era_filter = ("season", int(season_lo), int(season_hi))
            else:
                st.session_state.era_filter = None
        # Discard the current clue when the era selection changes so the
        # next question comes from the newly filtered pool.
        if st.session_state.get("era_filter") != prev_era:
            st.session_state.current_clue = None
            st.session_state.challenge_current_clue = None
    else:
        st.session_state.era_filter = None

    st.markdown("---")
    
    # Quick actions
    if st.button("🎯 New Question", use_container_width=True):
        st.session_state.current_clue = None
        st.rerun()

    if st.button("📊 Dataset Stats", use_container_width=True, help="Explore the full clue catalogue"):
        st.session_state.show_dataset_stats = True
        st.rerun()
    
    if st.session_state.is_signed_in:
        if st.button("🔁 Adaptive Mode", use_container_width=True, help="Focus on weak themes & missed questions"):
            if st.session_state.history:
                history_df = pd.DataFrame(st.session_state.history)
                category_stats = history_df.groupby("category").agg({
                    "was_correct": ["sum", "count"]
                })
                category_stats.columns = ["correct", "total"]
                category_stats["accuracy"] = category_stats["correct"] / category_stats["total"]
                weak_categories = category_stats[category_stats["accuracy"] < 0.5].index.tolist()
                missed = [h for h in st.session_state.history if not h["was_correct"]]
                weak_missed = [h for h in missed if h["category"] in weak_categories]
                retry_pool = weak_missed if weak_missed else missed
                if retry_pool:
                    weights = [0.5 + 0.5 * (i / len(retry_pool)) for i in range(len(retry_pool))]
                    retry = random.choices(retry_pool, weights=weights, k=1)[0]
                    st.session_state.current_clue = {
                        "category": retry["category"],
                        "clue": retry["clue"],
                        "correct_response": retry["correct_response"]
                    }
                    st.info(f"📚 Focusing on weak theme: {retry['category']}")
                    st.rerun()
                else:
                    st.success("🎉 Great job! No missed questions to retry!")
            else:
                st.info("Play some questions first to enable adaptive mode!")
    else:
        st.button("🔁 Adaptive Mode", use_container_width=True, disabled=True, help="Sign in to use adaptive mode")
        st.caption("🔒 Sign in to unlock")
        guest_sign_in_button("signin_adaptive")
    
    if st.button("🔄 Reset Game", use_container_width=True):
        for key in ["score", "total", "streak", "history", "daily_double_used"]:
            if key in st.session_state:
                if key in ["score", "total", "streak"]:
                    st.session_state[key] = 0
                elif key == "history":
                    st.session_state[key] = []
                else:
                    st.session_state[key] = False
        st.rerun()
    
    st.markdown("---")

    # Challenge Mode Section
    st.markdown("### 🏆 Challenge Mode")
    _db_ok = is_database_available()
    if not st.session_state.is_signed_in:
        st.caption("Sign in with an account to challenge friends.")
        guest_sign_in_button("signin_challenge")
    elif not _db_ok:
        st.info("⏳ Challenges are temporarily unavailable — the database can't be reached right now. Please try again shortly.")
    else:
        st.caption("Challenge friends and track your wins.")
    
    if "challenge_manager" not in st.session_state:
        st.session_state.challenge_manager = ChallengeManager()
    challenge_manager = st.session_state.challenge_manager

    if st.session_state.is_signed_in and _db_ok:
      try:
        with st.expander("➕ Create Challenge", expanded=False):
          opponent_name = st.text_input("Opponent username or email", key="challenge_opponent")
          num_q = st.number_input("Number of questions", min_value=5, max_value=20, value=10, step=1)
          if st.button("Send Challenge", use_container_width=True):
              if opponent_name and st.session_state.get("selected_categories"):
                  cid = challenge_manager.create_challenge(
                      st.session_state.username,
                      opponent_name.strip(),
                      st.session_state.selected_categories[:10],
                      int(num_q)
                  )
                  st.success(f"Challenge created (ID {cid}) for {opponent_name}")
              else:
                  st.warning("Please provide an opponent and select themes first.")

          # Show active challenges
          active_challenges = challenge_manager.get_active_challenges(st.session_state.username)
          if active_challenges:
              with st.expander(f"⚔️ Active Challenges ({len(active_challenges)})", expanded=False):
                  for challenge in active_challenges:
                      opponent = challenge["opponent"] if challenge["challenger"] == st.session_state.username else challenge["challenger"]
                      st.write(f"🎮 vs **{opponent}**")

                      # Show scores
                      your_score = challenge["challenger_score"] if challenge["challenger"] == st.session_state.username else challenge["opponent_score"]
                      their_score = challenge["opponent_score"] if challenge["challenger"] == st.session_state.username else challenge["challenger_score"]
                      your_done = challenge["challenger_completed"] if challenge["challenger"] == st.session_state.username else challenge["opponent_completed"]
                      their_done = challenge["opponent_completed"] if challenge["challenger"] == st.session_state.username else challenge["challenger_completed"]

                      st.write(f"You: {your_score} {'✅' if your_done else '⏳'}")
                      st.write(f"{opponent}: {their_score if their_done else '---'} {'✅' if their_done else '⏳'}")

                      if not your_done:
                          if st.button("🎮 Play", key=f"play_{challenge['id']}"):
                              # Ensure categories are parsed
                              ch_copy = dict(challenge)
                              if isinstance(ch_copy.get("categories"), str):
                                  try:
                                      ch_copy["categories"] = json.loads(ch_copy["categories"])
                                  except Exception:
                                      ch_copy["categories"] = []
                              st.session_state.current_challenge = ch_copy
                              st.session_state.challenge_mode = True
                              st.session_state.challenge_question_num = 0
                              st.session_state.challenge_score = 0
                              st.rerun()
                      st.markdown("---")

          # Show pending challenges
          pending_challenges = challenge_manager.get_pending_challenges(st.session_state.username)
          if pending_challenges:
              with st.expander(f"⏳ Pending Challenges ({len(pending_challenges)})", expanded=False):
                  for challenge in pending_challenges:
                      if challenge['opponent'] == st.session_state.username:
                          challenger = challenge['challenger']
                          st.write(f"⚔️ From **{challenger}**")
                          if st.button("✅ Accept", key=f"accept_{challenge['id']}"):
                              challenge_manager.accept_challenge(challenge["id"], st.session_state.username)
                              st.success("Challenge accepted!")
                              st.rerun()
                      else:
                          opponent = challenge['opponent']
                          st.write(f"⏳ Waiting for **{opponent}**")
                      st.markdown("---")

          # Show completed challenges
          completed_challenges = challenge_manager.get_completed_challenges(st.session_state.username)
          if completed_challenges:
              with st.expander(f"🏅 Results ({len(completed_challenges)})", expanded=False):
                  for challenge in completed_challenges[-5:]:  # Show last 5
                      opponent = challenge["opponent"] if challenge["challenger"] == st.session_state.username else challenge["challenger"]
                      # Determine user's score side
                      your_score = challenge["challenger_score"] if challenge["challenger"] == st.session_state.username else challenge["opponent_score"]
                      their_score = challenge["opponent_score"] if challenge["challenger"] == st.session_state.username else challenge["challenger_score"]
                      result_emoji = "🤝"
                      result_text = "Tied"
                      if challenge.get('winner_id'):
                          if (challenge['winner_id'] == challenge['challenger_id'] and challenge["challenger"] == st.session_state.username) or \
                             (challenge['winner_id'] == challenge['opponent_id'] and challenge["opponent"] == st.session_state.username):
                              result_emoji = "🏆"
                              result_text = "Won"
                          else:
                              result_emoji = "😔"
                              result_text = "Lost"
                      st.write(f"{result_emoji} **{result_text}** vs {opponent} ({your_score} - {their_score})")
                      st.markdown("---")
      except Exception:
          st.info("⏳ Challenges are temporarily unavailable — the database can't be reached right now. Please try again shortly.")

    st.markdown("---")

    if st.button("Sign out", use_container_width=True):
        auth.logout()

    st.markdown("---")
    _source_label = get_data_source()
    _db_label = "Connected" if _db_ok else "Unavailable"
    st.markdown(f"""
<div style="font-size:0.68rem;color:rgba(255,255,255,0.4);line-height:1.6;padding:.25rem 0;">
<strong style="color:rgba(255,255,255,0.55);letter-spacing:.05em;">Status</strong><br>
Clue data: {_source_label}<br>
Database: {_db_label}
</div>
""", unsafe_allow_html=True)
    st.markdown("""
<div style="font-size:0.68rem;color:rgba(255,255,255,0.4);line-height:1.6;padding:.25rem 0;">
<strong style="color:rgba(255,255,255,0.55);letter-spacing:.05em;">About</strong><br>
Jayopardy is an independent trivia training tool. It is not affiliated with, endorsed by, or connected to Jeopardy! Productions, Sony Pictures, or any official Jeopardy! entity.<br><br>
Built by <a href="https://julieyingst.com" target="_blank" style="color:rgba(201,150,74,0.8);text-decoration:none;">Julie Yingst</a>.
</div>
""", unsafe_allow_html=True)

# MAIN GAME AREA


# Dataset Stats view
@st.cache_data
def compute_catalogue_stats(_df_sig: int):
    """Derive catalogue metrics from the loaded dataset (cached per dataset signature)."""
    total_clues = len(df)
    total_games = df["game_id"].nunique() if "game_id" in df.columns else 0
    total_categories = df["category"].nunique() if "category" in df.columns else 0

    if "round" in df.columns:
        round_counts = df["round"].dropna().value_counts()
    else:
        round_counts = pd.Series(dtype=int)

    # Map each category to its theme (via the cached analyzer groups) and
    # count clues per theme.
    cat_to_theme = {}
    for theme, cats in theme_groups.items():
        for cat in cats:
            cat_to_theme.setdefault(cat, theme)
    theme_counts = (
        df["category"].map(cat_to_theme).dropna().value_counts()
        if "category" in df.columns else pd.Series(dtype=int)
    )

    top_categories = (
        df["category"].value_counts().head(15)
        if "category" in df.columns else pd.Series(dtype=int)
    )

    # Time coverage: clues per air-year (from a date column) or per season.
    # Gracefully empty when the dataset has neither.
    timeline_counts = pd.Series(dtype=int)
    timeline_label = None
    date_col = next((c for c in ("air_date", "airdate", "date") if c in df.columns), None)
    if date_col is not None:
        years = pd.to_datetime(df[date_col], errors="coerce").dt.year.dropna()
        if not years.empty:
            timeline_counts = years.astype(int).value_counts().sort_index()
            timeline_label = "Year"
    if timeline_counts.empty:
        season_col = next((c for c in ("season", "season_number") if c in df.columns), None)
        if season_col is not None:
            seasons = pd.to_numeric(df[season_col], errors="coerce").dropna()
            if not seasons.empty:
                timeline_counts = seasons.astype(int).value_counts().sort_index()
                timeline_label = "Season"

    return {
        "total_clues": total_clues,
        "total_games": total_games,
        "total_categories": total_categories,
        "round_counts": round_counts,
        "theme_counts": theme_counts,
        "top_categories": top_categories,
        "timeline_counts": timeline_counts,
        "timeline_label": timeline_label,
    }

if st.session_state.get("show_dataset_stats"):
    stats = compute_catalogue_stats(_df_signature)

    st.markdown("""
    <div class="main-header">
        <h1>📊 Dataset Stats</h1>
        <p>The full Jeopardy! clue catalogue powering your training</p>
    </div>
    """, unsafe_allow_html=True)

    # Headline metric cards
    c1, c2, c3, c4 = st.columns(4)
    headline = [
        (c1, f"{stats['total_clues']:,}", "Total Clues"),
        (c2, f"{stats['total_games']:,}", "Games"),
        (c3, f"{stats['total_categories']:,}", "Unique Categories"),
        (c4, f"{len(stats['theme_counts']):,}", "Themes"),
    ]
    for col, value, label in headline:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{value}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    col_round, col_theme = st.columns(2)
    with col_round:
        st.markdown("### 🎰 Clues by Round")
        if not stats["round_counts"].empty:
            round_df = stats["round_counts"].rename_axis("Round").reset_index(name="Clues")
            st.bar_chart(round_df.set_index("Round")["Clues"], color="#e5b94f")
            st.dataframe(
                round_df.assign(Clues=round_df["Clues"].map("{:,}".format)),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No round information available in this dataset.")

    with col_theme:
        st.markdown("### 🗂️ Clues by Theme")
        if not stats["theme_counts"].empty:
            theme_df = stats["theme_counts"].head(12).rename_axis("Theme").reset_index(name="Clues")
            st.bar_chart(theme_df.set_index("Theme")["Clues"], color="#e5b94f", horizontal=True)
            st.dataframe(
                theme_df.assign(Clues=theme_df["Clues"].map("{:,}".format)),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No theme information available.")

    if stats["timeline_label"] and not stats["timeline_counts"].empty:
        label = stats["timeline_label"]
        st.markdown(f"### 📅 Clues by {label}")
        tl = stats["timeline_counts"]
        st.caption(
            f"Catalogue spans {label.lower()}s {tl.index.min()}–{tl.index.max()} "
            f"({len(tl)} {label.lower()}s covered)"
        )
        timeline_df = tl.rename_axis(label).reset_index(name="Clues")
        st.bar_chart(timeline_df.set_index(label)["Clues"], color="#e5b94f")

    st.markdown("### 🏆 Most Frequent Categories")
    if not stats["top_categories"].empty:
        top_cat_df = stats["top_categories"].rename_axis("Category").reset_index(name="Clues")
        top_cat_df["Clues"] = top_cat_df["Clues"].map("{:,}".format)
        st.dataframe(top_cat_df, use_container_width=True, hide_index=True)

    if st.button("↩️ Back to Game", use_container_width=True):
        st.session_state.show_dataset_stats = False
        st.rerun()

    st.stop()  # Don't show the regular game while viewing stats

# Check if viewing a bookmark
if st.session_state.viewing_bookmark:
    st.info("📖 Viewing Bookmarked Question")
    bookmark = st.session_state.viewing_bookmark
    
    st.markdown(f"""
    <div class="theme-card">
        BOOKMARKED: {bookmark['category']}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="clue-card">
        <div class="clue-text">{bookmark['clue']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📖 View Answer", expanded=True):
        st.success(f"**Answer:** {bookmark['correct_response']}")
        
        # Note section for bookmark
        note_key = f"{bookmark['category']}_{bookmark['clue'][:50]}"
        existing_note = st.session_state.notes.get(note_key, "")
        new_note = st.text_area(
            "📝 Edit note for this bookmark:",
            value=existing_note,
            placeholder="Add memory tricks, related facts, etc."
        )
        if new_note != existing_note:
            st.session_state.notes[note_key] = new_note
    
    if st.button("↩️ Back to Game", use_container_width=True):
        st.session_state.viewing_bookmark = None
        st.rerun()
    
    st.stop()  # Don't show the regular game when viewing bookmark

# Show different header for AI mode vs regular mode
if st.session_state.ai_mode:
    # AI Mode - Show both player and AI scores
    st.markdown("""<div class="main-header"><h1>Jayopardy</h1></div>""", unsafe_allow_html=True)
    
    col_player, col_vs, col_ai = st.columns([2, 1, 2])
    _lead_color = "#1e1b4b"
    _trail_color = "#7c7492"
    with col_player:
        player_color = _lead_color if st.session_state.score >= st.session_state.ai_score else _trail_color
        st.markdown(f"""
        <div style="text-align:center;padding:1rem;background:#ffffff;border:1px solid #e8e3dc;
                    border-top:3px solid {player_color};border-radius:8px;color:#1a1625;">
            <div style="font-size:0.7rem;color:#7c7492;text-transform:uppercase;letter-spacing:0.16em;font-weight:600;margin-bottom:.4rem;">{st.session_state.username}</div>
            <div style="font-family:'Fraunces',Georgia,serif;font-size:2.2rem;font-weight:400;color:#1e1b4b;">{st.session_state.score}</div>
            <div style="font-size:0.78rem;color:#7c7492;margin-top:.25rem;">Streak: {st.session_state.streak}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_vs:
        st.markdown("""
        <div style="text-align:center;padding:2rem 0;">
            <div style="font-size:0.75rem;font-weight:700;color:#7c7492;letter-spacing:.2em;">VS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_ai:
        ai_color = "#9b1c1c" if st.session_state.ai_score > st.session_state.score else _trail_color
        st.markdown(f"""
        <div style="text-align:center;padding:1rem;background:#ffffff;border:1px solid #e8e3dc;
                    border-top:3px solid {ai_color};border-radius:8px;color:#1a1625;">
            <div style="font-size:0.7rem;color:#7c7492;text-transform:uppercase;letter-spacing:0.16em;font-weight:600;margin-bottom:.4rem;">{st.session_state.ai_personality}</div>
            <div style="font-family:'Fraunces',Georgia,serif;font-size:2.2rem;font-weight:400;color:#1e1b4b;">{st.session_state.ai_score}</div>
            <div style="font-size:0.78rem;color:#7c7492;margin-top:.25rem;">Streak: {st.session_state.ai_streak}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Show who's winning
    if st.session_state.buzzer_winner:
        if st.session_state.buzzer_winner == "player":
            st.success("You buzzed in first — your turn to answer.")
        else:
            st.info(f"{st.session_state.ai_personality} buzzed in first.")
else:
    # Regular mode header
    st.markdown(f"""
    <div class="main-header">
        <h1>Jayopardy</h1>
        <div class="header-stats">
            <div class="header-stat">
                <div class="header-stat-value">{st.session_state.score}</div>
                <div class="header-stat-label">Score</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value">{st.session_state.total}</div>
                <div class="header-stat-label">Questions</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value">{st.session_state.streak}</div>
                <div class="header-stat-label">Streak</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value">{f"{(st.session_state.score/st.session_state.total*100):.0f}%" if st.session_state.total > 0 else "-"}</div>
                <div class="header-stat-label">Accuracy</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Whether an active challenge is driving question selection (challenges use
# their own category pool, so normal theme/pool checks must not block them).
_in_challenge_mode = bool(st.session_state.get("challenge_mode"))

# Check if categories are selected (normal gameplay only)
if not st.session_state.selected_categories and not _in_challenge_mode:
    st.warning("⚠️ Please select themes from the sidebar to start playing!")
    st.stop()

@st.cache_data
def get_filtered_df(selected_cats_tuple: tuple, selected_round: str, era_filter, _df_sig: int):
    fdf = df[df["category"].isin(selected_cats_tuple)]
    if selected_round and selected_round != 'All Rounds':
        fdf = fdf[fdf['round'] == selected_round]
    fdf = apply_era_filter(fdf, era_filter, era_metadata)
    return fdf

filtered_df = get_filtered_df(
    tuple(st.session_state.selected_categories),
    st.session_state.get('selected_round', 'All Rounds'),
    st.session_state.get('era_filter'),
    _df_signature,
)

if filtered_df.empty and not _in_challenge_mode:
    st.warning("No clues found for selected themes/round/era. Please adjust your selection.")
    st.stop()

# Challenge Mode Game Logic
if "challenge_mode" in st.session_state and st.session_state.challenge_mode:
    challenge = st.session_state.current_challenge
    opponent = challenge["opponent"]
    
    # Display challenge header
    st.markdown(f"""
    <div style="background:#1e1b4b;color:#ffffff;padding:1.25rem 1.5rem;border-radius:6px;
                border-left:3px solid #c9964a;text-align:center;margin-bottom:1rem;">
        <div style="font:600 0.65rem 'Inter',sans-serif;color:#c9964a;letter-spacing:.22em;text-transform:uppercase;margin-bottom:.5rem;">Challenge Mode</div>
        <div style="font-family:'Fraunces',Georgia,serif;font-size:1.15rem;font-weight:400;color:#fff;">You vs {opponent}</div>
        <div style="font-size:0.85rem;color:rgba(255,255,255,0.65);margin-top:.35rem;">Question {st.session_state.challenge_question_num + 1} of {challenge['num_questions']} &nbsp;·&nbsp; Score: {st.session_state.challenge_score}</div>
    </div>
    """, unsafe_allow_html=True)

    # Check if challenge is complete
    if st.session_state.challenge_question_num >= challenge["num_questions"]:
        # Complete the challenge
        st.session_state.challenge_manager.complete_challenge(
            challenge["id"],
            st.session_state.username,
            st.session_state.challenge_score
        )

        st.success(f"Challenge complete! Your score: {st.session_state.challenge_score}/{challenge['num_questions']}")

        # Reset challenge mode
        st.session_state.challenge_mode = False
        st.session_state.current_challenge = None
        st.session_state.challenge_question_num = 0
        st.session_state.challenge_score = 0
        
        if st.button("Back to Normal Mode", type="primary"):
            st.rerun()
        st.stop()
    
    # Use challenge categories
    ch_categories = challenge.get("categories", [])
    if isinstance(ch_categories, str):
        try:
            ch_categories = json.loads(ch_categories)
        except Exception:
            ch_categories = []
    challenge_df = df[df["category"].isin(ch_categories)]
    if challenge_df.empty:
        # Challenge categories missing from dataset: fall back to the regular
        # filtered pool (which already respects the era/season filter).
        challenge_df = filtered_df
    else:
        # Respect the era/season filter in challenges too (round filter is
        # intentionally not applied: challenges are defined by their categories).
        challenge_df = apply_era_filter(
            challenge_df, st.session_state.get("era_filter"), era_metadata
        )
    if challenge_df.empty:
        st.warning(
            "⏳ This challenge has no clues from the selected era/season. "
            "Set the era filter back to All in the sidebar to continue the challenge."
        )
        st.stop()
    
    # Get challenge question
    if "challenge_current_clue" not in st.session_state or st.session_state.challenge_current_clue is None:
        st.session_state.challenge_current_clue = random.choice(challenge_df.to_dict(orient="records"))
        st.session_state.start_time = datetime.datetime.now()
    
    clue = st.session_state.challenge_current_clue
    
# Regular game mode
else:
    # Get current clue
    if st.session_state.current_clue is None:
        st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
        st.session_state.start_time = datetime.datetime.now()
    
    clue = st.session_state.current_clue

# Check for Daily Double
is_daily_double = False
if not st.session_state.daily_double_used and random.random() < 0.05:
    is_daily_double = True
    st.session_state.daily_double_used = True

# Display Daily Double if applicable
if is_daily_double:
    st.markdown("""
    <div style="background:#fdf8ef;border:1px solid #e8d5a8;border-left:3px solid #92681d;
                padding:1rem 1.25rem;border-radius:6px;text-align:center;margin-bottom:1rem;">
        <div style="font:700 0.62rem 'Inter',sans-serif;color:#92681d;letter-spacing:.22em;text-transform:uppercase;margin-bottom:.4rem;">Daily Double</div>
        <div style="font-family:'Fraunces',Georgia,serif;font-size:1.3rem;font-weight:500;color:#1a1625;letter-spacing:-.01em;">Double points on this question</div>
    </div>
    """, unsafe_allow_html=True)

# Display category
st.markdown(f"""
<div class="theme-card">
    {clue['category']}
</div>
""", unsafe_allow_html=True)

# Display clue
st.markdown(f"""
<div class="clue-card">
    <div class="clue-text">{clue['clue']}</div>
</div>
""", unsafe_allow_html=True)

# Study Mode - show answer immediately
if st.session_state.study_mode:
    with st.expander("📖 View Answer", expanded=False):
        st.success(f"**Answer:** {clue['correct_response']}")
        
        # Note-taking for study mode
        note_key = f"{clue['category']}_{clue['clue'][:50]}"
        existing_note = st.session_state.notes.get(note_key, "")
        new_note = st.text_area(
            "📝 Add a note:",
            value=existing_note,
            placeholder="Add memory tricks, related facts, etc.",
            key=f"note_{note_key}"
        )
        if new_note != existing_note:
            st.session_state.notes[note_key] = new_note

# AI Mode - Handle buzzer and AI responses
if st.session_state.ai_mode and not st.session_state.buzzer_winner and not st.session_state.study_mode:
    # Buzzer phase - AI might buzz automatically
    st.markdown("""
    <div class="buzzer-panel">
        <div class="bp-title">Buzzer Open</div>
        <div class="bp-text">Buzz in before your opponent to answer</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Give the player a guaranteed reading window before the AI can buzz.
    # On the first render of a new clue we roll ONCE whether the AI will buzz
    # and, if so, schedule when — always after a difficulty-scaled delay.
    import time

    _clue_key = f"{clue.get('category','')}|{clue.get('clue','')}"
    if st.session_state.get("buzz_phase_clue") != _clue_key:
        st.session_state.buzz_phase_clue = _clue_key
        st.session_state.buzz_phase_start = time.time()
        # Easy: 30% chance, Medium: 50% chance, Hard: 70% chance
        buzz_chances = {"Easy": 0.3, "Medium": 0.5, "Hard": 0.7}
        st.session_state.ai_will_buzz = (
            random.random() < buzz_chances[st.session_state.ai_difficulty]
        )
        # AI buzz delay (seconds after clue render), scaled by difficulty.
        # Even on Hard the player gets a few seconds to read and buzz.
        ai_delay_windows = {
            "Easy": (8.0, 12.0),
            "Medium": (5.0, 8.0),
            "Hard": (3.0, 5.0),
        }
        lo, hi = ai_delay_windows[st.session_state.ai_difficulty]
        st.session_state.ai_buzz_at = random.uniform(lo, hi)

    elapsed = time.time() - st.session_state.buzz_phase_start

    # Create a container for dynamic updates
    buzz_container = st.container()

    with buzz_container:
        col_buzz1, col_buzz2 = st.columns(2)

        with col_buzz1:
            if st.button("Buzz In", use_container_width=True, key="buzzer", type="primary"):
                # Player buzzed. If the AI had already buzzed (its scheduled
                # time passed), the AI wins; otherwise the player claims it.
                if st.session_state.get("ai_will_buzz") and elapsed >= st.session_state.get("ai_buzz_at", 0):
                    winner = "ai"
                else:
                    winner = "player"
                st.session_state.buzzer_winner = winner
                st.session_state.current_turn = winner

                if winner == "player":
                    st.success("You buzzed in first — your turn to answer.")
                else:
                    st.warning(f"{st.session_state.ai_personality} was faster to the buzzer.")
                st.rerun()

        with col_buzz2:
            if st.session_state.get("ai_will_buzz") and elapsed >= st.session_state.get("ai_buzz_at", 0):
                # AI's scheduled buzz time has arrived and the player hasn't buzzed
                st.session_state.buzzer_winner = "ai"
                st.session_state.current_turn = "ai"
                st.rerun()
            else:
                st.info(f"{st.session_state.ai_personality} is weighing the clue — buzz while you can.")

    # If the AI is going to buzz later, keep polling so its buzz fires after
    # the visible delay. Short sleeps keep the Buzz In button responsive —
    # a player click is processed on the next rerun.
    if st.session_state.get("ai_will_buzz"):
        remaining = st.session_state.ai_buzz_at - elapsed
        if remaining > 0:
            time.sleep(min(0.5, remaining))
            st.rerun()

    # Don't show answer form during buzzer phase
    st.stop()

elif st.session_state.ai_mode and st.session_state.buzzer_winner == "ai" and not st.session_state.study_mode:
    # AI is answering
    st.info(f"{st.session_state.ai_personality} buzzed in first.")
    
    # Simulate AI response
    with st.spinner(f"{st.session_state.ai_personality} is thinking..."):
        is_correct, thinking_time = simulate_ai_response(
            clue["clue"],
            clue["category"],
            st.session_state.ai_difficulty,
            st.session_state.ai_personality
        )
    
    if is_correct:
        st.error(f"{st.session_state.ai_personality} answered correctly. The response was: **{clue['correct_response']}**")
        
        # Award points to AI using clue value (daily double applies)
        base_value = parse_clue_value(clue.get("value"))
        ai_points = base_value * (2 if is_daily_double else 1)
        st.session_state.ai_score += int(ai_points)
        st.session_state.ai_streak += 1
        
        # Reset for next question
        if st.button("Next Question ➡️", use_container_width=True, type="primary"):
            st.session_state.current_clue = None
            st.session_state.buzzer_winner = None
            st.session_state.current_turn = None
            st.rerun()
        st.stop()  # Don't show answer form
    else:
        st.success(f"{st.session_state.ai_personality} missed it — the board is yours.")
        st.info("Answer below to steal the points.")
        # Let player try to steal - continue to answer form

# Show answer form if:
# 1. Not in AI mode, OR
# 2. Player buzzed in, OR  
# 3. AI got it wrong and player can steal, OR
# 4. In study mode
show_answer_form = (
    not st.session_state.ai_mode or
    st.session_state.buzzer_winner == "player" or
    st.session_state.study_mode or
    (st.session_state.buzzer_winner == "ai" and st.session_state.ai_mode)  # AI wrong, player can steal
)

if show_answer_form:
    # Reserve a slot for the live countdown timer above the answer form.
    # We fill it AFTER the form so we can suppress it when the player has
    # just submitted (which stops the countdown immediately on submit).
    _timer_slot = st.container()

    with st.form(key="clue_form", clear_on_submit=True):
        col_input, col_submit, col_bookmark = st.columns([3, 1, 1])
        with col_input:
            user_input = st.text_input(
                "Your response:",
                placeholder="Type your answer here...",
                label_visibility="collapsed",
                disabled=st.session_state.study_mode
            )
        with col_submit:
            submit_text = "🎯 Submit"
            if st.session_state.study_mode:
                submit_text = "⏭️ Next"
            elif st.session_state.ai_mode and st.session_state.buzzer_winner == "player":
                submit_text = "🎯 Answer!"
            submitted = st.form_submit_button(
                submit_text, 
                use_container_width=True
            )
        with col_bookmark:
            bookmark_btn = st.form_submit_button("🔖", use_container_width=True, help="Bookmark")

    # Render the live countdown into the reserved slot ABOVE the form, but
    # only if the player hasn't just submitted/bookmarked this render — that
    # way submitting an answer stops the countdown instantly.
    if (
        not submitted
        and not bookmark_btn
        and st.session_state.use_timer
        and not st.session_state.study_mode
        and st.session_state.time_limit != 999999
    ):
        _start_ms = int(st.session_state.start_time.timestamp() * 1000)
        _limit_s = int(st.session_state.time_limit)
        import streamlit.components.v1 as _components
        with _timer_slot:
            _components.html(
                f"""
                 <div style="font-family:'Inter',sans-serif;color:#1a1625;
                             background:#ffffff;border:1px solid #e8e3dc;border-radius:6px;
                             padding:0.6rem 1rem;box-shadow:0 1px 4px rgba(26,22,37,0.06);">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                     <span style="font:600 0.63rem 'Inter',sans-serif;color:#7c7492;text-transform:uppercase;letter-spacing:.18em;">Time remaining</span>
                     <span id="jpy-timer-value" style="font:600 1rem 'Inter',sans-serif;color:#1e1b4b;font-variant-numeric:tabular-nums;">{_limit_s}.0s</span>
                  </div>
                   <div style="margin-top:0.45rem;height:4px;background:#f0ece6;border-radius:99px;overflow:hidden;">
                    <div id="jpy-timer-bar" style="height:100%;width:100%;
                                                     background:#4338ca;border-radius:99px;
                                                    transition:width 0.12s linear,background-color 0.3s ease;">
                    </div>
                  </div>
                </div>
                <script>
                (function() {{
                    const startMs = {_start_ms};
                    const limit = {_limit_s};
                    const valueEl = document.getElementById('jpy-timer-value');
                    const barEl = document.getElementById('jpy-timer-bar');
                    if (!valueEl || !barEl) return;
                    function tick() {{
                        const elapsed = (Date.now() - startMs) / 1000;
                        const remaining = Math.max(0, limit - elapsed);
                        valueEl.textContent = remaining.toFixed(1) + 's';
                        const pct = Math.max(0, Math.min(100, (remaining / limit) * 100));
                        barEl.style.width = pct + '%';
                        if (pct <= 25) {{
                             barEl.style.background = '#dc2626';
                        }} else if (pct <= 50) {{
                             barEl.style.background = '#d97706';
                        }} else {{
                             barEl.style.background = '#4338ca';
                        }}
                        if (remaining > 0) {{
                            requestAnimationFrame(tick);
                        }} else {{
                            valueEl.textContent = "Time's up!";
                            autoSubmit();
                        }}
                    }}
                    let didSubmit = false;
                    function autoSubmit() {{
                        if (didSubmit) return;
                        didSubmit = true;
                        try {{
                            const parentDoc = window.parent.document;
                            // Scope strictly to the clue answer form so we don't
                            // accidentally hit sidebar buttons like "🎯 New Question".
                            // Streamlit renders st.form as <form data-testid="stForm">.
                            // Only one such form is mounted on the play screen at a time.
                            const forms = parentDoc.querySelectorAll('form[data-testid="stForm"]');
                            let answerForm = null;
                            for (const f of forms) {{
                                if (f.querySelector('input[type="text"]')) {{
                                    answerForm = f;
                                    break;
                                }}
                            }}
                            if (!answerForm) {{
                                // Couldn't find the form — fall back to a reload so
                                // the server-side time-limit check still fires.
                                try {{ window.parent.location.reload(); }} catch (e2) {{}}
                                return;
                            }}
                            // Stamp the answer input with a sentinel value BEFORE
                            // clicking submit. This is the explicit "auto-submit"
                            // signal the Python grader uses to distinguish a
                            // timer auto-submit from a user-initiated submit.
                            // We must use the native React value setter +
                            // 'input' event so React/Streamlit registers the
                            // change before the form submission.
                            try {{
                                const inputs = answerForm.querySelectorAll('input[type="text"]');
                                const proto = window.parent.HTMLInputElement
                                              && window.parent.HTMLInputElement.prototype;
                                const desc = proto && Object.getOwnPropertyDescriptor(proto, 'value');
                                const nativeSetter = desc && desc.set;
                                inputs.forEach(function(i) {{
                                    if (nativeSetter) {{
                                        nativeSetter.call(i, '{AUTO_SUBMIT_TIMEOUT_SENTINEL}');
                                    }} else {{
                                        i.value = '{AUTO_SUBMIT_TIMEOUT_SENTINEL}';
                                    }}
                                    i.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                }});
                            }} catch (e) {{}}
                            // Disable the answer input so the player can't keep typing.
                            answerForm.querySelectorAll('input[type="text"]').forEach(function(i) {{
                                i.disabled = true;
                                i.blur();
                            }});
                            // Pick the form's Submit button — the one that does NOT
                            // contain the bookmark 🔖 emoji.
                            const formBtns = answerForm.querySelectorAll(
                                'button[data-testid="stBaseButton-secondaryFormSubmit"], button[kind="secondaryFormSubmit"], [data-testid="stFormSubmitButton"] button, button'
                            );
                            const seen = new Set();
                            for (const btn of formBtns) {{
                                if (seen.has(btn)) continue;
                                seen.add(btn);
                                const txt = (btn.innerText || btn.textContent || '').trim();
                                if (txt.indexOf('🔖') !== -1) continue;
                                btn.click();
                                return;
                            }}
                        }} catch (e) {{
                            // Cross-origin or DOM access failed; fall back to a reload
                            // so the server-side time-limit check takes over.
                            try {{ window.parent.location.reload(); }} catch (e2) {{}}
                        }}
                    }}
                    tick();
                }})();
                </script>
                """,
                height=70,
            )

if bookmark_btn:
    if st.session_state.is_signed_in:
        bookmark_entry = {
            "category": clue["category"],
            "clue": clue["clue"],
            "correct_response": clue["correct_response"],
            "bookmarked_at": datetime.datetime.now().isoformat()
        }
        if _bookmark_key(bookmark_entry) not in {_bookmark_key(b) for b in st.session_state.bookmarks}:
            st.session_state.bookmarks.append(bookmark_entry)
            try:
                save_bookmark(
                    bookmark_identity(),
                    bookmark_entry["category"],
                    bookmark_entry["clue"],
                    bookmark_entry["correct_response"],
                )
            except Exception as e:
                import sys
                print(f"[bookmarks] save failed: {e}", file=sys.stderr)
            st.success("🔖 Bookmarked!")
    else:
        st.info("🔒 Sign in to save bookmarks — it's free.")
        guest_sign_in_button("signin_bookmark_save", use_container_width=False)

if submitted:
    if st.session_state.study_mode:
        # In study mode, just move to next question
        if "challenge_mode" in st.session_state and st.session_state.challenge_mode:
            st.session_state.challenge_current_clue = None
            st.session_state.challenge_question_num += 1
        else:
            st.session_state.current_clue = None
        st.rerun()
    else:
        elapsed_seconds = (datetime.datetime.now() - st.session_state.start_time).total_seconds()
        elapsed_time = int(elapsed_seconds)

        # Explicit signal from the JS countdown: when it auto-submits at
        # remaining == 0, it stamps this sentinel into the answer input
        # BEFORE clicking Submit. This is how we tell a timer auto-submit
        # apart from a user-initiated click.
        time_expired = (user_input == AUTO_SUBMIT_TIMEOUT_SENTINEL)
        if time_expired:
            # Clear the sentinel so it doesn't leak into grading, history,
            # or anything the player sees.
            user_input = ""

        # Server-side fallback: if the JS auto-submit didn't fire (browser
        # tab inactive, JS error, sentinel stripping by an extension, etc.)
        # and the player still managed to submit well past the deadline,
        # treat it as a timeout too. A generous 1.5s grace buffer avoids
        # punishing borderline legitimate manual submits caused by network
        # round-trip / Streamlit websocket latency.
        timer_on = (
            st.session_state.use_timer
            and not st.session_state.study_mode
            and st.session_state.time_limit != 999999
        )
        if not time_expired and timer_on and elapsed_seconds > st.session_state.time_limit + 1.5:
            time_expired = True

        user_clean = normalize(user_input)
        answer_clean = normalize(clue["correct_response"])

        # Calculate points
        points_multiplier = 1
        if st.session_state.speed_round and elapsed_time <= 5:
            points_multiplier = 2
        elif is_daily_double:
            points_multiplier = 2

        # Check correctness using fuzzy matching
        answer_matches = fuzzy_match(user_input, clue["correct_response"], threshold=65)

        # A timed-out submit is always incorrect, regardless of whatever
        # (typically empty) text was in the box. A manual submit within the
        # time limit is graded purely on the answer text.
        if time_expired:
            correct = False
        else:
            correct = answer_matches

        base_value = parse_clue_value(clue.get("value"))

        if time_expired:
            st.warning(
                "⏰ **Time expired!** The countdown ran out before you could submit your answer."
            )

        if correct:
            st.balloons()
            points_earned = base_value * points_multiplier
            st.success(f"**Correct** — well played. +${points_earned}")
            st.session_state.score += int(points_earned)
            st.session_state.streak += 1
            st.session_state.best_streak = max(st.session_state.streak, st.session_state.best_streak)
            
            # Check for achievements
            if st.session_state.streak == 5 and "5_streak" not in st.session_state.achievements:
                st.session_state.achievements.append("5_streak")
                st.success("🏆 Achievement: 5 Question Streak!")
            elif st.session_state.streak == 10 and "10_streak" not in st.session_state.achievements:
                st.session_state.achievements.append("10_streak")
                st.success("🏆 Achievement: 10 Question Streak!")
        else:
            if time_expired:
                st.error("**Incorrect** — no answer submitted in time.")
            else:
                st.error("**Incorrect**")
            st.info(f"The correct response was: **{clue['correct_response']}**")
            st.session_state.streak = 0
            points_earned = 0
            
            # Track weak themes
            themes = analyzer.categorize_single(clue["category"])
            theme = themes[0] if isinstance(themes, list) and themes else (themes if isinstance(themes, str) else "MISCELLANEOUS")
            if theme not in st.session_state.weak_themes:
                st.session_state.weak_themes[theme] = {"incorrect": 0, "total": 0}
            st.session_state.weak_themes[theme]["incorrect"] += 1

            # Suggest more clues from the same category to practice (fast keyword match)
            try:
                same_cat = filtered_df[
                    (filtered_df["category"] == clue["category"]) &
                    (filtered_df["clue"] != clue["clue"])
                ].head(3)
                if not same_cat.empty:
                    st.markdown("#### More from this category:")
                    for _, row in same_cat.iterrows():
                        st.markdown(f"- {row['clue']}  \n  Answer: *{row['correct_response']}*")
            except Exception:
                pass

        # Update weak theme totals regardless of correct/incorrect
        themes = analyzer.categorize_single(clue["category"])
        theme = themes[0] if isinstance(themes, list) and themes else (themes if isinstance(themes, str) else "MISCELLANEOUS")
        if theme not in st.session_state.weak_themes:
            st.session_state.weak_themes[theme] = {"incorrect": 0, "total": 0}
        st.session_state.weak_themes[theme]["total"] += 1
        
        st.session_state.total += 1
        st.session_state.history.append({
            "category": clue["category"],
            "clue": clue["clue"],
            "correct_response": clue["correct_response"],
            "user_response": user_input,
            "was_correct": correct,
            "time_taken": elapsed_time,
            "points_earned": points_earned
        })

        # Handle challenge mode progression
        if "challenge_mode" in st.session_state and st.session_state.challenge_mode:
            # Update challenge score
            if correct:
                st.session_state.challenge_score += int(points_earned > 0)
            
            # Move to next question
            st.session_state.challenge_current_clue = None
            st.session_state.challenge_question_num += 1
            
            # Show next button
            if st.button("Next Challenge Question →", type="primary", use_container_width=True):
                st.rerun()
        else:
            st.session_state.current_clue = None
            
            # Reset AI mode states
            if st.session_state.ai_mode:
                st.session_state.buzzer_winner = None
                st.session_state.current_turn = None
            
            # Add a next button for better flow
            if st.button("Next Question →", type="primary", use_container_width=True):
                st.rerun()

# Expandable sections at the bottom
col_exp1, col_exp2, col_exp3 = st.columns(3)

with col_exp1:
    # Session history
    if st.session_state.history:
        with st.expander("📊 Session History", expanded=False):
            history_df = pd.DataFrame(st.session_state.history)
            
            # Summary metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Questions", len(history_df))
                avg_time = history_df["time_taken"].mean()
                st.metric("Avg Time", f"{avg_time:.1f}s")
            with col2:
                st.metric("Correct", len(history_df[history_df["was_correct"]]))
                acc = (len(history_df[history_df["was_correct"]]) / len(history_df)) * 100
                st.metric("Accuracy", f"{acc:.1f}%")
            
            # Show last 5 questions
            st.markdown("#### Recent Questions")
            recent = history_df.tail(5)[["category", "clue", "correct_response", "was_correct"]]
            st.dataframe(recent, use_container_width=True, height=200)

with col_exp2:
    if st.session_state.is_signed_in:
        if st.session_state.bookmarks:
            with st.expander(f"🔖 Bookmarks ({len(st.session_state.bookmarks)})", expanded=False):
                st.markdown("#### Your Bookmarked Questions")
                all_bookmarks = list(reversed(st.session_state.bookmarks))  # newest first

                # Search / filter
                search = st.text_input(
                    "🔍 Search bookmarks",
                    key="bookmark_search",
                    placeholder="Filter by category, clue, or answer...",
                )
                if search:
                    q = search.strip().lower()
                    all_bookmarks = [
                        b for b in all_bookmarks
                        if q in b["category"].lower()
                        or q in b["clue"].lower()
                        or q in b["correct_response"].lower()
                    ]
                    if not all_bookmarks:
                        st.info("No bookmarks match your search.")

                # Pagination
                PER_PAGE = 5
                total = len(all_bookmarks)
                total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
                if st.session_state.get("bookmark_page", 1) > total_pages:
                    st.session_state.bookmark_page = total_pages
                page = 1
                if total_pages > 1:
                    page = st.number_input(
                        "Page",
                        min_value=1,
                        max_value=total_pages,
                        step=1,
                        key="bookmark_page",
                    )
                start = (page - 1) * PER_PAGE
                page_bookmarks = all_bookmarks[start:start + PER_PAGE]

                for i, bookmark in enumerate(page_bookmarks, start + 1):
                    st.markdown(f"**{i}. {bookmark['category']}**")
                    st.markdown(f"Q: {bookmark['clue']}")
                    st.markdown(f"A: *{bookmark['correct_response']}*")
                    col_bm1, col_bm2 = st.columns(2)
                    with col_bm1:
                        if st.button(f"Practice #{i}", key=f"practice_bookmark_{i}"):
                            st.session_state.current_clue = {
                                "category": bookmark["category"],
                                "clue": bookmark["clue"],
                                "correct_response": bookmark["correct_response"]
                            }
                            st.rerun()
                    with col_bm2:
                        if st.button(f"🗑️ Remove #{i}", key=f"remove_bookmark_{i}"):
                            st.session_state.bookmarks = [
                                b for b in st.session_state.bookmarks
                                if _bookmark_key(b) != _bookmark_key(bookmark)
                            ]
                            try:
                                delete_bookmark(
                                    bookmark_identity(),
                                    bookmark["category"],
                                    bookmark["clue"],
                                    bookmark["correct_response"],
                                )
                            except Exception as e:
                                import sys
                                print(f"[bookmarks] delete failed: {e}", file=sys.stderr)
                            st.rerun()
                    st.markdown("---")
                if total_pages > 1:
                    st.caption(f"Showing {start + 1}–{min(start + PER_PAGE, total)} of {total} bookmarks")
        else:
            with st.expander("🔖 Bookmarks (0)", expanded=False):
                st.info("No bookmarks yet! Click the 🔖 button during gameplay to bookmark questions.")
    else:
        with st.expander("🔖 Bookmarks", expanded=False):
            st.info("🔒 Sign in to save and review bookmarks.")
            guest_sign_in_button("signin_bookmarks_panel")

with col_exp3:
    if st.session_state.is_signed_in:
        if st.session_state.weak_themes:
            with st.expander("📈 Theme Performance", expanded=False):
                st.markdown("#### Your Performance by Theme")
                theme_data = []
                for theme, stats in st.session_state.weak_themes.items():
                    if stats["total"] > 0:
                        accuracy = ((stats["total"] - stats["incorrect"]) / stats["total"]) * 100
                        theme_data.append({
                            "Theme": theme,
                            "Accuracy": f"{accuracy:.0f}%",
                            "Questions": stats["total"],
                            "Missed": stats["incorrect"]
                        })
                if theme_data:
                    theme_data.sort(key=lambda x: float(x["Accuracy"].rstrip("%")))
                    weak_themes = [t for t in theme_data if float(t["Accuracy"].rstrip("%")) < 50]
                    if weak_themes:
                        st.warning(f"🎯 Focus areas: {', '.join([t['Theme'] for t in weak_themes[:3]])}")
                    theme_df = pd.DataFrame(theme_data)
                    st.dataframe(theme_df, use_container_width=True, height=200)
        else:
            with st.expander("📈 Theme Performance", expanded=False):
                st.info("Play some questions to see your performance by theme!")
    else:
        with st.expander("📈 Theme Performance", expanded=False):
            st.info("🔒 Sign in to see detailed analytics.")
            guest_sign_in_button("signin_analytics")


# ── FOOTER DISCLAIMER ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;padding:1.5rem 0 0.5rem;font-size:0.78rem;color:#a99fba;line-height:1.7;max-width:600px;margin:0 auto;">
<strong style="color:#7c7492;">Jayopardy</strong> is an independent trivia training tool built for serious quiz preparation.<br>
It is not affiliated with, sponsored by, or endorsed by Jeopardy! Productions, Sony Pictures Television, or any official <em>Jeopardy!</em> entity.<br>
Question data is sourced from publicly available archives. No personal data beyond session scores is stored for guest players.
</div>
""", unsafe_allow_html=True)
