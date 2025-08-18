import streamlit as st
import pandas as pd
import random
import re
import os
import datetime
import time
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Set page config
st.set_page_config(page_title="Jayopardy! Trainer", page_icon="🧠", layout="wide")

# Custom CSS for modern game board design
st.markdown("""
<style>
/* Main app background */
.stApp {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white;
}

/* Text color fixes */
.stMarkdown, .stText, label {
    color: white !important;
}

/* Caption text */
.stCaption {
    color: #e0e0e0 !important;
}

/* Help text */
[data-testid="stHelpBlock"] {
    color: #d0d0d0 !important;
}

/* Metric labels */
[data-testid="metric-container"] label {
    color: #e0e0e0 !important;
}

/* Metric values */
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: white !important;
}

/* Metric delta */
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    color: #ffc107 !important;
}

/* All icons and SVGs */
svg {
    stroke: white !important;
    opacity: 0.9;
}

/* Sidebar specific buttons - make text smaller to prevent wrapping */
[data-testid="stSidebar"] .stButton > button {
    font-size: 13px !important;
    padding: 8px 12px !important;
    white-space: nowrap !important;
}

/* Fix info, warning, and success boxes text */
.stAlert > div {
    color: white !important;
}

/* Info boxes specifically */
div[data-testid="stInfo"] > div {
    background: rgba(102, 126, 234, 0.2) !important;
    color: white !important;
}

/* Warning boxes */
div[data-testid="stWarning"] > div {
    background: rgba(255, 193, 7, 0.2) !important;
    color: white !important;
}

/* Success boxes */
div[data-testid="stSuccess"] > div {
    background: rgba(76, 175, 80, 0.2) !important;
    color: white !important;
}

/* Error boxes */
div[data-testid="stError"] > div {
    background: rgba(244, 67, 54, 0.2) !important;
    color: white !important;
}

/* Header styling */
.header-container {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    padding: 15px 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-radius: 15px;
    margin-bottom: 20px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.logo-wrapper {
    display: flex;
    align-items: center;
    gap: 15px;
}

.logo-small {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-radius: 10px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: bold;
    color: white;
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

/* Score display */
.score-display {
    background: rgba(255, 255, 255, 0.1);
    padding: 8px 20px;
    border-radius: 20px;
    font-size: 18px;
    font-weight: 600;
    color: #4ade80;
    display: inline-block;
}

/* Question box styling */
.question-box {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 2px solid rgba(102, 126, 234, 0.3);
    border-radius: 20px;
    padding: 40px;
    box-shadow: 0 20px 60px rgba(102, 126, 234, 0.3);
    margin: 20px 0;
}

/* Category and theme display */
.category-header {
    text-align: center;
    margin-bottom: 20px;
}

.theme-label {
    font-size: 14px;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 5px;
}

.category-label {
    font-size: 24px;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Clue box */
.clue-box {
    background: rgba(102, 126, 234, 0.1);
    border: 2px solid rgba(102, 126, 234, 0.3);
    border-radius: 15px;
    padding: 30px;
    margin: 20px 0;
    text-align: center;
}

.clue-text {
    font-size: 22px;
    line-height: 1.6;
    color: white;
}

/* Stats cards */
.stat-card {
    background: rgba(255, 255, 255, 0.1);
    padding: 20px;
    border-radius: 15px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    text-align: center;
    margin: 10px 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.stat-label {
    font-size: 12px;
    color: #e0e0e0;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

.stat-value {
    font-size: 24px;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
    border: none;
    border-radius: 10px;
    padding: 10px 25px;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    background: linear-gradient(135deg, #764ba2, #667eea) !important;
}

/* Form submit button specific styling */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
    font-weight: 600 !important;
}

/* Input field */
.stTextInput > div > div > input {
    background: rgba(255, 255, 255, 0.05);
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: white;
    padding: 15px;
    font-size: 16px;
}

.stTextInput > div > div > input:focus {
    border-color: #667eea;
    background: rgba(255, 255, 255, 0.08);
}

/* Sidebar styling */
.css-1d391kg, [data-testid="stSidebar"] {
    background: rgba(0, 0, 0, 0.3);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
}

[data-testid="stSidebar"] .stMarkdown {
    color: white !important;
}

/* Sidebar collapse button - make it visible */
[data-testid="collapsedControl"] {
    background: rgba(255, 255, 255, 0.15) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    color: white !important;
}

[data-testid="collapsedControl"]:hover {
    background: rgba(255, 255, 255, 0.25) !important;
    border: 1px solid rgba(255, 255, 255, 0.5) !important;
}

/* Sidebar expand/collapse icon */
[data-testid="collapsedControl"] svg {
    stroke: white !important;
    fill: white !important;
}

/* Expander styling */
.streamlit-expanderHeader {
    background: rgba(255, 255, 255, 0.1) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 10px;
    color: white !important;
}

.streamlit-expanderHeader:hover {
    background: rgba(255, 255, 255, 0.15) !important;
}

/* Expander arrow icon */
.streamlit-expanderHeader svg {
    stroke: white !important;
    fill: white !important;
}

/* Select box styling */
.stSelectbox > div > div {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
}

/* Success/Error/Info boxes */
.stAlert {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 10px;
}

/* Timer display */
.timer-display {
    font-size: 32px;
    font-weight: bold;
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Focus area warning */
.focus-area-warning {
    background: linear-gradient(135deg, #f97316, #ea580c);
    color: white;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
    text-align: center;
    font-weight: 600;
}

/* Checkbox styling */
.stCheckbox > label {
    color: white !important;
}

/* Checkbox text specifically */
.stCheckbox > label > div[data-testid="stMarkdownContainer"] > p {
    color: white !important;
}

/* Expander content text */
.streamlit-expanderContent {
    color: white !important;
}

.streamlit-expanderContent p {
    color: white !important;
}

.streamlit-expanderContent .stMarkdown {
    color: white !important;
}

/* Number input styling */
.stNumberInput > div > div > input {
    background: rgba(255, 255, 255, 0.05);
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: white;
}

/* Multiselect styling */
.stMultiSelect > div > div {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
}

.stMultiSelect > div > div > div {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# Import authentication manager
try:
    from auth_manager import AuthManager
    auth = AuthManager()
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    auth = None

# Load model once
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_model()

# Normalize text for fuzzy matching
def normalize(text):
    text = text.lower()
    text = re.sub(r"^(what|who|where|when|why|how)\s+(is|are|was|were)\s+", "", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()

# Get sample data for fallback
def get_sample_data():
    """Return sample Jeopardy data for testing/fallback"""
    return pd.DataFrame({
        'category': ['HISTORY'] * 10 + ['SCIENCE'] * 10 + ['MOVIES'] * 10 + ['GEOGRAPHY'] * 10 + ['LITERATURE'] * 10,
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
            'This film features the line "I\'ll be back"',
            'This is the longest river in the world',
            'This mountain range contains Mount Everest',
            'This is the smallest country in the world',
            'This desert is the largest hot desert in the world',
            'This is the deepest point in Earth\'s oceans',
            'This country has the most natural lakes',
            'This is the capital of Australia',
            'This strait separates Europe from Asia in Turkey',
            'This is the largest island in the world',
            'This U.S. state is the largest by area',
            'This author wrote "Romeo and Juliet"',
            'This novel begins "Call me Ishmael"',
            'This author created the detective Sherlock Holmes',
            'This epic poem by Homer tells of the fall of Troy',
            'This dystopian novel by George Orwell was published in 1949',
            'This American author wrote "The Great Gatsby"',
            'This is the best-selling book series of all time',
            'This playwright wrote "A Streetcar Named Desire"',
            'This novel features the character Atticus Finch',
            'This Russian author wrote "War and Peace"'
        ],
        'correct_response': [
            'Benjamin Franklin', '1776', '1803', 'Ronald Reagan', 'Pennsylvania',
            'Mayflower', 'John Hancock', 'New York City', '1849', 'Alaska',
            'Hydrogen', '299,792,458', 'Charles Darwin', '100', 'Mars',
            '46', 'Skin', 'Oxygen', 'Gravity', 'Deoxyribonucleic acid',
            'Parasite', 'Steven Spielberg', 'Leonardo DiCaprio', 'Star Wars', 'The Wizard of Oz',
            'Heath Ledger', 'The Lord of the Rings: The Return of the King', 'Finding Nemo', 'Robert Downey Jr.', 'The Terminator',
            'Nile River', 'Himalayas', 'Vatican City', 'Sahara', 'Mariana Trench',
            'Canada', 'Canberra', 'Bosphorus', 'Greenland', 'Alaska',
            'William Shakespeare', 'Moby-Dick', 'Arthur Conan Doyle', 'The Iliad', '1984',
            'F. Scott Fitzgerald', 'Harry Potter', 'Tennessee Williams', 'To Kill a Mockingbird', 'Leo Tolstoy'
        ],
        'round': ['Jeopardy'] * 25 + ['Double Jeopardy'] * 25,
        'game_id': [str(i//5) for i in range(50)]
    })

# Load and filter data
@st.cache_data
def load_data():
    import requests
    
    # Try local file first
    local_file = "data/all_jeopardy_clues.csv"
    if os.path.exists(local_file) and os.path.getsize(local_file) > 1000:  # Check file is not empty
        try:
            with st.spinner("Loading dataset..."):
                df = pd.read_csv(local_file)
            df = df.dropna(subset=["clue", "correct_response"])
            if len(df) > 100:  # Make sure we have real data
                return df
        except Exception as e:
            st.warning(f"Local file issue: {e}")
    
    # Try downloading from GitHub
    try:
        with st.spinner("Downloading Jeopardy dataset from GitHub (this may take a minute)..."):
            url = "https://github.com/yingstj/jeopardy-trainer/raw/main/data/all_jeopardy_clues.csv"
            
            # Download directly into pandas
            df = pd.read_csv(url)
            df = df.dropna(subset=["clue", "correct_response"])
            
            # Check for data quality
            bad_answers = df[df['correct_response'].str.contains(r'^\$\d+\s+\d+$', na=False, regex=True)]
            if len(bad_answers) > 0:
                st.warning(f"Found {len(bad_answers)} corrupted answers. Using sample data instead.")
                return get_sample_data()
            
            if len(df) > 100:
                st.success(f"Successfully loaded {len(df):,} Jeopardy clues!")
                # Save locally for next time
                os.makedirs("data", exist_ok=True)
                df.to_csv("data/all_jeopardy_clues.csv", index=False)
                return df
    except Exception as e:
        st.warning(f"Could not download from GitHub: {e}")
    
    # Fall back to R2 if available
    try:
        from r2_jeopardy_data_loader import load_jeopardy_data_from_r2
        with st.spinner("Trying Cloudflare R2..."):
            df = load_jeopardy_data_from_r2()
        
        if not df.empty:
            df = df.dropna(subset=["clue", "correct_response"])
            if len(df) > 100:
                return df
    except:
        pass  # R2 not configured
    
    # Final fallback - use sample data
    st.warning("Using sample data (50 questions). Full dataset couldn't be loaded.")
    return get_sample_data()

# Initialize global variables and session state
model = load_model()

# Track session state
if "history" not in st.session_state:
    st.session_state.history = []

if "score" not in st.session_state:
    st.session_state.score = 0
    st.session_state.total = 0

if "current_streak" not in st.session_state:
    st.session_state.current_streak = 0
    st.session_state.best_streak = 0

if "start_time" not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()

if "current_clue" not in st.session_state:
    st.session_state.current_clue = None

# Progress tracking uses memory instead of file storage for Streamlit Cloud compatibility
if "progress_data" not in st.session_state:
    st.session_state.progress_data = []

# Adaptive training mode
if "adaptive_mode" not in st.session_state:
    st.session_state.adaptive_mode = False
    
if "weak_categories" not in st.session_state:
    st.session_state.weak_categories = {}

# Timer settings
if "use_timer" not in st.session_state:
    st.session_state.use_timer = False
    
if "timer_seconds" not in st.session_state:
    st.session_state.timer_seconds = 5

# Add custom CSS for Jeopardy blue theme
st.markdown("""
<style>
    /* Jeopardy blue colors */
    :root {
        --jeopardy-blue: #060CE9;
        --jeopardy-dark-blue: #0520A5;
        --jeopardy-gold: #FFD700;
    }
    
    /* Headers in Jeopardy blue */
    h1, h2, h3 {
        color: #060CE9 !important;
    }
    
    /* Progress bar Jeopardy blue */
    .stProgress > div > div > div > div {
        background-color: #060CE9;
    }
</style>
""", unsafe_allow_html=True)

# Check authentication (if available)
if AUTH_AVAILABLE and auth:
    if not st.session_state.get('authenticated', False):
        auth.show_login_page()
        st.stop()
    # Show user menu in sidebar
    auth.show_user_menu()
else:
    # No auth available - show warning but let app work
    st.sidebar.warning("Authentication not available - progress won't be saved between sessions")

# Create modern header
st.markdown("""
<div class="header-container">
    <div class="logo-wrapper">
        <div class="logo-small">J!</div>
        <h2 style='color: white; margin: 0; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Jayopardy!</h2>
    </div>
    <div style='display: flex; gap: 20px; align-items: center;'>
        <div class="score-display">Score: {}/{} ({}%)</div>
    </div>
</div>
""".format(
    st.session_state.score,
    st.session_state.total,
    int((st.session_state.score / st.session_state.total * 100)) if st.session_state.total > 0 else 0
), unsafe_allow_html=True)

# Stats bar with modern cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">Session Score</div>
        <div class="stat-value">{}/{}</div>
    </div>
    """.format(st.session_state.score, st.session_state.total), unsafe_allow_html=True)

