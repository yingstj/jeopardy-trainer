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
from r2_jeopardy_data_loader import load_jeopardy_data_from_r2, start_prewarm

# Kick off background dataset download at server startup so the first user
# (often a guest) doesn't wait 20s for the R2 fetch.
start_prewarm()
from auth_manager import AuthManager
from category_analyzer import JeopardyCategoryAnalyzer
from database import initialize_database, get_db_connection

# Sentinel value written into the answer input by the JS countdown's
# auto-submit handler. The Python grader uses this to distinguish a
# timer-triggered submit from a user-clicked submit. Must match the
# string used in the JS in the countdown component below.
AUTO_SUBMIT_TIMEOUT_SENTINEL = "__JPY_AUTO_SUBMIT_TIMEOUT__"

# Initialize the database
initialize_database()

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
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced styling
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:opsz,wght,SOFT@9..144,300..600,0..100&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
    :root {
        --ink: #f7f4ea;
        --ink-soft: #d9d5c8;
        --muted: #a7aec6;
        --muted-2: #737c9d;
        --bg: #080d2b;
        --card: #111944;
        --line: #293363;
        --line-soft: #1a2450;
        --accent: #e5b94f;
        --accent-soft: #2d2a42;
        --ring: rgba(229, 185, 79, 0.28);
        --danger: #ef7777;
        --success: #72d6b0;
        --shadow-sm: 0 8px 24px rgba(2, 5, 24, 0.28);
        --shadow-md: 0 18px 45px rgba(2, 5, 24, 0.42);
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--ink);
        font-feature-settings: "ss01", "cv11";
    }

    .stApp { background: radial-gradient(circle at 50% -20%, #1d2860 0, var(--bg) 42rem); }
    .stApp::before { content:""; position:fixed; inset:0; pointer-events:none; opacity:.035;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 160 160' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.5'/%3E%3C/svg%3E"); z-index:0; }

    h1, h2, h3 {
        font-family: 'Fraunces', Georgia, serif !important;
        font-weight: 400 !important;
        letter-spacing: -0.015em;
        font-variation-settings: "opsz" 96, "SOFT" 50;
    }
    h1 { font-weight: 400 !important; }
    h2, h3 { font-weight: 500 !important; }

    /* Overline (small caps style label) */
    .overline {
        font-family: 'Inter', sans-serif;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-weight: 600;
        color: var(--muted);
    }

    /* Main container */
    .main { padding: 0 1rem; }
    .block-container { padding-top: 2.25rem; padding-bottom: 4rem; max-width: 1080px; }

    /* Custom header — refined editorial masthead */
    .main-header {
        background: transparent;
        padding: 1.5rem 0 1.75rem;
        margin-bottom: 2rem;
        border-bottom: 1px solid var(--line);
        text-align: center;
    }
    .main-header h1 {
        color: var(--ink) !important; margin: 0;
        font-size: 2.6rem;
        font-style: italic;
        letter-spacing: -0.02em;
    }
    .main-header p {
        color: var(--muted);
        text-align: center; margin-top: 0.35rem; font-size: 0.95rem;
    }

    /* Theme card — quiet category label */
    .theme-card {
        background: transparent;
        color: var(--muted);
        border: none;
        padding: 0.5rem 0 0.85rem;
        margin-bottom: 0.75rem;
        text-align: left;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.78rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        border-bottom: 1px solid var(--line);
    }

    /* Clue card — editorial reading surface */
    .clue-card {
        background: var(--card);
        border: 1px solid var(--line);
        padding: 2.25rem 2rem;
        border-radius: 6px;
        margin: 1.25rem 0;
        box-shadow: var(--shadow-sm);
        position: relative;
    }
    .clue-card::before {
        content: "";
        position: absolute; left: 2rem; top: -1px;
        width: 32px; height: 2px;
        background: var(--accent);
    }
    .clue-text {
        font-family: 'Fraunces', Georgia, serif;
        font-weight: 400;
        font-size: 1.45rem;
        color: var(--ink);
        line-height: 1.55;
        letter-spacing: -0.005em;
    }

    /* Score display */
    .score-container {
        background: var(--card);
        border: 1px solid var(--line);
        padding: 1.1rem 1rem;
        border-radius: 6px;
        text-align: center; color: var(--ink);
    }
    .score-label {
        font-size: 0.7rem; color: var(--muted);
        margin-bottom: 0.35rem; letter-spacing: 0.18em;
        text-transform: uppercase; font-weight: 600;
    }
    .score-value {
        font-size: 2rem; font-weight: 400;
        font-family: 'Fraunces', Georgia, serif;
        color: var(--ink);
        letter-spacing: -0.02em;
    }

    /* Timer */
    .timer-container {
        background: var(--card);
        border: 1px solid var(--line);
        padding: 0.85rem 1rem; border-radius: 6px;
        text-align: center; color: var(--ink);
        margin-bottom: 1rem;
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.1rem;
        font-weight: 500;
    }

    /* Alerts */
    .stSuccess, div[data-testid="stAlertContentSuccess"] {
        background-color: #f5f9f3 !important;
        border: 1px solid #d8e3d2 !important;
        color: #2d4226 !important;
        border-radius: 6px !important;
    }
    .stError, div[data-testid="stAlertContentError"] {
        background-color: #faf2f0 !important;
        border: 1px solid #e9cdc6 !important;
        color: #6b2417 !important;
        border-radius: 6px !important;
    }

    /* Buttons — refined, restrained */
    .stButton > button {
        background: var(--ink);
        color: #ffffff;
        border: 1px solid var(--ink);
        padding: 0.6rem 1.5rem;
        font-size: 0.92rem;
        font-weight: 500;
        letter-spacing: 0.02em;
        border-radius: 4px;
        box-shadow: none;
        transition: background-color 0.18s ease, transform 0.12s ease;
    }
    .stButton > button:hover {
        background: var(--accent);
        border-color: var(--accent);
        transform: translateY(-1px);
    }
    .stButton > button:focus { box-shadow: 0 0 0 3px var(--ring) !important; }

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stNumberInput input,
    .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 4px !important;
        border: 1px solid var(--line) !important;
        background: var(--card) !important;
        font-size: 0.95rem !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus,
    .stNumberInput input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--ring) !important;
    }

    /* Tabs — minimal */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
        border-bottom: 1px solid var(--line);
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.65rem 0;
        font-weight: 500; color: var(--muted);
        font-size: 0.92rem;
        letter-spacing: 0.01em;
    }
    .stTabs [aria-selected="true"] { color: var(--ink) !important; }
    .stTabs [data-baseweb="tab-highlight"] {
        background: var(--ink) !important; height: 1px !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: var(--bg);
        border-right: 1px solid var(--line);
    }
    section[data-testid="stSidebar"] .stMarkdown { color: var(--ink); }

    /* Stat card */
    .stat-card {
        background: var(--card);
        border: 1px solid var(--line);
        padding: 1rem 0.85rem;
        border-radius: 6px;
        text-align: center;
    }
    .stat-number {
        font-size: 1.7rem; font-weight: 400;
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        letter-spacing: -0.02em;
    }
    .stat-label {
        font-size: 0.68rem; color: var(--muted);
        text-transform: uppercase; letter-spacing: 0.18em;
        font-weight: 600;
        margin-top: 0.2rem;
    }

    /* Progress bar — hairline */
    .progress-bar {
        background: var(--line-soft);
        border: none;
        height: 4px; border-radius: 999px;
        overflow: hidden; margin: 0.75rem 0;
    }
    .progress-fill {
        height: 100%;
        background: var(--accent);
        font-size: 0; /* hide percentage label for cleaner look */
        transition: width 0.4s ease;
    }

    /* Expander */
    .streamlit-expanderHeader, [data-testid="stExpander"] details summary {
        border-radius: 4px !important;
        font-weight: 500;
    }
    [data-testid="stExpander"] {
        border: 1px solid var(--line) !important;
        border-radius: 6px !important;
    }

    /* Dataframe */
    .stDataFrame { border-radius: 6px; overflow: hidden; border: 1px solid var(--line); }

    /* Caption refinement */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--muted) !important;
        font-style: italic;
        font-size: 0.85rem !important;
    }

    /* Hide Streamlit default footer */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    /* Header stats — elegant masthead style */
    .header-stats {
        display: flex;
        justify-content: center;
        gap: 3rem;
        margin-top: 1.25rem;
        padding-top: 0;
    }
    .header-stat { text-align: center; }
    .header-stat-value {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.6rem;
        font-weight: 400;
        color: var(--ink);
        letter-spacing: -0.02em;
        line-height: 1;
    }
    .header-stat-label {
        font-size: 0.68rem;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.2em;
        font-weight: 600;
        margin-top: 0.35rem;
    }

    /* Bold Jeopardy Energy: the shared Streamlit surface system */
    .main-header { padding: 1.8rem 0 2rem; margin-bottom: 2.25rem; border-bottom: 1px solid var(--line); }
    .main-header::before { content:"JAYOPARDY!  /  TRAINING GROUND"; display:block; color:var(--accent);
        font:700 .68rem 'Space Mono', monospace; letter-spacing:.2em; margin-bottom:.9rem; }
    .main-header h1 { color:var(--ink)!important; font-size:clamp(2.7rem,7vw,5.2rem); line-height:.95; font-style:normal; text-shadow:0 4px 30px rgba(229,185,79,.15); }
    .main-header p { color:var(--muted); font-size:.95rem; letter-spacing:.04em; }
    .theme-card { color:var(--accent); border:1px solid var(--accent); background:rgba(229,185,79,.07); border-radius:3px;
        padding:.65rem 1rem .55rem; font:700 .7rem 'Space Mono',monospace; letter-spacing:.16em; }
    .clue-card { background:linear-gradient(145deg,#172154,#0f163c); border:1px solid #39457c; border-radius:12px;
        padding:clamp(1.8rem,5vw,3.4rem) clamp(1.25rem,5vw,3rem); box-shadow:var(--shadow-md); }
    .clue-card::before { left:0; top:22%; width:4px; height:56%; background:var(--accent); }
    .clue-text { color:var(--ink); font-size:clamp(1.35rem,2.7vw,2.25rem); line-height:1.35; text-align:center; }
    .score-container,.stat-card,.timer-container { background:rgba(17,25,68,.88); border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow-sm); }
    .score-label,.stat-label { color:var(--muted); font-family:'Space Mono',monospace; }
    .score-value,.stat-number,.header-stat-value { color:var(--accent); }
    .progress-bar { background:#252e5b; height:7px; } .progress-fill { background:var(--accent); }
    .stMarkdown, .stText, label, p, li { color:var(--ink); }
    .stCaption,[data-testid="stCaptionContainer"] { color:var(--muted)!important; }
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button { background:var(--accent); color:#11162f; border:1px solid var(--accent);
        border-radius:5px; font-weight:700; box-shadow:0 5px 0 #9b7629; transition:transform .15s ease, background-color .15s ease; }
    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover { background:#f3cc6b; border-color:#f3cc6b; transform:translateY(-2px); }
    .stButton > button:active, .stFormSubmitButton > button:active { transform:translateY(2px); box-shadow:0 2px 0 #9b7629; }
    .stTextInput input,.stTextArea textarea,.stNumberInput input,
    .stSelectbox [data-baseweb="select"] > div { color:var(--ink)!important; background:#0d1438!important; border-color:#3b477b!important; border-radius:6px!important; }
    input::placeholder, textarea::placeholder { color:#747eaa!important; }
    .stTextInput input:focus,.stTextArea textarea:focus,.stNumberInput input:focus { border-color:var(--accent)!important; box-shadow:0 0 0 2px var(--ring)!important; }
    [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="list"] { background:#111944!important; color:var(--ink)!important; }
    [data-baseweb="menu"] li:hover,[data-baseweb="menu"] li[aria-selected="true"] { background:#293363!important; }
    [data-testid="stSidebar"] { background:#0b1235!important; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] hr { border-color:var(--line); }
    [data-testid="stSidebar"] .stMarkdown h2 { color:var(--accent)!important; }
    .stTabs [data-baseweb="tab-list"] { gap:1.4rem; border-color:var(--line); }
    .stTabs [data-baseweb="tab"] { color:var(--muted); font-weight:600; }
    .stTabs [aria-selected="true"] { color:var(--accent)!important; }
    .stTabs [data-baseweb="tab-highlight"] { background:var(--accent)!important; height:3px!important; }
    [data-testid="stExpander"], [data-testid="stExpander"] details, [data-testid="stExpander"] details summary { background:#111944!important; border-color:var(--line)!important; color:var(--ink)!important; }
    [data-testid="stAlert"] { border-radius:8px!important; }
    div[data-testid="stAlertContentSuccess"] { background:#103b3b!important; border-color:#287565!important; color:#b8f2d9!important; }
    div[data-testid="stAlertContentError"] { background:#42243b!important; border-color:#8b4055!important; color:#ffd0d0!important; }
    div[data-testid="stAlertContentWarning"] { background:#40351e!important; border-color:#8d722e!important; color:#ffe8a8!important; }
    div[data-testid="stAlertContentInfo"] { background:#172753!important; border-color:#3b5791!important; color:#c9d8ff!important; }
    [data-testid="stDataFrame"], .stDataFrame { border-color:var(--line)!important; }
    [data-testid="stForm"] { border-color:var(--line)!important; background:rgba(17,25,68,.35); border-radius:10px; }
    [data-testid="stCheckbox"] label, [data-testid="stRadio"] label { color:var(--ink)!important; }
    [data-testid="stSlider"] [role="slider"] { background:var(--accent)!important; border-color:var(--accent)!important; }
    @media (max-width: 700px) { .block-container { padding-top:1.25rem; } .header-stats { gap:1rem; } .main-header { margin-bottom:1.3rem; } }
</style>
""", unsafe_allow_html=True)

# Load and filter data
@st.cache_data
def load_data():
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
        # Load from R2
        with st.spinner("🎯 Loading dataset from Cloudflare R2..."):
            df = load_jeopardy_data_from_r2()
        
        if df.empty:
            st.error("Failed to load dataset from R2. Please check your connection and credentials.")
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

# SIDEBAR FOR SETTINGS
with st.sidebar:
    st.markdown("## 🎯 Jayopardy!")
    # Derive username from AuthManager
    current_username = st.session_state.get("user_name") or st.session_state.get("username") or "Player"
    st.session_state.username = current_username
    st.markdown(f"👤 **Player:** {current_username}")

    check_signed_in_status()

    if st.session_state.is_signed_in:
        st.markdown('<span style="display:inline-block;padding:.28rem .55rem;border:1px solid #e5b94f;border-radius:3px;color:#e5b94f;background:rgba(229,185,79,.08);font:700 .68rem Space Mono,monospace;letter-spacing:.14em;text-transform:uppercase;">Signed in</span>', unsafe_allow_html=True)

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
    
    st.markdown("---")
    
    # Quick actions
    if st.button("🎯 New Question", use_container_width=True):
        st.session_state.current_clue = None
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
    if not st.session_state.is_signed_in:
        st.caption("Sign in with an account to challenge friends.")
    else:
        st.caption("Challenge friends and track your wins.")
    
    if "challenge_manager" not in st.session_state:
        st.session_state.challenge_manager = ChallengeManager()
    challenge_manager = st.session_state.challenge_manager

    if st.session_state.is_signed_in:
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

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        auth.logout()

# MAIN GAME AREA


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
    st.markdown("""<div class="main-header"><h1>🎯 Jayopardy!</h1></div>""", unsafe_allow_html=True)
    
    col_player, col_vs, col_ai = st.columns([2, 1, 2])
    
    with col_player:
        player_color = "#667eea" if st.session_state.score >= st.session_state.ai_score else "#6c757d"
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: #ffffff; border: 1px solid #e7e5e4;
                    border-top: 3px solid {player_color}; border-radius: 12px; color: #0f172a;">
            <div style="font-size: 0.78rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;">👤 {st.session_state.username}</div>
            <div style="font-size: 2.5rem; font-weight: 800;">${st.session_state.score}</div>
            <div style="font-size: 0.8rem; color: #64748b;">Streak: {st.session_state.streak}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_vs:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0;">
            <div style="font-size: 1.5rem; font-weight: bold; color: #6c757d;">VS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_ai:
        ai_color = "#dc3545" if st.session_state.ai_score > st.session_state.score else "#6c757d"
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: #ffffff; border: 1px solid #e7e5e4;
                    border-top: 3px solid {ai_color}; border-radius: 12px; color: #0f172a;">
            <div style="font-size: 0.78rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;">🤖 {st.session_state.ai_personality}</div>
            <div style="font-size: 2.5rem; font-weight: 800;">${st.session_state.ai_score}</div>
            <div style="font-size: 0.8rem; color: #64748b;">Streak: {st.session_state.ai_streak}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Show who's winning
    if st.session_state.buzzer_winner:
        if st.session_state.buzzer_winner == "player":
            st.success(f"🎯 You buzzed in first! Your turn to answer.")
        else:
            st.info(f"🤖 {st.session_state.ai_personality} buzzed in first!")
else:
    # Regular mode header
    st.markdown(f"""
    <div class="main-header">
        <h1>🎯 Jayopardy!</h1>
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

# Check if categories are selected
if not st.session_state.selected_categories:
    st.warning("⚠️ Please select themes from the sidebar to start playing!")
    st.stop()

@st.cache_data
def get_filtered_df(selected_cats_tuple: tuple, selected_round: str, _df_sig: int):
    fdf = df[df["category"].isin(selected_cats_tuple)]
    if selected_round and selected_round != 'All Rounds':
        fdf = fdf[fdf['round'] == selected_round]
    return fdf

filtered_df = get_filtered_df(
    tuple(st.session_state.selected_categories),
    st.session_state.get('selected_round', 'All Rounds'),
    _df_signature,
)

if filtered_df.empty:
    st.warning("No clues found for selected themes/round. Please adjust your selection.")
    st.stop()

# Challenge Mode Game Logic
if "challenge_mode" in st.session_state and st.session_state.challenge_mode:
    challenge = st.session_state.current_challenge
    opponent = challenge["opponent"]
    
    # Display challenge header
    st.markdown(f"""
    <div style="background: #0f172a; color: #ffffff; padding: 1.5rem; border-radius: 14px;
                border-left: 4px solid #f59e0b;
                text-align: center; margin-bottom: 1rem;
                box-shadow: 0 10px 24px -12px rgba(15,23,42,0.35);">
        <h2 style="margin: 0; color: #ffffff;">⚔️ Challenge Mode</h2>
        <p style="margin: 0.5rem 0; color: rgba(255,255,255,0.78);">You vs {opponent}</p>
        <p style="margin: 0; color: rgba(255,255,255,0.78);">Question {st.session_state.challenge_question_num + 1} of {challenge['num_questions']}</p>
        <p style="margin: 0.4rem 0 0; font-size: 1.2rem; color: #f59e0b; font-weight: 700;">Your Score: {st.session_state.challenge_score}</p>
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
        challenge_df = filtered_df  # Fallback to regular filtered df
    
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
    <div style="background: linear-gradient(135deg,#312954,#171b4b); color: #f7f4ea; padding: 1.25rem 1.5rem; border-radius: 10px;
                border: 1px solid #e5b94f; border-left: 4px solid #e5b94f;
                text-align: center; margin-bottom: 1rem;
                box-shadow: 0 10px 28px rgba(2, 5, 24, .35);">
        <h2 style="margin: 0; font:600 1.6rem Fraunces,Georgia,serif; color: #e5b94f;">DAILY DOUBLE</h2>
        <p style="margin: 0.3rem 0 0; color: #d9d5c8;">Double points for this question</p>
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
    st.markdown("### 🔔 Ready to buzz in!")
    
    # Check if AI buzzes first (happens automatically based on difficulty)
    import time
    ai_buzz_delay = AI_DIFFICULTY[st.session_state.ai_difficulty]["buzzer_speed"]
    
    # Create a container for dynamic updates
    buzz_container = st.container()
    
    with buzz_container:
        col_buzz1, col_buzz2 = st.columns(2)
        
        # Add a placeholder for AI buzzing notification
        ai_buzz_placeholder = st.empty()
        
        with col_buzz1:
            if st.button("🎯 BUZZ IN!", use_container_width=True, key="buzzer", type="primary"):
                # Player buzzed - determine who was faster
                winner, reaction_time = simulate_buzzer_race(st.session_state.ai_difficulty)
                st.session_state.buzzer_winner = winner
                st.session_state.current_turn = winner
                
                if winner == "player":
                    st.balloons()
                    st.success("🎯 You buzzed in first!")
                else:
                    st.warning(f"🤖 {st.session_state.ai_personality} was faster!")
                st.rerun()
        
        with col_buzz2:
            # Simulate AI potentially buzzing on its own
            # Easy: 30% chance, Medium: 50% chance, Hard: 70% chance
            buzz_chances = {"Easy": 0.3, "Medium": 0.5, "Hard": 0.7}
            if random.random() < buzz_chances[st.session_state.ai_difficulty]:
                # AI decides to buzz
                with st.spinner(f"🤖 {st.session_state.ai_personality} is buzzing in..."):
                    time.sleep(ai_buzz_delay)
                st.session_state.buzzer_winner = "ai"
                st.session_state.current_turn = "ai"
                st.warning(f"🤖 {st.session_state.ai_personality} buzzed in!")
                st.rerun()
            else:
                st.info(f"⏱️ Be quick! {st.session_state.ai_personality} is thinking...")
    
    # Don't show answer form during buzzer phase
    st.stop()

elif st.session_state.ai_mode and st.session_state.buzzer_winner == "ai" and not st.session_state.study_mode:
    # AI is answering
    st.info(f"🤖 {st.session_state.ai_personality} buzzed in first!")
    
    # Simulate AI response
    with st.spinner(f"{st.session_state.ai_personality} is thinking..."):
        is_correct, thinking_time = simulate_ai_response(
            clue["clue"],
            clue["category"],
            st.session_state.ai_difficulty,
            st.session_state.ai_personality
        )
        
        # Add artificial delay for realism
        import time
        time.sleep(min(thinking_time, 2))
    
    if is_correct:
        st.error(f"🤖 {st.session_state.ai_personality} got it right! The answer was: **{clue['correct_response']}**")
        
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
        st.success(f"❌ {st.session_state.ai_personality} got it wrong!")
        st.info("Your chance to steal the point! Answer below:")
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
                 <div style="font-family: 'DM Sans', sans-serif; color: #f7f4ea;
                             background: linear-gradient(135deg,#151e50,#0d1438); border: 1px solid #3b477b;
                             padding: 0.75rem 1rem; border-radius: 8px; box-shadow: 0 8px 22px rgba(2,5,24,.3);">
                  <div style="display:flex; justify-content:space-between; align-items:center;
                               font-size: 0.9rem; letter-spacing:.02em;">
                     <span style="color:#a7aec6;text-transform:uppercase;font:700 .66rem 'Space Mono',monospace;">Time remaining</span>
                     <span id="jpy-timer-value" style="font:700 1.05rem 'Space Mono',monospace; color:#e5b94f; font-variant-numeric: tabular-nums;">{_limit_s}.0s</span>
                  </div>
                   <div style="margin-top:0.55rem; height:7px; background:#293363;
                              border-radius:4px; overflow:hidden;">
                    <div id="jpy-timer-bar" style="height:100%; width:100%;
                                                     background:#e5b94f;
                                                    transition: width 0.12s linear,
                                                                background-color 0.3s ease;">
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
                             barEl.style.background = '#ef7777';
                        }} else if (pct <= 50) {{
                             barEl.style.background = '#f0a957';
                        }} else {{
                             barEl.style.background = '#e5b94f';
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
        if bookmark_entry not in st.session_state.bookmarks:
            st.session_state.bookmarks.append(bookmark_entry)
            st.success("🔖 Bookmarked!")
    else:
        st.info("🔒 Sign in to save bookmarks — it's free.")

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
            st.success(f"🎉 **Correct!** +${points_earned}")
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
                st.error("❌ **Incorrect** — no answer submitted in time.")
            else:
                st.error("❌ **Incorrect**")
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
                for i, bookmark in enumerate(st.session_state.bookmarks[-5:], 1):
                    st.markdown(f"**{i}. {bookmark['category']}**")
                    st.markdown(f"Q: {bookmark['clue']}")
                    st.markdown(f"A: *{bookmark['correct_response']}*")
                    if st.button(f"Practice #{i}", key=f"practice_bookmark_{i}"):
                        st.session_state.current_clue = {
                            "category": bookmark["category"],
                            "clue": bookmark["clue"],
                            "correct_response": bookmark["correct_response"]
                        }
                        st.rerun()
                    st.markdown("---")
                if len(st.session_state.bookmarks) > 5:
                    st.info(f"Showing 5 of {len(st.session_state.bookmarks)} bookmarks")
        else:
            with st.expander("🔖 Bookmarks (0)", expanded=False):
                st.info("No bookmarks yet! Click the 🔖 button during gameplay to bookmark questions.")
    else:
        with st.expander("🔖 Bookmarks", expanded=False):
            st.info("🔒 Sign in to save and review bookmarks.")

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
