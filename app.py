import streamlit as st
import pandas as pd
import random
import re
import os
import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import Dict, List, Optional
import time

# Import the R2 data loader
from r2_jeopardy_data_loader import load_jeopardy_data_from_r2

# Page configuration
st.set_page_config(
    page_title="Jay's Jeopardy Trainer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 1rem;
    }
    
    /* Score display styling */
    .score-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    /* Category badge styling */
    .category-badge {
        background-color: #4c51bf;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.5rem 0;
        font-weight: bold;
    }
    
    /* Clue card styling */
    .clue-card {
        background: linear-gradient(to right, #f7f7f7 0%, #ffffff 100%);
        border: 2px solid #e2e8f0;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Timer styling */
    .timer-display {
        font-size: 2rem;
        font-weight: bold;
        color: #ef4444;
        text-align: center;
        padding: 1rem;
    }
    
    /* Streak indicator */
    .streak-indicator {
        background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 10px;
        font-weight: bold;
        display: inline-block;
        margin: 0.5rem;
    }
    
    /* Success animation */
    @keyframes successPulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .success-animation {
        animation: successPulse 0.5s ease-in-out;
    }
</style>
""", unsafe_allow_html=True)

# Constants
DIFFICULTY_SETTINGS = {
    "Easy": {"time_multiplier": 1.5, "hint_enabled": True},
    "Medium": {"time_multiplier": 1.0, "hint_enabled": False},
    "Hard": {"time_multiplier": 0.7, "hint_enabled": False},
    "Expert": {"time_multiplier": 0.5, "hint_enabled": False}
}

# Load model once
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

# Enhanced text normalization with multiple strategies
def normalize(text: str) -> str:
    """Normalize text for fuzzy matching with improved handling"""
    text = text.lower().strip()
    # Remove common question starters
    text = re.sub(r"^(what|who|where|when|why|how)\s+(is|are|was|were|does|do|did)\s+", "", text)
    # Remove articles
    text = re.sub(r"\b(the|a|an)\b", "", text)
    # Remove punctuation but keep numbers
    text = re.sub(r"[^\w\s]", "", text)
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def calculate_similarity(user_answer: str, correct_answer: str) -> float:
    """Calculate similarity between user answer and correct answer"""
    user_norm = normalize(user_answer)
    correct_norm = normalize(correct_answer)
    
    # Exact match after normalization
    if user_norm == correct_norm:
        return 1.0
    
    # Check if user answer contains the key parts of correct answer
    if len(correct_norm) > 3 and correct_norm in user_norm:
        return 0.9
    
    # Check word overlap
    user_words = set(user_norm.split())
    correct_words = set(correct_norm.split())
    if correct_words and user_words:
        overlap = len(user_words & correct_words) / len(correct_words)
        if overlap > 0.7:
            return overlap
    
    return 0.0

# Load and filter data with better error handling
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data():
    """Load Jeopardy data with proper error handling and caching"""
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        return pd.DataFrame({
            'category': ['HISTORY', 'SCIENCE', 'MOVIES'],
            'clue': ['First president of the US', 'Element with symbol H', 'This film won Best Picture in 2020'],
            'correct_response': ['George Washington', 'Hydrogen', 'Parasite'],
            'round': ['Jeopardy', 'Jeopardy', 'Double Jeopardy'],
            'game_id': ['1', '1', '2'],
            'value': [200, 400, 800]
        })
    
    try:
        df = load_jeopardy_data_from_r2()
        
        if df.empty:
            return pd.DataFrame()
        
        # Clean data
        df = df.dropna(subset=["clue", "correct_response"])
        df['category'] = df['category'].str.upper()
        
        # Add difficulty scoring if not present
        if 'value' not in df.columns:
            df['value'] = df['round'].map({
                'Jeopardy': 200,
                'Double Jeopardy': 400,
                'Final Jeopardy': 1000
            }).fillna(200)
        
        return df
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "history": [],
        "score": 0,
        "total": 0,
        "streak": 0,
        "best_streak": 0,
        "start_time": datetime.datetime.now(),
        "current_clue": None,
        "progress_data": [],
        "difficulty": "Medium",
        "show_hint": False,
        "timer_active": False,
        "time_remaining": 30,
        "achievements": set(),
        "daily_goal": 10,
        "daily_completed": 0,
        "last_played_date": datetime.date.today()
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def check_achievements():
    """Check and award achievements"""
    achievements = []
    
    if st.session_state.streak >= 5 and "Streak Master" not in st.session_state.achievements:
        st.session_state.achievements.add("Streak Master")
        achievements.append("🏆 Streak Master - 5 correct in a row!")
    
    if st.session_state.total >= 50 and "Dedicated Player" not in st.session_state.achievements:
        st.session_state.achievements.add("Dedicated Player")
        achievements.append("🎯 Dedicated Player - 50 questions answered!")
    
    if st.session_state.score / max(st.session_state.total, 1) >= 0.8 and st.session_state.total >= 10:
        if "Accuracy Expert" not in st.session_state.achievements:
            st.session_state.achievements.add("Accuracy Expert")
            achievements.append("🎖️ Accuracy Expert - 80% accuracy!")
    
    return achievements

def display_timer():
    """Display countdown timer"""
    if st.session_state.timer_active:
        elapsed = (datetime.datetime.now() - st.session_state.start_time).seconds
        remaining = max(0, st.session_state.time_remaining - elapsed)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if remaining > 10:
                st.markdown(f'<div class="timer-display">⏱️ {remaining}s</div>', unsafe_allow_html=True)
            elif remaining > 0:
                st.markdown(f'<div class="timer-display" style="color: #ef4444;">⚠️ {remaining}s</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="timer-display" style="color: #ef4444;">⏰ Time\'s Up!</div>', unsafe_allow_html=True)

def display_score_dashboard():
    """Display enhanced score dashboard"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        accuracy = (st.session_state.score / max(st.session_state.total, 1)) * 100
        st.metric("Score", f"{st.session_state.score}/{st.session_state.total}", 
                  f"{accuracy:.1f}% accuracy")
    
    with col2:
        st.metric("Current Streak", st.session_state.streak,
                  f"Best: {st.session_state.best_streak}")
    
    with col3:
        st.metric("Daily Goal", f"{st.session_state.daily_completed}/{st.session_state.daily_goal}",
                  "✅ Complete!" if st.session_state.daily_completed >= st.session_state.daily_goal else None)
    
    with col4:
        st.metric("Achievements", len(st.session_state.achievements),
                  "🏆" * min(len(st.session_state.achievements), 5))

def main():
    """Main application logic"""
    init_session_state()
    
    # Header
    st.title("🧠 Jay's Jeopardy Trainer")
    st.markdown("### Test your knowledge with real Jeopardy questions!")
    
    # Load data
    with st.spinner("Loading Jeopardy dataset..."):
        df = load_data()
    
    if df.empty:
        st.error("❌ Failed to load Jeopardy dataset.")
        st.info("Check your internet connection or contact the administrator.")
        st.stop()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Game Settings")
        
        # Difficulty selector
        st.session_state.difficulty = st.selectbox(
            "Difficulty Level",
            list(DIFFICULTY_SETTINGS.keys()),
            index=1
        )
        
        # Category filter
        categories = sorted(df["category"].unique())
        selected_categories = st.multiselect(
            "Select Categories:",
            categories,
            default=categories[:5] if len(categories) >= 5 else categories
        )
        
        # Time limit
        base_time = st.slider("Base Time Limit (seconds):", 10, 60, 30)
        difficulty_mult = DIFFICULTY_SETTINGS[st.session_state.difficulty]["time_multiplier"]
        st.session_state.time_remaining = int(base_time * difficulty_mult)
        st.caption(f"Adjusted time: {st.session_state.time_remaining}s")
        
        # Daily goal
        st.session_state.daily_goal = st.number_input(
            "Daily Goal:",
            min_value=5,
            max_value=100,
            value=st.session_state.daily_goal,
            step=5
        )
        
        st.markdown("---")
        
        # Statistics
        st.header("📊 Session Stats")
        if st.session_state.total > 0:
            accuracy = (st.session_state.score / st.session_state.total) * 100
            st.progress(accuracy / 100)
            st.caption(f"Accuracy: {accuracy:.1f}%")
            
            # Category performance
            if st.session_state.history:
                history_df = pd.DataFrame(st.session_state.history)
                category_stats = history_df.groupby('category')['was_correct'].agg(['mean', 'count'])
                st.markdown("**Category Performance:**")
                for cat, row in category_stats.iterrows():
                    st.caption(f"{cat}: {row['mean']*100:.0f}% ({int(row['count'])} played)")
    
    # Main game area
    if not selected_categories:
        st.warning("Please select at least one category to continue.")
        st.stop()
    
    filtered_df = df[df["category"].isin(selected_categories)]
    
    if filtered_df.empty:
        st.warning("No clues found for the selected categories.")
        st.stop()
    
    # Display score dashboard
    display_score_dashboard()
    st.markdown("---")
    
    # Get or set current clue
    if st.session_state.current_clue is None:
        st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
        st.session_state.start_time = datetime.datetime.now()
        st.session_state.timer_active = True
        st.session_state.show_hint = False
    
    clue = st.session_state.current_clue
    
    # Display clue in a card
    st.markdown(f'<div class="category-badge">{clue["category"]}</div>', unsafe_allow_html=True)
    st.markdown('<div class="clue-card">', unsafe_allow_html=True)
    st.markdown(f"### {clue['clue']}")
    
    # Show hint if enabled and requested
    if DIFFICULTY_SETTINGS[st.session_state.difficulty]["hint_enabled"]:
        if st.button("💡 Show Hint"):
            st.session_state.show_hint = True
        
        if st.session_state.show_hint:
            answer = clue["correct_response"]
            hint = f"The answer starts with '{answer[0]}' and has {len(answer.split())} word(s)"
            st.info(hint)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Display timer
    display_timer()
    
    # Answer form
    with st.form(key="clue_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            user_input = st.text_input("Your response:", placeholder="Enter your answer here...")
        with col2:
            submitted = st.form_submit_button("Submit", use_container_width=True, type="primary")
    
    if submitted and user_input:
        elapsed_time = (datetime.datetime.now() - st.session_state.start_time).seconds
        similarity = calculate_similarity(user_input, clue["correct_response"])
        
        # Check if answer is correct (with fuzzy matching)
        correct = similarity >= 0.8 and elapsed_time <= st.session_state.time_remaining
        
        if correct:
            st.success(f"✅ Correct! Well done!")
            st.session_state.score += 1
            st.session_state.streak += 1
            st.session_state.best_streak = max(st.session_state.streak, st.session_state.best_streak)
            st.session_state.daily_completed += 1
            
            # Check for achievements
            new_achievements = check_achievements()
            for achievement in new_achievements:
                st.balloons()
                st.success(achievement)
        else:
            if elapsed_time > st.session_state.time_remaining:
                st.error(f"⏰ Time's up! The correct response was: **{clue['correct_response']}**")
            elif similarity > 0.5:
                st.warning(f"🤔 Close, but not quite right! The correct response was: **{clue['correct_response']}**")
            else:
                st.error(f"❌ Incorrect. The correct response was: **{clue['correct_response']}**")
            st.session_state.streak = 0
        
        st.session_state.total += 1
        st.session_state.history.append({
            "timestamp": datetime.datetime.now(),
            "game_id": clue.get("game_id", ""),
            "category": clue["category"],
            "clue": clue["clue"],
            "correct_response": clue["correct_response"],
            "user_response": user_input,
            "was_correct": correct,
            "time_taken": elapsed_time,
            "difficulty": st.session_state.difficulty
        })
        
        # Reset for next question
        st.session_state.current_clue = None
        st.session_state.timer_active = False
        time.sleep(2)  # Brief pause to show feedback
        st.rerun()
    
    # Bottom section with history and analytics
    if st.session_state.history:
        st.markdown("---")
        
        tab1, tab2, tab3 = st.tabs(["📜 Recent History", "📈 Analytics", "🎯 Practice Mode"])
        
        with tab1:
            # Show last 5 questions
            recent_history = pd.DataFrame(st.session_state.history[-5:])
            recent_history['result'] = recent_history['was_correct'].map({True: '✅', False: '❌'})
            st.dataframe(
                recent_history[['result', 'category', 'clue', 'user_response', 'time_taken']],
                use_container_width=True,
                hide_index=True
            )
        
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                # Performance over time
                st.subheader("Performance Trend")
                if len(st.session_state.history) >= 5:
                    history_df = pd.DataFrame(st.session_state.history)
                    history_df['rolling_accuracy'] = history_df['was_correct'].rolling(5).mean() * 100
                    st.line_chart(history_df['rolling_accuracy'])
                else:
                    st.info("Play at least 5 questions to see trends")
            
            with col2:
                # Category breakdown
                st.subheader("Category Performance")
                history_df = pd.DataFrame(st.session_state.history)
                category_performance = history_df.groupby('category')['was_correct'].mean() * 100
                st.bar_chart(category_performance)
        
        with tab3:
            st.subheader("🔁 Practice Missed Questions")
            missed = [h for h in st.session_state.history if not h["was_correct"]]
            
            if missed:
                st.info(f"You have {len(missed)} missed questions to practice")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📚 Practice Random Missed", use_container_width=True):
                        retry = random.choice(missed)
                        st.session_state.current_clue = retry
                        st.rerun()
                
                with col2:
                    if st.button("🎯 Practice Hardest Category", use_container_width=True):
                        history_df = pd.DataFrame(missed)
                        worst_category = history_df['category'].value_counts().index[0]
                        retry = random.choice([m for m in missed if m['category'] == worst_category])
                        st.session_state.current_clue = retry
                        st.rerun()
                
                with col3:
                    if st.button("🔄 Reset Practice", use_container_width=True):
                        st.session_state.history = []
                        st.session_state.score = 0
                        st.session_state.total = 0
                        st.session_state.streak = 0
                        st.rerun()
            else:
                st.success("Great job! No missed questions to practice!")

if __name__ == "__main__":
    main()