with col2:
    accuracy = (st.session_state.score / st.session_state.total * 100) if st.session_state.total > 0 else 0
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">Accuracy</div>
        <div class="stat-value">{:.0f}%</div>
    </div>
    """.format(accuracy), unsafe_allow_html=True)

with col3:
    streak = st.session_state.get('current_streak', 0)
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">Current Streak</div>
        <div class="stat-value">{}</div>
    </div>
    """.format(streak), unsafe_allow_html=True)

with col4:
    if AUTH_AVAILABLE and auth and st.session_state.get('authenticated', False):
        try:
            from pathlib import Path
            import json
            user_id = auth.get_user_id(st.session_state.user_email)
            session_file = Path(f"user_data/{user_id}_session.json")
            if session_file.exists():
                with open(session_file, 'r') as f:
                    saved_data = json.load(f)
                    all_history = saved_data.get('history', [])
                    if all_history:
                        total_all = len(all_history)
                        st.markdown("""
                        <div class="stat-card">
                            <div class="stat-label">Lifetime Questions</div>
                            <div class="stat-value">{}</div>
                        </div>
                        """.format(total_all), unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div class="stat-card">
                            <div class="stat-label">Lifetime Questions</div>
                            <div class="stat-value">0</div>
                        </div>
                        """, unsafe_allow_html=True)
        except:
            st.markdown("""
            <div class="stat-card">
                <div class="stat-label">Lifetime Questions</div>
                <div class="stat-value">N/A</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="stat-card">
            <div class="stat-label">Session Time</div>
            <div class="stat-value">--:--</div>
        </div>
        """, unsafe_allow_html=True)

# Loading spinner while data is being fetched
with st.spinner("Loading Jeopardy dataset..."):
    df = load_data()

if df.empty:
    st.error("❌ Failed to load Jeopardy dataset.")
    st.info("Check your internet connection or contact the administrator.")
    st.stop()

# Load theme mapping
@st.cache_data
def load_theme_mapping():
    """Load category to theme mapping"""
    try:
        import os
        if os.path.exists('data/category_themes.csv'):
            theme_df = pd.read_csv('data/category_themes.csv')
            return dict(zip(theme_df['category'], theme_df['theme']))
        else:
            # Create basic theme mapping if file doesn't exist
            return create_theme_mapping(df)
    except:
        return create_theme_mapping(df)

def create_theme_mapping(df):
    """Create theme mapping based on Jeopardy's top 30 most common categories"""
    import re
    theme_map = {}
    
    for cat in df['category'].unique():
        if not cat:
            continue
        cat_upper = str(cat).upper()
        
        # Map to Jeopardy's Top 30 Most Common Categories
        # Check specific patterns in order of priority
        
        # American History (includes U.S. History, Presidents)
        if any(word in cat_upper for word in ['U.S.', 'UNITED STATES', 'AMERICA', 'PRESIDENT', 
                                                'CIVIL WAR', 'REVOLUTION', 'FOUNDING']):
            theme_map[cat] = 'AMERICAN HISTORY'
        # World History
        elif any(word in cat_upper for word in ['WORLD HISTORY', 'EMPIRE', 'DYNASTY', 'ANCIENT',
                                                  'MEDIEVAL', 'RENAISSANCE', 'WORLD WAR']):
            theme_map[cat] = 'WORLD HISTORY'
        # Science
        elif any(word in cat_upper for word in ['SCIENCE', 'BIOLOGY', 'CHEMISTRY', 'PHYSICS',
                                                  'ANATOMY', 'ELEMENT', 'ATOM', 'NATURE']):
            theme_map[cat] = 'SCIENCE'
        # Literature (includes Books & Authors)
        elif any(word in cat_upper for word in ['LITERATURE', 'BOOK', 'AUTHOR', 'POET', 'NOVEL',
                                                  'SHAKESPEARE', 'WRITER', 'FICTION']):
            theme_map[cat] = 'LITERATURE'
        # World Geography (includes World Capitals, Islands)
        elif any(word in cat_upper for word in ['WORLD GEOGRAPHY', 'CONTINENT', 'CAPITAL',
                                                  'ISLAND', 'HEMISPHERE', 'NATION']):
            theme_map[cat] = 'WORLD GEOGRAPHY'
        # U.S. Geography (includes U.S. Cities)
        elif any(word in cat_upper for word in ['U.S. GEOGRAPHY', 'U.S. CIT', 'AMERICAN CIT',
                                                  'STATE', 'TERRITORY']):
            theme_map[cat] = 'U.S. GEOGRAPHY'
        # Sports
        elif any(word in cat_upper for word in ['SPORT', 'FOOTBALL', 'BASEBALL', 'BASKETBALL',
                                                  'HOCKEY', 'TENNIS', 'GOLF', 'OLYMPIC']):
            theme_map[cat] = 'SPORTS'
        # Business & Industry
        elif any(word in cat_upper for word in ['BUSINESS', 'INDUSTRY', 'COMPANY', 'CORPORATION',
                                                  'ECONOMY', 'MARKET', 'ENTREPRENEUR']):
            theme_map[cat] = 'BUSINESS & INDUSTRY'
        # Religion (includes The Bible)
        elif any(word in cat_upper for word in ['RELIGION', 'BIBLE', 'CHURCH', 'GOSPEL',
                                                  'TESTAMENT', 'FAITH', 'SAINT']):
            theme_map[cat] = 'RELIGION'
        # Mythology
        elif any(word in cat_upper for word in ['MYTH', 'LEGEND', 'GOD', 'GODDESS',
                                                  'OLYMPUS', 'NORSE', 'DEITY']):
            theme_map[cat] = 'MYTHOLOGY'
        # Television
        elif any(word in cat_upper for word in ['TV', 'TELEVISION', 'SHOW', 'SERIES',
                                                  'SITCOM', 'DRAMA', 'NETWORK']):
            theme_map[cat] = 'TELEVISION'
        # Opera & Art
        elif any(word in cat_upper for word in ['OPERA', 'ART', 'ARTIST', 'PAINT',
                                                  'SCULPTURE', 'MUSEUM', 'GALLERY']):
            theme_map[cat] = 'ART & OPERA'
        # Food
        elif any(word in cat_upper for word in ['FOOD', 'CUISINE', 'COOK', 'CHEF',
                                                  'RECIPE', 'DISH', 'RESTAURANT']):
            theme_map[cat] = 'FOOD'
        # Transportation
        elif any(word in cat_upper for word in ['TRANSPORT', 'VEHICLE', 'CAR', 'TRAIN',
                                                  'PLANE', 'SHIP', 'AVIATION']):
            theme_map[cat] = 'TRANSPORTATION'
        # Animals
        elif any(word in cat_upper for word in ['ANIMAL', 'MAMMAL', 'BIRD', 'FISH',
                                                  'REPTILE', 'SPECIES', 'WILDLIFE']):
            theme_map[cat] = 'ANIMALS'
        # Languages & Word Origins
        elif any(word in cat_upper for word in ['LANGUAGE', 'WORD ORIGIN', 'ETYMOLOGY',
                                                  'VOCABULARY', 'DIALECT', 'TRANSLATE']):
            theme_map[cat] = 'LANGUAGES & WORD ORIGINS'
        # Bodies of Water
        elif any(word in cat_upper for word in ['OCEAN', 'SEA', 'LAKE', 'RIVER',
                                                  'WATER', 'BAY', 'GULF']):
            theme_map[cat] = 'BODIES OF WATER'
        # Colleges & Universities
        elif any(word in cat_upper for word in ['COLLEGE', 'UNIVERSITY', 'CAMPUS',
                                                  'ACADEMIC', 'IVY LEAGUE']):
            theme_map[cat] = 'COLLEGES & UNIVERSITIES'
        # History (general)
        elif 'HISTORY' in cat_upper:
            theme_map[cat] = 'HISTORY'
        # Geography (general)
        elif 'GEOGRAPHY' in cat_upper:
            theme_map[cat] = 'GEOGRAPHY'
        # Potpourri (catch-all)
        else:
            theme_map[cat] = 'POTPOURRI'
    
    return theme_map

# Add theme column to dataframe
theme_mapping = load_theme_mapping()
df['theme'] = df['category'].map(theme_mapping).fillna('GENERAL KNOWLEDGE')

# Status bar with Jeopardy styling
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.success(f"✅ Loaded {len(df):,} Jeopardy clues!")
with col2:
    if st.session_state.adaptive_mode:
        st.info(f"🎯 Adaptive: ON")
with col3:
    if st.session_state.use_timer:
        st.info(f"⏱️ Timer: {st.session_state.timer_seconds}s")

# Initialize filtered_df as df by default
filtered_df = df

# Check if filtered_df is empty
if filtered_df.empty:
    st.warning("No clues found for the selected categories. Please select different categories.")
    st.stop()

if st.session_state.current_clue is None:
    # Choose clue based on mode
    if st.session_state.adaptive_mode and st.session_state.history:
        # Adaptive mode: prioritize weak categories
        # Calculate category performance
        history_df = pd.DataFrame(st.session_state.history)
        category_performance = history_df.groupby('category')['was_correct'].agg(['mean', 'count'])
        
        # Find focus areas (accuracy < 50%) and strong areas (accuracy >= 80%)
        # Require at least 3 attempts for reliable statistics
        qualified_cats = category_performance[category_performance['count'] >= 3]
        
        weak_cats = qualified_cats[qualified_cats['mean'] < 0.5]
        st.session_state.weak_categories = dict(zip(weak_cats.index, weak_cats['mean'] * 100))
        
        strong_cats = qualified_cats[qualified_cats['mean'] >= 0.8]
        st.session_state.strong_categories = dict(zip(strong_cats.index, strong_cats['mean'] * 100))
        
        if not weak_cats.empty:
            # 70% chance to pick from weak categories
            if random.random() < 0.7:
                weak_category_names = weak_cats.index.tolist()
                weak_clues = filtered_df[filtered_df['category'].isin(weak_category_names)]
                if not weak_clues.empty:
                    st.session_state.current_clue = random.choice(weak_clues.to_dict(orient="records"))
                else:
                    st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
            else:
                st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
        else:
            st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
    else:
        # Normal mode: random selection
        st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
    
    st.session_state.start_time = datetime.datetime.now()

clue = st.session_state.current_clue

# Sidebar settings with theme filter
with st.sidebar:
    st.markdown("<h2 style='color: white;'>🎮 Game Settings</h2>", unsafe_allow_html=True)
    
    # Display question pool info at top (will be updated after filtering)
    pool_col1, pool_col2 = st.columns(2)
    pool_placeholder1 = pool_col1.empty()
    pool_placeholder2 = pool_col2.empty()
    
    pool_placeholder1.metric("Database", f"{len(df):,}", help="Total questions available")
    pool_placeholder2.metric("Filtered", f"{len(df):,}", help="Questions matching filters")
    
    st.markdown("---")
    
    # Settings change notification
    if 'settings_changed' not in st.session_state:
        st.session_state.settings_changed = False
    
    # Round Filter
    with st.expander("🎲 Round Filter", expanded=False):
        # Initialize round filter
        if 'selected_rounds' not in st.session_state:
            st.session_state.selected_rounds = ['Jeopardy', 'Double Jeopardy', 'Final Jeopardy']
        
        # Add round column if it doesn't exist
        if 'round' not in df.columns:
            df['round'] = 'Jeopardy'  # Default if not present
        
        available_rounds = df['round'].unique().tolist()
        selected_rounds = st.multiselect(
            "Select rounds:",
            available_rounds,
            default=st.session_state.selected_rounds if st.session_state.selected_rounds else available_rounds,
            key="round_selector",
            help="Filter by Jeopardy round"
        )
        
        if selected_rounds != st.session_state.selected_rounds:
            st.session_state.selected_rounds = selected_rounds
            st.session_state.settings_changed = True
        
        # Apply round filter
        if selected_rounds:
            filtered_df = df[df['round'].isin(selected_rounds)]
        else:
            filtered_df = df
    
    # Theme Filter (with round-aware filtering)
    with st.expander("🎯 Theme Filter", expanded=False):
        # Get themes from round-filtered data
        available_themes = sorted(filtered_df['theme'].unique())
        
        # Default to all themes
        if 'selected_themes' not in st.session_state:
            st.session_state.selected_themes = available_themes
        
        # Top 30 themes for quick selection
        top_30_themes = ['SCIENCE', 'HISTORY', 'LITERATURE', 'AMERICAN HISTORY', 'POTPOURRI',
                         'SPORTS', 'BUSINESS & INDUSTRY', 'WORLD GEOGRAPHY', 'RELIGION',
                         'LANGUAGES & WORD ORIGINS', 'WORLD HISTORY', 'TRANSPORTATION',
                         'ANIMALS', 'ART & OPERA', 'GEOGRAPHY', 'U.S. GEOGRAPHY',
                         'BODIES OF WATER', 'FOOD', 'MYTHOLOGY', 'TELEVISION',
                         'COLLEGES & UNIVERSITIES']
        
        # Quick select buttons with better layout
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("All", use_container_width=True, key="all_themes", help="Select all available themes"):
                st.session_state.selected_themes = available_themes
                st.session_state.settings_changed = True
                st.rerun()
        with col2:
            # Select top 5 most common themes from available data
            theme_counts_for_selection = filtered_df['theme'].value_counts()
            top_5_themes = theme_counts_for_selection.head(5).index.tolist()
            if st.button("Top 5", use_container_width=True, key="top5_themes", help="Select 5 most common themes"):
                st.session_state.selected_themes = top_5_themes
                st.session_state.settings_changed = True
                st.rerun()
        with col3:
            if st.button("None", use_container_width=True, key="clear_themes", help="Clear all selections"):
                st.session_state.selected_themes = []
                st.session_state.settings_changed = True
                st.rerun()
        
        selected_themes = st.multiselect(
            "Select themes:",
            available_themes,
            default=st.session_state.selected_themes if st.session_state.selected_themes else available_themes,
            key="theme_selector",
            help="Choose themes for your questions"
        )
        
        if selected_themes != st.session_state.selected_themes:
            st.session_state.selected_themes = selected_themes
            st.session_state.settings_changed = True
        
        if selected_themes:
            filtered_df = filtered_df[filtered_df["theme"].isin(selected_themes)]
            theme_counts = filtered_df.groupby('theme').size().sort_values(ascending=False)
            
            # Show selection summary as caption
            st.caption(f"✅ Selected: {len(selected_rounds)} rounds × {len(selected_themes)} themes = {len(filtered_df):,} questions")
            
            # Show top themes in selection
            if len(theme_counts) > 0:
                with st.expander("📊 View theme distribution", expanded=False):
                    for theme, count in theme_counts.head(10).items():
                        st.caption(f"• {theme}: {count:,} questions")
        else:
            filtered_df = df[df['round'].isin(selected_rounds)] if selected_rounds else df
            st.warning("⚠️ No themes selected - using all available questions")
        
        # Show what will happen
        if st.session_state.settings_changed:
            st.caption("🔄 New settings will apply to your next question")
    
    # Update the filtered count display
    pool_placeholder2.metric("Filtered", f"{len(filtered_df):,}", 
                            delta=f"-{len(df) - len(filtered_df):,}" if len(filtered_df) < len(df) else None,
                            help="Questions matching your filters")
    
    # Timer settings in collapsible section
    with st.expander("⏱️ Timer Settings", expanded=False):
        # Check if timer was just enabled
        was_timer_off = not st.session_state.use_timer
        new_timer_state = st.toggle("Timer", value=st.session_state.use_timer, help="Enable countdown timer for questions")
        
        if new_timer_state != st.session_state.use_timer:
            st.session_state.use_timer = new_timer_state
            st.session_state.settings_changed = True
            if new_timer_state:
                st.success("⏱️ Timer enabled for next question")
                st.session_state.start_time = datetime.datetime.now()
            else:
                st.info("Timer disabled for next question")
        
        if st.session_state.use_timer:
            # Use number input with common presets
            col1, col2 = st.columns([2, 1])
            with col1:
                st.session_state.timer_seconds = st.number_input(
                    "Time Limit (seconds):",
                    min_value=3,
                    max_value=60,
                    value=st.session_state.timer_seconds,
                    step=1,
                    help="Enter custom time or use preset"
                )
            with col2:
                st.caption("Quick Set:")
                if st.button("5s", help="Official Jeopardy timing", type="secondary", use_container_width=True):
                    st.session_state.timer_seconds = 5
                    st.rerun()
                if st.button("10s", help="Practice mode timing", type="secondary", use_container_width=True):
                    st.session_state.timer_seconds = 10
                    st.rerun()
                if st.button("15s", help="Learning mode timing", type="secondary", use_container_width=True):
                    st.session_state.timer_seconds = 15
                    st.rerun()
            
            if st.session_state.timer_seconds == 5:
                st.success(f"🏆 Official Jeopardy timing: {st.session_state.timer_seconds} seconds")
            else:
                st.info(f"⏱️ You have {st.session_state.timer_seconds} seconds to answer")
        else:
            st.info("Timer is OFF - Take your time!")
    
    # Adaptive Training Mode in collapsible section
    with st.expander("🎯 Adaptive Training", expanded=False):
        old_adaptive = st.session_state.adaptive_mode
        st.session_state.adaptive_mode = st.toggle(
            "Adaptive Mode", 
            value=st.session_state.adaptive_mode,
            help="Focuses on categories where you have <50% accuracy after 3+ attempts"
        )
        
        if old_adaptive != st.session_state.adaptive_mode:
            st.session_state.settings_changed = True
            if st.session_state.adaptive_mode:
                st.success("🎯 Adaptive mode enabled - will focus on weak areas")
            else:
                st.info("Adaptive mode disabled - random question selection")
    
        # Show requirements
        with st.expander("How It Works", expanded=False):
            st.write("""
            **Requirements:**
            - Answer at least **3 questions** per category
            - Categories with **<50% accuracy** become focus areas
            - When active, **70% chance** to get questions from focus areas
            
            **Currently tracks:**
            - Category-based performance only
            - Future: Question difficulty, response time patterns
            """)
    
    # Performance Insights section
    with st.expander("📊 Performance Insights", expanded=False):
        if st.session_state.history:
            history_df = pd.DataFrame(st.session_state.history)
            category_stats = history_df.groupby('category').agg(
                attempts=('was_correct', 'count'),
                accuracy=('was_correct', 'mean')
            )
            category_stats['accuracy'] *= 100
            
            # Categories with 3+ attempts
            qualified = category_stats[category_stats['attempts'] >= 3]
            
            if not qualified.empty:
                # Focus areas
                focus = qualified[qualified['accuracy'] < 50].sort_values('accuracy')
                if not focus.empty:
                    st.error(f"🎯 Focus Areas ({len(focus)}) - Need practice")
                    for cat in focus.head(5).index:
                        acc = focus.loc[cat, 'accuracy']
                        att = focus.loc[cat, 'attempts']
                        st.caption(f"• {cat}: {acc:.0f}% ({att} attempts)")
                
                # Strong areas
                strong = qualified[qualified['accuracy'] >= 80].sort_values('accuracy', ascending=False)
                if not strong.empty:
                    st.success(f"⭐ Strong Areas ({len(strong)}) - Great job!")
                    for cat in strong.head(5).index:
                        acc = strong.loc[cat, 'accuracy']
                        att = strong.loc[cat, 'attempts']
                        st.caption(f"• {cat}: {acc:.0f}% ({att} attempts)")
                
                # Progress indicator
                total_qualified = len(qualified)
                total_attempted = len(category_stats)
                st.info(f"Progress: {total_qualified}/{total_attempted} categories qualified (3+ attempts)")
                
                if st.session_state.adaptive_mode and st.session_state.weak_categories:
                    st.warning(f"🎯 Adaptive Mode Active - Prioritizing {len(st.session_state.weak_categories)} focus areas")
            else:
                st.info("Answer at least 3 questions per category to see insights")
                if len(category_stats) > 0:
                    st.caption(f"Current: {len(category_stats)} categories attempted")
        else:
            st.info("📊 Start playing to build your performance profile!")

# Get theme for current clue
clue_theme = theme_mapping.get(clue['category'], 'GENERAL KNOWLEDGE')

# Display question in modern modal-like box
st.markdown(f"""
<div class="question-box">
    <div class="category-header">
        <div class="theme-label">{clue_theme}</div>
        <div class="category-label">{clue['category'].upper()}</div>
    </div>
    <div class="clue-box">
        <div class="clue-text">{clue['clue']}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Display adaptive mode indicator if applicable
if st.session_state.adaptive_mode and clue['category'] in st.session_state.weak_categories:
    accuracy = st.session_state.weak_categories[clue['category']]
    # Get attempt count for this category
    if st.session_state.history:
        history_df = pd.DataFrame(st.session_state.history)
        attempts = len(history_df[history_df['category'] == clue['category']])
    else:
        attempts = 0
    st.markdown(f"""
    <div class="focus-area-warning">
        🎯 <strong>Focus Area</strong> - Your stats: {accuracy:.0f}% accuracy over {attempts} attempts
    </div>
    """, unsafe_allow_html=True)

# Timer display - create container first
timer_container = st.container()

# Calculate if time is up BEFORE creating form
time_is_up = False
if st.session_state.use_timer:
    elapsed_time = (datetime.datetime.now() - st.session_state.start_time).total_seconds()
    remaining = max(0, st.session_state.timer_seconds - int(elapsed_time))
    time_is_up = remaining <= 0

# Form with conditional input field
with st.form(key="clue_form", clear_on_submit=True):
    if time_is_up and st.session_state.use_timer:
        # Time's up - disable input field
        st.text_input(
            "Your response:", 
            value="TIME'S UP! Press Buzz to see the answer.",
            disabled=True,
            key="user_response_disabled"
        )
        user_input = ""  # Empty input when time's up
    else:
        # Normal input field
        user_input = st.text_input("Your response:", key="user_response")
    
    submitted = st.form_submit_button("🔔 Buzz!")

# Now display timer above the form using the container
if st.session_state.use_timer:
    with timer_container:
        # Timer already calculated above
        if remaining > 0:
            progress = remaining / st.session_state.timer_seconds
            if remaining > 3:
                st.progress(progress, text=f"⏱️ Time remaining: {remaining} seconds")
            else:
                # Last 3 seconds warning
                st.warning(f"⏱️ Time remaining: {remaining} seconds - HURRY!")
            
            # Auto-refresh for countdown
            time.sleep(1)
            st.rerun()
        else:
            st.error("⏰ Time's up! Press Buzz to reveal the answer.")

if submitted:
    elapsed_time = (datetime.datetime.now() - st.session_state.start_time).seconds
    user_clean = normalize(user_input)
    answer_clean = normalize(clue["correct_response"])
    
    # Check if correct with fuzzy matching
    def fuzzy_match(user_ans, correct_ans, threshold=0.85):
        """Check if answers match with some flexibility"""
        # Exact match after normalization
        if user_ans == correct_ans:
            return True
        
        # Handle common variations
        # Remove articles
        user_no_article = re.sub(r'^(the|a|an)\s+', '', user_ans)
        correct_no_article = re.sub(r'^(the|a|an)\s+', '', correct_ans)
        if user_no_article == correct_no_article:
            return True
        
        # Check if user answer is contained in correct answer or vice versa
        if len(user_ans) > 3 and (user_ans in correct_ans or correct_ans in user_ans):
            return True
        
        # Calculate similarity score using difflib
        import difflib
        similarity = difflib.SequenceMatcher(None, user_ans, correct_ans).ratio()
        return similarity >= threshold
    
    # Check if correct and within time limit (if timer is on)
    if st.session_state.use_timer:
        timed_out = elapsed_time > st.session_state.timer_seconds
        if timed_out:
            correct = False  # Can't be correct if time ran out
        else:
            correct = fuzzy_match(user_clean, answer_clean)
    else:
        correct = fuzzy_match(user_clean, answer_clean)
        timed_out = False

    if correct:
        st.success("✅ Correct!")
        st.session_state.score += 1
        st.session_state.current_streak += 1
        if st.session_state.current_streak > st.session_state.best_streak:
            st.session_state.best_streak = st.session_state.current_streak
    elif timed_out:
        st.error(f"⏰ Time expired! The correct response was: **{clue['correct_response']}**")
        st.session_state.current_streak = 0
    else:
        st.error(f"❌ Incorrect. The correct response was: **{clue['correct_response']}**")
        st.session_state.current_streak = 0

        # Semantic similarity - disabled for deployment (embeddings too slow)
        # if "clue_embedding" in filtered_df.columns:
        #     user_vector = model.encode(clue["clue"])
        #     clue_vectors = np.vstack(filtered_df["clue_embedding"].values)
        #     similarities = cosine_similarity([user_vector], clue_vectors)[0]
        #     top_indices = similarities.argsort()[-4:][::-1]
        #     similar_clues = filtered_df.iloc[top_indices]
        #
        #     with st.expander("🔍 Review similar clues"):
        #         for _, row in similar_clues.iterrows():
        #             st.markdown(f"- **{row['category']}**: {row['clue']}")
        #             st.markdown(f"  → *{row['correct_response']}*")

    st.session_state.total += 1
    st.session_state.history.append({
        "game_id": clue.get("game_id", ""),
        "category": clue["category"],
        "clue": clue["clue"],
        "correct_response": clue["correct_response"],
        "round": clue.get("round", ""),
        "user_response": user_input,
        "was_correct": correct
    })

    # Update in-memory progress tracking
    today = datetime.date.today().isoformat()
    st.session_state.progress_data.append({
        "date": today,
        "total": 1,
        "correct": 1 if correct else 0
    })

    # Auto-save progress (if auth available)
    if AUTH_AVAILABLE and auth:
        auth.save_user_session()
    
    st.session_state.current_clue = None
    st.rerun()

if st.session_state.total:
    st.markdown("<hr style='border: 1px solid #060CE9; margin-top: 20px;'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Correct", st.session_state.score)
    with col2:
        st.metric("❌ Incorrect", st.session_state.total - st.session_state.score)
    with col3:
        accuracy = (st.session_state.score / st.session_state.total * 100) if st.session_state.total > 0 else 0
        st.metric("📊 Accuracy", f"{accuracy:.1f}%")

if st.session_state.history:
    st.markdown("---")
    st.subheader("📝 Recent Answers")
    st.caption("Showing last 5 responses - see full history below for complete session")
    
    # Show last 5 answers in a clean format
    for i, h in enumerate(reversed(st.session_state.history[-5:]), 1):
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                if h["was_correct"]:
                    st.success(f"✅ **{h['category']}**")
                else:
                    st.error(f"❌ **{h['category']}**")
                
                st.write(f"*{h['clue'][:100]}...*" if len(h['clue']) > 100 else f"*{h['clue']}*")
                st.write(f"Your answer: {h['user_response']}")
                if not h["was_correct"]:
                    st.write(f"Correct answer: **{h['correct_response']}**")
            with col2:
                if h["was_correct"]:
                    st.write("✅ Correct")
                else:
                    st.write("❌ Incorrect")
    
    # Full history in expander with filtering
    with st.expander("📊 View Full Session History"):
        history_df = pd.DataFrame(st.session_state.history)
        history_df["Result"] = history_df["was_correct"].map({True: "✅ Correct", False: "❌ Incorrect"})
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            result_filter = st.selectbox(
                "Filter by result:",
                ["All", "✅ Correct", "❌ Incorrect"],
                key="result_filter"
            )
        with col2:
            categories_in_history = ["All"] + sorted(history_df["category"].unique())
            category_filter = st.selectbox(
                "Filter by category:",
                categories_in_history,
                key="category_filter"
            )
        with col3:
            st.metric("Total Questions", len(history_df))
        
        # Apply filters
        display_df = history_df.copy()
        if result_filter != "All":
            display_df = display_df[display_df["Result"] == result_filter]
        if category_filter != "All":
            display_df = display_df[display_df["category"] == category_filter]
        
        # Show filtered dataframe
        if not display_df.empty:
            st.dataframe(
                display_df[["Result", "category", "clue", "user_response", "correct_response"]],
                use_container_width=True,
                height=400  # Fixed height to avoid excessive scrolling
            )
            st.caption(f"Showing {len(display_df)} of {len(history_df)} total questions")
        else:
            st.info("No questions match the selected filters")
    
    # Session History
    with st.expander("📅 View All Sessions History"):
        try:
            # Load all saved sessions
            import json
            from pathlib import Path
            if AUTH_AVAILABLE and auth:
                user_id = auth.get_user_id(st.session_state.user_email)
            else:
                user_id = "default_user"
            session_file = Path(f"user_data/{user_id}_session.json")
            
            if session_file.exists():
                with open(session_file, 'r') as f:
                    saved_data = json.load(f)
                
                st.write("**Lifetime Statistics:**")
                all_history = saved_data.get('history', [])
                if all_history:
                    total_all_time = len(all_history)
                    correct_all_time = sum(1 for h in all_history if h.get('was_correct'))
                    accuracy_all_time = (correct_all_time / total_all_time * 100) if total_all_time > 0 else 0
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Questions", f"{total_all_time:,}")
                    with col2:
                        st.metric("Lifetime Correct", f"{correct_all_time:,}")
                    with col3:
                        st.metric("Overall Accuracy", f"{accuracy_all_time:.1f}%")
                    
                    # Category breakdown
                    st.write("**Performance by Category (All-Time):**")
                    import pandas as pd
                    history_df = pd.DataFrame(all_history)
                    category_stats = history_df.groupby('category').agg(
                        attempts=('was_correct', 'count'),
                        correct=('was_correct', 'sum')
                    )
                    category_stats['accuracy'] = (category_stats['correct'] / category_stats['attempts'] * 100).round(1)
                    category_stats = category_stats.sort_values('attempts', ascending=False)
                    
                    # Show top categories
                    st.dataframe(
                        category_stats.head(20),
                        use_container_width=True,
                        height=300
                    )
                    
                    # Last login
                    last_login = saved_data.get('last_login', 'Unknown')
                    st.caption(f"Last saved: {last_login}")
                    
                    # Clear history button with confirmation
                    st.markdown("---")
                    with st.form("clear_history_form"):
                        st.warning("⚠️ Danger Zone")
                        st.write("This will permanently delete all your historical data.")
                        confirm = st.checkbox("I understand this action cannot be undone")
                        if st.form_submit_button("🗑️ Clear All History", type="secondary", disabled=not confirm):
                            st.session_state.history = []
                            st.session_state.score = 0
                            st.session_state.total = 0
                            st.session_state.weak_categories = {}
                            st.session_state.strong_categories = {}
                            if AUTH_AVAILABLE and auth:
                                auth.save_user_session()
                            st.success("All history cleared!")
                            st.rerun()
                else:
                    st.info("No historical data yet. Keep playing to build your history!")
            else:
                st.info("No saved sessions found. Your progress saves automatically as you play!")
        except Exception as e:
            st.error(f"Could not load session history: {e}")
    
    # Progress summary
    st.markdown("---")
    st.subheader("📈 Current Session Summary")
    col1, col2 = st.columns(2)
    
    with col1:
        # Category performance - only show categories with 3+ attempts
        category_stats = pd.DataFrame(st.session_state.history).groupby("category")["was_correct"].agg(["sum", "count"])
        category_stats["accuracy"] = (category_stats["sum"] / category_stats["count"] * 100).round(1)
        
        # Filter for categories with 3+ attempts and 80%+ accuracy
        best_categories = category_stats[(category_stats["count"] >= 3) & (category_stats["accuracy"] >= 80)]
        best_categories = best_categories.sort_values("accuracy", ascending=False)
        
        if not best_categories.empty:
            st.write("**Best Categories:**")
            for cat, row in best_categories.head(3).iterrows():
                st.write(f"• {cat}: {row['accuracy']}% ({int(row['sum'])}/{int(row['count'])})")
        else:
            st.write("**Best Categories:**")
            st.write("*Need 3+ attempts with 80%+ accuracy*")
    
    with col2:
        st.write("**Session Stats:**")
        st.write(f"• Total Questions: {st.session_state.total}")
        st.write(f"• Correct: {st.session_state.score}")
        st.write(f"• Accuracy: {accuracy:.1f}%")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Practice Missed", use_container_width=True, type="secondary", help="Review questions you got wrong"):
            missed = [h for h in st.session_state.history if not h["was_correct"]]
            if missed:
                # Select a random missed question and use it directly
                retry_question = random.choice(missed)
                # Create a clue dict from the missed question
                st.session_state.current_clue = {
                    'category': retry_question['category'],
                    'clue': retry_question['clue'],
                    'correct_response': retry_question['correct_response'],
                    'round': retry_question.get('round', 'Jeopardy'),
                    'game_id': retry_question.get('game_id', '')
                }
                # Add embedding if model is available
                if 'clue_embedding' in df.columns and not df.empty:
                    # Try to find matching clue in dataframe for embedding
                    matching = df[df['clue'] == retry_question['clue']]
                    if not matching.empty:
                        st.session_state.current_clue['clue_embedding'] = matching.iloc[0]['clue_embedding']
                    else:
                        st.session_state.current_clue['clue_embedding'] = model.encode(retry_question['clue'])
                
                st.session_state.start_time = datetime.datetime.now()
                st.rerun()
            else:
                st.success("Great job! No missed questions to practice!")
    
    with col2:
        if st.button("New Question", use_container_width=True, type="primary", help="Get a new random question"):
            st.session_state.current_clue = None
            st.rerun()
