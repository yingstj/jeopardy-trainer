import streamlit as st
import pandas as pd
import numpy as np
import json
import random
import time
import os
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# Import AI components
from ai_opponent import AI_PERSONALITIES, AI_DIFFICULTY, simulate_ai_response, simulate_buzzer_race, get_ai_daily_double_wager
from firebase_auth_streamlit import firebase_auth_helper
from jeopardy_answer_checker import JeopardyAnswerChecker

# Page configuration
st.set_page_config(
    page_title="🎯 Jaypardy! - AI Trainer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with game mode styling
st.markdown("""
<style>
    /* Main container */
    .main { padding: 0rem 1rem; }
    
    /* Header gradient */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
    }
    
    /* Game mode cards */
    .game-mode-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .game-mode-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        border-color: #667eea;
    }
    
    .game-mode-card.selected {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
    }
    
    /* AI opponent card */
    .ai-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    
    .ai-personality {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    /* Score displays */
    .score-display {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        color: white;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
    }
    
    .ai-score-display {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }
    
    /* Buzzer indicator */
    .buzzer-indicator {
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    
    /* Question card */
    .question-card {
        background: #f8f9fa;
        border-left: 5px solid #667eea;
        padding: 2rem;
        border-radius: 10px;
        margin: 1.5rem 0;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
    }
    
    /* Daily Double */
    .daily-double {
        background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
        color: #333;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(255, 215, 0, 0.4);
        animation: glow 2s ease-in-out infinite;
    }
    
    @keyframes glow {
        0%, 100% { box-shadow: 0 10px 30px rgba(255, 215, 0, 0.4); }
        50% { box-shadow: 0 15px 40px rgba(255, 215, 0, 0.6); }
    }
    
    /* Stats dashboard */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .stat-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    
    .stat-label {
        color: #666;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'logged_in': False,
        'username': None,
        'user_id': None,
        'auth_method': None,
        'game_mode': None,
        'ai_personality': 'Ken Jennings',
        'ai_difficulty': 'Medium',
        'score': 0,
        'ai_score': 0,
        'streak': 0,
        'questions_answered': 0,
        'correct_answers': 0,
        'current_question': None,
        'current_answer': None,
        'current_value': 200,
        'current_category': None,
        'is_daily_double': False,
        'daily_double_wager': 0,
        'buzzer_winner': None,
        'game_history': [],
        'category_performance': {},
        'achievements': [],
        'total_games': 0,
        'total_wins': 0,
        'highest_score': 0,
        'longest_streak': 0,
        'ai_stats': {
            'games_played': 0,
            'games_won': 0,
            'total_score': 0,
            'questions_answered': 0,
            'correct_answers': 0
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Load questions with multiple sources
@st.cache_data
def load_questions(file_path: str = None) -> pd.DataFrame:
    """Load Jeopardy questions from file"""
    try:
        paths_to_try = [
            "data/all_jeopardy_clues.csv",  # 577k questions
            "data/questions_sample.json",    # 1000 questions
            "data/jeopardy_questions_fixed.json",  # 220 questions
            "data/comprehensive_questions.json",
            "data/jeopardy_questions.json",
        ]
        
        if file_path:
            paths_to_try.insert(0, file_path)
        
        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    if path.endswith('.json'):
                        with open(path, 'r') as f:
                            data = json.load(f)
                            df = pd.DataFrame(data)
                    elif path.endswith('.csv'):
                        df = pd.read_csv(path)
                        # Standardize column names
                        column_mapping = {
                            'clue': 'question',
                            'correct_response': 'answer',
                            'game_id': 'show_number'
                        }
                        df.rename(columns=column_mapping, inplace=True)
                        if 'category' in df.columns:
                            df['category'] = df['category'].str.upper()
                    else:
                        continue
                    
                    if not df.empty:
                        required_cols = ['question', 'answer', 'category']
                        if all(col in df.columns for col in required_cols):
                            if 'value' not in df.columns:
                                df['value'] = 200
                            if 'round' not in df.columns:
                                df['round'] = 'Jeopardy!'
                            
                            num_questions = len(df)
                            if num_questions > 10000:
                                st.success(f"🎉 Loaded {num_questions:,} questions!")
                            else:
                                st.success(f"Loaded {num_questions} questions")
                            return df
                except Exception as e:
                    st.warning(f"Error reading {path}: {e}")
                    continue
        
        # Fallback to sample questions
        st.warning("Using sample questions")
        return pd.DataFrame([
            {"category": "SCIENCE", "question": "This planet is known as the Red Planet", 
             "answer": "Mars", "value": 200, "round": "Jeopardy!"},
        ])
    except Exception as e:
        st.error(f"Error loading questions: {e}")
        return pd.DataFrame()

# Game Mode Selection
def show_game_mode_selection():
    """Display game mode selection screen"""
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Jaypardy! AI Trainer</h1>
        <p>Choose Your Training Mode</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎮 **Solo Practice**\n\nPractice at your own pace", 
                     use_container_width=True, key="solo_mode"):
            st.session_state.game_mode = "solo"
            st.rerun()
    
    with col2:
        if st.button("🤖 **vs AI Opponent**\n\nCompete against AI champions", 
                     use_container_width=True, key="ai_mode"):
            st.session_state.game_mode = "ai_opponent"
            st.rerun()
    
    with col3:
        if st.button("📊 **Category Focus**\n\nMaster specific categories", 
                     use_container_width=True, key="category_mode"):
            st.session_state.game_mode = "category_focus"
            st.rerun()
    
    # Show stats if user has played before
    if st.session_state.total_games > 0:
        st.markdown("---")
        st.markdown("### 📈 Your Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Games", st.session_state.total_games)
        with col2:
            win_rate = (st.session_state.total_wins / st.session_state.total_games * 100) if st.session_state.total_games > 0 else 0
            st.metric("Win Rate", f"{win_rate:.1f}%")
        with col3:
            st.metric("Highest Score", f"${st.session_state.highest_score:,}")
        with col4:
            st.metric("Longest Streak", st.session_state.longest_streak)

# AI Opponent Setup
def setup_ai_opponent():
    """Configure AI opponent settings"""
    st.markdown("### 🤖 Configure Your AI Opponent")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Select AI Personality")
        for name, data in AI_PERSONALITIES.items():
            if st.button(f"**{name}**\n{data['description']}", 
                        use_container_width=True, 
                        key=f"ai_{name}"):
                st.session_state.ai_personality = name
                st.rerun()
        
        if st.session_state.ai_personality:
            personality = AI_PERSONALITIES[st.session_state.ai_personality]
            st.info(f"**Selected:** {st.session_state.ai_personality}")
            st.write(f"**Strengths:** {', '.join(personality['strengths']) if personality['strengths'] else 'None'}")
            st.write(f"**Weaknesses:** {', '.join(personality['weaknesses']) if personality['weaknesses'] else 'None'}")
    
    with col2:
        st.markdown("#### Select Difficulty")
        difficulty = st.radio(
            "AI Difficulty Level",
            ["Easy", "Medium", "Hard"],
            index=["Easy", "Medium", "Hard"].index(st.session_state.ai_difficulty)
        )
        st.session_state.ai_difficulty = difficulty
        
        diff_info = AI_DIFFICULTY[difficulty]
        st.info(f"""
        **{difficulty} Mode:**
        - Accuracy: {(AI_PERSONALITIES[st.session_state.ai_personality]['base_accuracy'] + diff_info['accuracy_modifier'])*100:.0f}%
        - Buzzer Speed: {diff_info['buzzer_speed']:.1f}s
        - DD Aggression: {diff_info['daily_double_aggression']*100:.0f}%
        """)
    
    if st.button("🎮 Start Game vs AI", use_container_width=True, type="primary"):
        st.session_state.game_started = True
        st.rerun()

# Play against AI
def play_vs_ai(df: pd.DataFrame):
    """Main game loop for AI opponent mode"""
    
    # Score display
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown(f"""
        <div class="score-display">
            <h3>Your Score</h3>
            <div style="font-size: 2rem; font-weight: bold;">${st.session_state.score:,}</div>
            <div>Streak: {st.session_state.streak}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="score-display ai-score-display">
            <h3>{st.session_state.ai_personality}</h3>
            <div style="font-size: 2rem; font-weight: bold;">${st.session_state.ai_score:,}</div>
            <div>Accuracy: {(st.session_state.ai_stats['correct_answers'] / max(1, st.session_state.ai_stats['questions_answered']) * 100):.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Get random question
        if st.session_state.current_question is None:
            question_row = df.sample(1).iloc[0]
            st.session_state.current_question = question_row['question']
            st.session_state.current_answer = question_row['answer']
            st.session_state.current_category = question_row.get('category', 'GENERAL')
            st.session_state.current_value = question_row.get('value', 200)
            
            # Check for Daily Double (10% chance)
            st.session_state.is_daily_double = random.random() < 0.1
            st.session_state.buzzer_winner = None
        
        # Display category and value
        st.markdown(f"""
        <div style="text-align: center; margin: 1rem 0;">
            <h3>{st.session_state.current_category}</h3>
            <h4>${st.session_state.current_value}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Daily Double handling
        if st.session_state.is_daily_double and st.session_state.daily_double_wager == 0:
            st.markdown("""
            <div class="daily-double">
                <h2>⭐ DAILY DOUBLE! ⭐</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Buzzer race for Daily Double
            winner, reaction_time = simulate_buzzer_race(st.session_state.ai_difficulty)
            
            if winner == "player":
                st.success(f"🎯 You buzzed in first! ({reaction_time:.2f}s)")
                max_wager = max(1000, st.session_state.score)
                wager = st.number_input(
                    f"Enter your wager (max ${max_wager:,})",
                    min_value=5,
                    max_value=max_wager,
                    value=min(1000, max_wager),
                    step=100
                )
                if st.button("Lock in Wager"):
                    st.session_state.daily_double_wager = wager
                    st.session_state.buzzer_winner = "player"
                    st.rerun()
            else:
                ai_wager = get_ai_daily_double_wager(
                    st.session_state.ai_score,
                    st.session_state.score,
                    st.session_state.ai_difficulty
                )
                st.warning(f"🤖 {st.session_state.ai_personality} buzzed in first! ({reaction_time:.2f}s)")
                st.info(f"AI wagers ${ai_wager:,}")
                st.session_state.daily_double_wager = ai_wager
                st.session_state.buzzer_winner = "ai"
                time.sleep(2)
                st.rerun()
        
        # Display question
        st.markdown(f"""
        <div class="question-card">
            <div style="font-size: 1.3rem; line-height: 1.6;">
                {st.session_state.current_question}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Handle regular question buzzer
        if not st.session_state.is_daily_double and st.session_state.buzzer_winner is None:
            if st.button("🔔 BUZZ IN!", use_container_width=True, type="primary"):
                winner, reaction_time = simulate_buzzer_race(st.session_state.ai_difficulty)
                st.session_state.buzzer_winner = winner
                
                if winner == "player":
                    st.success(f"🎯 You buzzed in first! ({reaction_time:.2f}s)")
                else:
                    st.warning(f"🤖 {st.session_state.ai_personality} buzzed in first! ({reaction_time:.2f}s)")
                    # AI answers
                    is_correct, thinking_time = simulate_ai_response(
                        st.session_state.current_question,
                        st.session_state.current_category,
                        st.session_state.ai_difficulty,
                        st.session_state.ai_personality
                    )
                    
                    with st.spinner(f"{st.session_state.ai_personality} is thinking..."):
                        time.sleep(thinking_time)
                    
                    value = st.session_state.daily_double_wager if st.session_state.is_daily_double else st.session_state.current_value
                    
                    if is_correct:
                        st.success(f"✅ {st.session_state.ai_personality} got it right!")
                        st.session_state.ai_score += value
                        st.session_state.ai_stats['correct_answers'] += 1
                    else:
                        st.error(f"❌ {st.session_state.ai_personality} got it wrong!")
                        st.session_state.ai_score -= value
                    
                    st.session_state.ai_stats['questions_answered'] += 1
                    st.info(f"The answer was: **{st.session_state.current_answer}**")
                    
                    if st.button("Next Question"):
                        st.session_state.current_question = None
                        st.session_state.is_daily_double = False
                        st.session_state.daily_double_wager = 0
                        st.rerun()
        
        # Player answers
        if st.session_state.buzzer_winner == "player":
            user_answer = st.text_input(
                "Your answer (remember to phrase as a question!):",
                placeholder="What is...? / Who is...?"
            )
            
            if st.button("Submit Answer", type="primary"):
                if user_answer:
                    # Check if phrased as question
                    is_question = any(user_answer.lower().startswith(q) for q in 
                                     ["what", "who", "where", "when", "why", "how"])
                    
                    if not is_question:
                        st.warning("Remember: Answers must be in the form of a question!")
                    
                    # Check answer correctness
                    is_correct = check_answer(user_answer, st.session_state.current_answer)
                    value = st.session_state.daily_double_wager if st.session_state.is_daily_double else st.session_state.current_value
                    
                    if is_correct and is_question:
                        st.success(f"✅ Correct! +${value}")
                        st.session_state.score += value
                        st.session_state.streak += 1
                        st.session_state.correct_answers += 1
                        
                        if st.session_state.streak > st.session_state.longest_streak:
                            st.session_state.longest_streak = st.session_state.streak
                    else:
                        st.error(f"❌ Incorrect! -${value}")
                        st.session_state.score -= value
                        st.session_state.streak = 0
                    
                    st.session_state.questions_answered += 1
                    st.info(f"The answer was: **{st.session_state.current_answer}**")
                    
                    # Update category performance
                    cat = st.session_state.current_category
                    if cat not in st.session_state.category_performance:
                        st.session_state.category_performance[cat] = {'correct': 0, 'total': 0}
                    st.session_state.category_performance[cat]['total'] += 1
                    if is_correct and is_question:
                        st.session_state.category_performance[cat]['correct'] += 1
                    
                    if st.button("Next Question"):
                        st.session_state.current_question = None
                        st.session_state.is_daily_double = False
                        st.session_state.daily_double_wager = 0
                        st.rerun()

# Initialize answer checker
answer_checker = JeopardyAnswerChecker()

# Check answer correctness
def check_answer(user_answer: str, correct_answer: str, threshold: float = 0.85) -> bool:
    """Check if user's answer is correct using improved Jeopardy rules"""
    is_correct, confidence = answer_checker.check_answer(user_answer, correct_answer, threshold)
    return is_correct

# Solo Practice Mode
def play_solo_practice(df: pd.DataFrame):
    """Solo practice mode without AI opponent"""
    st.markdown("### 🎮 Solo Practice Mode")
    
    # Score display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score", f"${st.session_state.score:,}")
    with col2:
        st.metric("Streak", st.session_state.streak)
    with col3:
        accuracy = (st.session_state.correct_answers / max(1, st.session_state.questions_answered) * 100)
        st.metric("Accuracy", f"{accuracy:.1f}%")
    
    # Category filter
    categories = ["All"] + sorted(df['category'].unique().tolist())
    selected_category = st.selectbox("Choose Category", categories)
    
    if selected_category != "All":
        df = df[df['category'] == selected_category]
    
    # Get question
    if st.button("🎲 New Question", use_container_width=True):
        st.session_state.current_question = None
    
    if st.session_state.current_question is None and not df.empty:
        question_row = df.sample(1).iloc[0]
        st.session_state.current_question = question_row['question']
        st.session_state.current_answer = question_row['answer']
        st.session_state.current_category = question_row.get('category', 'GENERAL')
        st.session_state.current_value = question_row.get('value', 200)
    
    if st.session_state.current_question:
        # Display question
        st.markdown(f"""
        <div class="question-card">
            <h4>{st.session_state.current_category} - ${st.session_state.current_value}</h4>
            <p style="font-size: 1.2rem; margin-top: 1rem;">
                {st.session_state.current_question}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Answer input
        user_answer = st.text_input("Your answer:", placeholder="Type your answer...")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Submit", type="primary", use_container_width=True):
                if user_answer:
                    is_correct = check_answer(user_answer, st.session_state.current_answer)
                    
                    if is_correct:
                        st.success(f"✅ Correct! +${st.session_state.current_value}")
                        st.session_state.score += st.session_state.current_value
                        st.session_state.streak += 1
                        st.session_state.correct_answers += 1
                    else:
                        st.error(f"❌ Incorrect!")
                        st.session_state.streak = 0
                    
                    st.session_state.questions_answered += 1
                    st.info(f"The answer was: **{st.session_state.current_answer}**")
        
        with col2:
            if st.button("Skip", use_container_width=True):
                st.info(f"The answer was: **{st.session_state.current_answer}**")
                st.session_state.current_question = None
                st.session_state.streak = 0
                st.rerun()

# Category Focus Mode
def play_category_focus(df: pd.DataFrame):
    """Practice specific categories"""
    st.markdown("### 📚 Category Focus Training")
    
    # Category selection
    categories = sorted(df['category'].unique().tolist())
    selected_categories = st.multiselect(
        "Select categories to practice:",
        categories,
        default=categories[:3] if len(categories) >= 3 else categories
    )
    
    if selected_categories:
        df_filtered = df[df['category'].isin(selected_categories)]
        
        # Show category stats
        st.markdown("#### 📊 Category Performance")
        cols = st.columns(len(selected_categories))
        
        for i, cat in enumerate(selected_categories):
            with cols[i]:
                perf = st.session_state.category_performance.get(cat, {'correct': 0, 'total': 0})
                accuracy = (perf['correct'] / max(1, perf['total'])) * 100 if perf['total'] > 0 else 0
                st.metric(
                    cat[:15] + "..." if len(cat) > 15 else cat,
                    f"{accuracy:.0f}%",
                    f"{perf['correct']}/{perf['total']}"
                )
        
        # Practice questions
        play_solo_practice(df_filtered)
    else:
        st.warning("Please select at least one category to practice")

# Statistics Dashboard
def show_statistics():
    """Display detailed statistics"""
    st.markdown("### 📈 Performance Analytics")
    
    # Overall stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Questions", st.session_state.questions_answered)
    with col2:
        accuracy = (st.session_state.correct_answers / max(1, st.session_state.questions_answered)) * 100
        st.metric("Overall Accuracy", f"{accuracy:.1f}%")
    with col3:
        st.metric("Current Score", f"${st.session_state.score:,}")
    with col4:
        st.metric("Best Streak", st.session_state.longest_streak)
    
    # Category breakdown
    if st.session_state.category_performance:
        st.markdown("#### Category Mastery")
        
        cat_data = []
        for cat, perf in st.session_state.category_performance.items():
            if perf['total'] > 0:
                cat_data.append({
                    'Category': cat,
                    'Questions': perf['total'],
                    'Correct': perf['correct'],
                    'Accuracy': f"{(perf['correct']/perf['total']*100):.1f}%"
                })
        
        if cat_data:
            df_stats = pd.DataFrame(cat_data)
            df_stats = df_stats.sort_values('Questions', ascending=False)
            st.dataframe(df_stats, use_container_width=True, hide_index=True)
    
    # AI Battle Stats (if played against AI)
    if st.session_state.ai_stats['games_played'] > 0:
        st.markdown("#### 🤖 AI Battle Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Games vs AI", st.session_state.ai_stats['games_played'])
        with col2:
            win_rate = (st.session_state.ai_stats['games_won'] / st.session_state.ai_stats['games_played']) * 100
            st.metric("Win Rate vs AI", f"{win_rate:.1f}%")
        with col3:
            avg_score = st.session_state.ai_stats['total_score'] / st.session_state.ai_stats['games_played']
            st.metric("Avg Score vs AI", f"${avg_score:.0f}")

# Main App
def main():
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎯 Jaypardy! AI Trainer")
        
        if st.session_state.logged_in:
            st.success(f"👤 {st.session_state.username}")
            
            if st.button("📊 Statistics"):
                st.session_state.show_stats = True
            
            if st.button("🏠 Change Game Mode"):
                st.session_state.game_mode = None
                st.session_state.game_started = False
                st.rerun()
            
            if st.button("🚪 Logout"):
                for key in st.session_state.keys():
                    del st.session_state[key]
                st.rerun()
        else:
            st.info("Please log in to save progress")
    
    # Main content
    if not st.session_state.logged_in:
        # Show login page (reuse from original app.py)
        from app import show_login_page
        show_login_page()
    else:
        # Load questions
        df = load_questions()
        
        if df.empty:
            st.error("No questions available. Please check data files.")
            return
        
        # Show statistics if requested
        if st.session_state.get('show_stats', False):
            show_statistics()
            if st.button("Back to Game"):
                st.session_state.show_stats = False
                st.rerun()
        # Game mode selection
        elif st.session_state.game_mode is None:
            show_game_mode_selection()
        # AI opponent setup
        elif st.session_state.game_mode == "ai_opponent" and not st.session_state.get('game_started', False):
            setup_ai_opponent()
        # Play against AI
        elif st.session_state.game_mode == "ai_opponent":
            play_vs_ai(df)
        # Solo practice
        elif st.session_state.game_mode == "solo":
            play_solo_practice(df)
        # Category focus
        elif st.session_state.game_mode == "category_focus":
            play_category_focus(df)

if __name__ == "__main__":
    main()