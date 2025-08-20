import streamlit as st
import pandas as pd
import random
import re
import os
import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import defaultdict
from typing import Dict, List

# Import the R2 data loader
from r2_jeopardy_data_loader import load_jeopardy_data_from_r2

# Page configuration with custom icon
st.set_page_config(
    page_title="Jaypardy!",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 0rem 1rem;
    }
    
    /* Custom header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        text-align: center;
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        text-align: center;
        margin-top: 0.5rem;
        font-size: 1.1rem;
    }
    
    /* Theme card */
    .theme-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
        font-weight: bold;
        font-size: 1.2rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Clue card */
    .clue-card {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .clue-text {
        font-size: 1.3rem;
        color: #2c3e50;
        line-height: 1.6;
    }
    
    /* Score display */
    .score-container {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .score-label {
        font-size: 1rem;
        opacity: 0.9;
        margin-bottom: 0.5rem;
    }
    
    .score-value {
        font-size: 2.5rem;
        font-weight: bold;
    }
    
    /* Timer styling */
    .timer-container {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 1rem;
    }
    
    /* Success and error messages */
    .stSuccess {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid;
    }
    
    .stError {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        font-weight: bold;
        border-radius: 8px;
        transition: transform 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Progress bar */
    .progress-bar {
        background: #e9ecef;
        height: 30px;
        border-radius: 15px;
        overflow: hidden;
        margin: 1rem 0;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        transition: width 0.3s ease;
    }
    
    /* Stats cards */
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    
    .stat-label {
        color: #6c757d;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    /* Theme selector cards */
    .theme-selector-card {
        background: white;
        border: 2px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        transition: all 0.2s;
    }
    
    .theme-selector-card:hover {
        border-color: #667eea;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
    }
    
    .theme-count {
        color: #6c757d;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

class JeopardyCategoryAnalyzer:
    """Analyze and categorize Jeopardy categories into themes"""
    
    def __init__(self):
        # Define theme keywords and patterns
        self.theme_patterns = {
            "HISTORY": {
                "keywords": ["history", "historical", "ancient", "medieval", "war", "battle", 
                            "empire", "dynasty", "revolution", "civil war", "world war", 
                            "century", "era", "period", "ages", "civilization", "historic",
                            "past", "founding", "colonial", "conquest", "president", "king", 
                            "queen", "royal", "monarch"],
                "patterns": [r"\b\d{4}\b", r"\b\d{1,2}th century\b", r"\bwar\b", r"the \d{2,4}s"]
            },
            
            "GEOGRAPHY": {
                "keywords": ["geography", "countries", "cities", "states", "capitals", 
                            "nations", "world", "islands", "mountains", "rivers", "lakes",
                            "oceans", "continents", "maps", "places", "landmarks", "wonders",
                            "national parks", "territories", "regions", "hemispheres", "travel"],
                "patterns": [r"countries", r"u\.s\. states", r"capitals", r"cities of"]
            },
            
            "SCIENCE": {
                "keywords": ["science", "biology", "chemistry", "physics", "anatomy", 
                            "medicine", "astronomy", "geology", "meteorology", "elements",
                            "atoms", "molecules", "space", "planets", "stars", "medical",
                            "body", "human", "animals", "nature", "environment", "ecology",
                            "evolution", "genetics", "dna", "cells", "periodic table", "math",
                            "mathematics", "computer", "technology"],
                "patterns": [r"scientific", r"the body", r"in space"]
            },
            
            "LITERATURE": {
                "keywords": ["literature", "books", "novels", "authors", "writers", "poets",
                            "poetry", "poems", "shakespeare", "classics", "fiction", 
                            "characters", "novels", "stories", "tales", "fables", "plays",
                            "playwright", "literary", "reading", "bibliography", "novel"],
                "patterns": [r"shakespeare", r"authors?", r"literat", r"book"]
            },
            
            "ENTERTAINMENT": {
                "keywords": ["movies", "films", "cinema", "hollywood", "actors", "actresses",
                            "oscars", "academy awards", "directors", "television", "tv",
                            "shows", "series", "sitcom", "drama", "comedy", "entertainment",
                            "celebrities", "stars", "emmys", "tonys", "grammys", "awards",
                            "music", "songs", "singers", "bands", "albums", "composers"],
                "patterns": [r"at the movies", r"on tv", r"oscar", r"film", r"music"]
            },
            
            "SPORTS": {
                "keywords": ["sports", "football", "baseball", "basketball", "hockey",
                            "soccer", "tennis", "golf", "olympics", "athletes", "teams",
                            "championship", "tournament", "league", "nfl", "nba", "mlb",
                            "nhl", "fifa", "espn", "stadium", "arena", "game", "match",
                            "player", "coach", "referee", "score", "bowl", "cup"],
                "patterns": [r"sports", r"olympi", r"super bowl", r"world cup"]
            },
            
            "BUSINESS": {
                "keywords": ["business", "company", "corporation", "brand", "ceo", "economy",
                            "money", "dollar", "bank", "finance", "stock", "market", "trade",
                            "industry", "commerce", "entrepreneur", "startup", "investment",
                            "wall street", "nasdaq", "fortune"],
                "patterns": [r"business", r"compan", r"corporate", r"\$\d+", r"money"]
            },
            
            "FOOD & DRINK": {
                "keywords": ["food", "cuisine", "cooking", "chef", "recipe", "restaurant",
                            "meal", "dish", "ingredient", "flavor", "taste", "drink",
                            "beverage", "wine", "beer", "cocktail", "coffee", "tea",
                            "fruit", "vegetable", "meat", "dessert", "kitchen"],
                "patterns": [r"food", r"cook", r"eat", r"drink", r"cuisine"]
            },
            
            "WORDPLAY": {
                "keywords": ["rhyme", "rhyming", "pun", "anagram", "palindrome", "crossword",
                            "puzzle", "riddle", "wordplay", "scramble", "spell", "letter",
                            "before & after", "before and after", "quotation", "phrase"],
                "patterns": [r"rhym", r"pun", r"anagram", r"wordplay", r"before.*after"]
            },
            
            "POP CULTURE": {
                "keywords": ["pop culture", "celebrity", "famous", "trend", "fashion", "style",
                            "social media", "internet", "meme", "viral", "modern", "contemporary",
                            "current", "today", "recent", "millennial", "gen z", "popular"],
                "patterns": [r"pop cultur", r"celebrit", r"fashion", r"modern"]
            },
            
            "RELIGION & MYTHOLOGY": {
                "keywords": ["religion", "religious", "god", "goddess", "bible", "church",
                            "faith", "mythology", "myth", "legend", "zeus", "greek god",
                            "roman god", "norse", "saint", "prophet", "temple", "sacred",
                            "holy", "worship", "prayer", "spiritual"],
                "patterns": [r"relig", r"god", r"myth", r"bible", r"saint"]
            },
            
            "GENERAL KNOWLEDGE": {
                "keywords": ["potpourri", "hodgepodge", "mixed", "general", "trivia",
                            "miscellaneous", "variety", "assorted"],
                "patterns": [r"potpourri", r"hodgepodge", r"mixed bag"]
            }
        }
    
    def categorize_single(self, category: str) -> str:
        """Categorize a single category string into a theme"""
        if not category:
            return "GENERAL KNOWLEDGE"
        
        category_lower = str(category).lower()
        theme_scores = {}
        
        # Score each theme based on keyword matches
        for theme, criteria in self.theme_patterns.items():
            score = 0
            
            # Check keywords
            for keyword in criteria["keywords"]:
                if keyword in category_lower:
                    score += len(keyword)  # Longer matches score higher
            
            # Check patterns
            for pattern in criteria["patterns"]:
                if re.search(pattern, category_lower):
                    score += 10
            
            if score > 0:
                theme_scores[theme] = score
        
        # Return the theme with highest score, or GENERAL KNOWLEDGE if no match
        if theme_scores:
            return max(theme_scores.items(), key=lambda x: x[1])[0]
        else:
            return "GENERAL KNOWLEDGE"
    
    def group_categories_by_theme(self, categories: List[str]) -> Dict[str, List[str]]:
        """Group all categories into themes"""
        theme_groups = defaultdict(list)
        
        for category in categories:
            theme = self.categorize_single(category)
            theme_groups[theme].append(category)
        
        # Sort themes by number of categories (most popular first)
        sorted_themes = dict(sorted(theme_groups.items(), 
                                  key=lambda x: len(x[1]), 
                                  reverse=True))
        
        return sorted_themes

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
        
        # Compute embeddings (can be expensive, so we'll do it on demand)
        with st.spinner("🧮 Computing clue embeddings..."):
            # Process in batches to avoid memory issues
            batch_size = min(1000, len(df))
            sample_df = df.sample(n=batch_size) if len(df) > batch_size else df
            sample_df["clue_embedding"] = sample_df["clue"].apply(lambda x: model.encode(x))
            return sample_df
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Initialize session state
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

# Header
st.markdown("""
<div class="main-header">
    <h1>🎯 Jaypardy!</h1>
    <p>Master the art of trivia with real Jeopardy questions!</p>
</div>
""", unsafe_allow_html=True)

# Loading data
with st.spinner("🎯 Loading Jeopardy dataset..."):
    df = load_data()

if df.empty:
    st.error("❌ Failed to load Jeopardy dataset.")
    st.info("Check your internet connection or contact the administrator.")
    st.stop()

# Success message with animation
success_placeholder = st.empty()
success_placeholder.success(f"✅ Successfully loaded {len(df):,} Jeopardy clues!")

# Create two columns for main layout
col1, col2 = st.columns([2, 1])

with col1:
    # Theme selection with improved UI
    st.markdown("### 🎯 Select Themes")
    
    # Initialize analyzer and group categories
    analyzer = JeopardyCategoryAnalyzer()
    all_categories = df["category"].unique()
    theme_groups = analyzer.group_categories_by_theme(all_categories)
    
    # Calculate theme statistics
    theme_stats = {}
    for theme, categories in theme_groups.items():
        theme_df = df[df["category"].isin(categories)]
        theme_stats[theme] = {
            'categories': len(categories),
            'clues': len(theme_df)
        }
    
    # Create theme options
    theme_options = []
    for theme, stats in theme_stats.items():
        if stats['clues'] >= 10:  # Only show themes with enough clues
            theme_options.append(f"{theme} ({stats['clues']:,} clues)")
    
    # Quick select buttons
    col_quick1, col_quick2, col_quick3 = st.columns(3)
    with col_quick1:
        if st.button("📖 All Themes"):
            selected_theme_displays = theme_options
    with col_quick2:
        if st.button("🎲 Random Mix"):
            selected_theme_displays = random.sample(theme_options, min(5, len(theme_options)))
    with col_quick3:
        if st.button("🔄 Clear All"):
            selected_theme_displays = []
    
    selected_theme_displays = st.multiselect(
        "Choose themes to practice:",
        theme_options,
        default=theme_options[:3] if len(theme_options) >= 3 else theme_options,
        help="Each theme contains related Jeopardy categories"
    )
    
    if not selected_theme_displays:
        st.warning("⚠️ Please select at least one theme to continue.")
        st.stop()
    
    # Convert selected themes to categories
    selected_categories = []
    for theme_display in selected_theme_displays:
        theme_name = theme_display.split(" (")[0]
        if theme_name in theme_groups:
            selected_categories.extend(theme_groups[theme_name])
    
    filtered_df = df[df["category"].isin(selected_categories)]

    if filtered_df.empty:
        st.warning("No clues found for the selected themes. Please select different themes.")
        st.stop()
    
    # Show selection info
    st.info(f"📊 Selected {len(selected_theme_displays)} themes • {len(set(selected_categories)):,} categories • {len(filtered_df):,} total clues")

    # Game Settings
    st.markdown("### ⚙️ Game Settings")
    
    col_set1, col_set2 = st.columns(2)
    
    with col_set1:
        # Time limit slider
        time_limit = st.slider(
            "⏱️ Time Limit (seconds):",
            10, 60, 30,
            help="Set how long you have to answer each question"
        )
        
        # Difficulty filter
        if 'round' in df.columns:
            rounds = ['All'] + sorted(df['round'].dropna().unique().tolist())
            selected_round = st.selectbox(
                "📈 Difficulty Level:",
                rounds,
                help="Filter by Jeopardy round for difficulty"
            )
            if selected_round != 'All':
                filtered_df = filtered_df[filtered_df['round'] == selected_round]
    
    with col_set2:
        # Study Mode toggle
        study_mode = st.checkbox(
            "📚 Study Mode",
            value=st.session_state.study_mode,
            help="No timer, see answers immediately"
        )
        st.session_state.study_mode = study_mode
        
        # Speed Round toggle
        speed_round = st.checkbox(
            "⚡ Speed Round",
            help="5-second timer, 2x points for correct answers"
        )
        if speed_round:
            time_limit = 5

with col2:
    # Stats dashboard
    st.markdown("### 📊 Your Stats")
    
    # Score card
    st.markdown(f"""
    <div class="score-container">
        <div class="score-label">Current Score</div>
        <div class="score-value">{st.session_state.score} / {st.session_state.total}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Progress bar
    if st.session_state.total > 0:
        accuracy = (st.session_state.score / st.session_state.total) * 100
        st.markdown(f"""
        <div class="progress-bar">
            <div class="progress-fill" style="width: {accuracy}%">
                {accuracy:.1f}% Accuracy
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Streak counter
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{st.session_state.streak}</div>
            <div class="stat-label">Current Streak</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_stat2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{st.session_state.best_streak}</div>
            <div class="stat-label">Best Streak</div>
        </div>
        """, unsafe_allow_html=True)

# Clear success message after display
success_placeholder.empty()

# Main game area
st.markdown("---")

if st.session_state.current_clue is None:
    st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
    st.session_state.start_time = datetime.datetime.now()

clue = st.session_state.current_clue

# Check for Daily Double (random 5% chance, once per session)
is_daily_double = False
if not st.session_state.daily_double_used and random.random() < 0.05:
    is_daily_double = True
    st.session_state.daily_double_used = True

# Display current clue with enhanced styling
if is_daily_double:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); 
                color: #1a1a1a; padding: 2rem; border-radius: 15px; 
                text-align: center; margin-bottom: 1rem; 
                box-shadow: 0 6px 12px rgba(255, 215, 0, 0.3);">
        <h2 style="margin: 0; font-size: 2rem;">⭐ DAILY DOUBLE! ⭐</h2>
        <p style="margin-top: 0.5rem;">Double points for this question!</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<div class="theme-card">
    {clue['category']}
</div>
""", unsafe_allow_html=True)

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
            "📝 Add a note for this question:",
            value=existing_note,
            placeholder="Add memory tricks, related facts, etc.",
            key=f"note_{note_key}"
        )
        if new_note != existing_note:
            st.session_state.notes[note_key] = new_note

# Answer form
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
        submitted = st.form_submit_button(
            "🎯 Submit Answer" if not st.session_state.study_mode else "⏭️ Next Question", 
            use_container_width=True
        )
    with col_bookmark:
        bookmark_btn = st.form_submit_button("🔖", use_container_width=True, help="Bookmark this question")

if bookmark_btn:
    bookmark_entry = {
        "category": clue["category"],
        "clue": clue["clue"],
        "correct_response": clue["correct_response"],
        "bookmarked_at": datetime.datetime.now().isoformat()
    }
    if bookmark_entry not in st.session_state.bookmarks:
        st.session_state.bookmarks.append(bookmark_entry)
        st.success("🔖 Question bookmarked!")

if submitted:
    if st.session_state.study_mode:
        # In study mode, just move to next question
        st.session_state.current_clue = None
        st.rerun()
    else:
        elapsed_time = (datetime.datetime.now() - st.session_state.start_time).seconds
        user_clean = normalize(user_input)
        answer_clean = normalize(clue["correct_response"])
        
        # Check if it's speed round
        points_multiplier = 1
        if speed_round and elapsed_time <= 5:
            points_multiplier = 2
        elif is_daily_double:
            points_multiplier = 2
            
        correct = user_clean == answer_clean and elapsed_time <= time_limit

        if correct:
            st.balloons()
            points_earned = 1 * points_multiplier
            st.success(f"🎉 **Correct!** {'⚡ Speed Bonus!' if speed_round and elapsed_time <= 5 else ''} {'⭐ Daily Double!' if is_daily_double else ''} +{points_earned} points")
            st.session_state.score += points_earned
            st.session_state.streak += 1
            st.session_state.best_streak = max(st.session_state.streak, st.session_state.best_streak)
            
            # Check for achievements
            if st.session_state.streak == 5 and "5_streak" not in st.session_state.achievements:
                st.session_state.achievements.append("5_streak")
                st.success("🏆 Achievement Unlocked: 5 Question Streak!")
            elif st.session_state.streak == 10 and "10_streak" not in st.session_state.achievements:
                st.session_state.achievements.append("10_streak")
                st.success("🏆 Achievement Unlocked: 10 Question Streak Master!")
        else:
            st.error(f"❌ **Incorrect** {'(Time\'s up!)' if elapsed_time > time_limit else ''}")
            st.info(f"The correct response was: **{clue['correct_response']}**")
            st.session_state.streak = 0
            points_earned = 0
            
            # Track weak themes
            theme = clue["category"]
            if theme not in st.session_state.weak_themes:
                st.session_state.weak_themes[theme] = {"incorrect": 0, "total": 0}
            st.session_state.weak_themes[theme]["incorrect"] += 1

        # Semantic similarity with better display
        if "clue_embedding" in filtered_df.columns:
            user_vector = model.encode(clue["clue"])
            clue_vectors = np.vstack(filtered_df["clue_embedding"].values)
            similarities = cosine_similarity([user_vector], clue_vectors)[0]
            top_indices = similarities.argsort()[-4:][::-1]
            similar_clues = filtered_df.iloc[top_indices]

            with st.expander("🔍 Review similar clues to improve"):
                for idx, (_, row) in enumerate(similar_clues.iterrows(), 1):
                    st.markdown(f"""
                    **{idx}. {row['category']}**  
                    📝 {row['clue']}  
                    ✅ *{row['correct_response']}*
                    """)

        # Update weak themes tracking
        theme = clue["category"]
        if theme not in st.session_state.weak_themes:
            st.session_state.weak_themes[theme] = {"incorrect": 0, "total": 0}
        st.session_state.weak_themes[theme]["total"] += 1

        st.session_state.total += 1
        st.session_state.history.append({
            "game_id": clue.get("game_id", ""),
            "category": clue["category"],
            "clue": clue["clue"],
            "correct_response": clue["correct_response"],
            "round": clue.get("round", ""),
            "user_response": user_input,
            "was_correct": correct,
            "time_taken": elapsed_time if not st.session_state.study_mode else 0,
            "points_earned": points_earned if not st.session_state.study_mode else 0
        })

        # Update progress tracking
        today = datetime.date.today().isoformat()
        st.session_state.progress_data.append({
            "date": today,
            "total": 1,
            "correct": 1 if correct else 0
        })

        st.session_state.current_clue = None
        st.rerun()

# Session history and tools
if st.session_state.history:
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📊 Session Recap", "📈 Progress Tracker", "🎮 Game Tools"])
    
    with tab1:
        history_df = pd.DataFrame(st.session_state.history)
        
        # Summary metrics
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Total Questions", len(history_df))
        with col_m2:
            st.metric("Correct Answers", len(history_df[history_df["was_correct"]]))
        with col_m3:
            avg_time = history_df["time_taken"].mean()
            st.metric("Avg. Time", f"{avg_time:.1f}s")
        with col_m4:
            acc = (len(history_df[history_df["was_correct"]]) / len(history_df)) * 100
            st.metric("Accuracy", f"{acc:.1f}%")
        
        # Detailed history
        st.dataframe(
            history_df[["category", "clue", "user_response", "correct_response", "was_correct", "time_taken"]],
            use_container_width=True
        )
    
    with tab2:
        if st.session_state.progress_data:
            progress_df = pd.DataFrame(st.session_state.progress_data)
            summary = progress_df.groupby("date").sum().reset_index()
            summary["accuracy"] = (summary["correct"] / summary["total"] * 100).round(1)
            
            # Display progress chart
            st.line_chart(summary.set_index("date")["accuracy"])
            st.dataframe(summary, use_container_width=True)
        else:
            st.info("No progress data available yet. Keep playing!")
    
    with tab3:
        col_tool1, col_tool2 = st.columns(2)
        
        with col_tool1:
            if st.button("🔁 Adaptive Retry Mode", use_container_width=True):
                missed = [h for h in st.session_state.history if not h["was_correct"]]
                if missed:
                    retry = random.choice(missed)
                    st.session_state.current_clue = retry
                    st.rerun()
                else:
                    st.info("No missed clues to retry yet!")
        
        with col_tool2:
            if st.button("🎯 New Random Question", use_container_width=True):
                st.session_state.current_clue = None
                st.rerun()
        
        # Theme performance
        st.markdown("### 📊 Performance by Category")
        history_df = pd.DataFrame(st.session_state.history)
        theme_stats = history_df.groupby("category").agg({
            "was_correct": ["sum", "count"]
        }).round(2)
        theme_stats.columns = ["Correct", "Total"]
        theme_stats["Accuracy %"] = (theme_stats["Correct"] / theme_stats["Total"] * 100).round(1)
        st.dataframe(theme_stats, use_container_width=True)