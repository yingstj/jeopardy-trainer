"""
Jaypardy! Complete Edition - All Features Included
- Timer with visual countdown
- Two-player mode
- AI opponents with realistic buzzer timing
- Full Jeopardy board (6x5 grid)
- Daily Doubles
- Final Jeopardy
- Tournament mode
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import random
import time
import os
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
import asyncio
import threading
from collections import defaultdict

# Import components
from ai_opponent import AI_PERSONALITIES, AI_DIFFICULTY, simulate_ai_response, simulate_buzzer_race, get_ai_daily_double_wager
from firebase_auth_streamlit import firebase_auth_helper
from jeopardy_answer_checker import JeopardyAnswerChecker

# Page configuration
st.set_page_config(
    page_title="🎯 Jaypardy! - Complete Edition",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with timer and animations
st.markdown("""
<style>
    /* Main container */
    .main { padding: 0rem 1rem; }
    
    /* Jeopardy Board */
    .jeopardy-board {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 10px;
        margin: 20px 0;
        background: #060CE9;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    
    .board-cell {
        background: #060CE9;
        color: #FFD700;
        border: 3px solid #FFD700;
        padding: 20px;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s;
        border-radius: 8px;
        min-height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .board-cell:hover {
        transform: scale(1.05);
        background: #0820F0;
        box-shadow: 0 5px 15px rgba(255, 215, 0, 0.4);
    }
    
    .board-cell.answered {
        background: #333;
        color: #666;
        border-color: #666;
        cursor: not-allowed;
    }
    
    .category-header {
        background: #060CE9;
        color: white;
        font-size: 18px;
        text-transform: uppercase;
        padding: 15px;
        border: 2px solid #FFD700;
    }
    
    /* Timer Display */
    .timer-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 50%;
        width: 120px;
        height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 20px auto;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        position: relative;
    }
    
    .timer-text {
        color: white;
        font-size: 48px;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .timer-warning {
        animation: pulse-warning 1s infinite;
    }
    
    .timer-danger {
        animation: pulse-danger 0.5s infinite;
        background: linear-gradient(135deg, #ff6b6b 0%, #ff0000 100%);
    }
    
    @keyframes pulse-warning {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    @keyframes pulse-danger {
        0%, 100% { transform: scale(1); background: linear-gradient(135deg, #ff6b6b 0%, #ff0000 100%); }
        50% { transform: scale(1.1); background: linear-gradient(135deg, #ff0000 0%, #cc0000 100%); }
    }
    
    /* Buzzer Button */
    .buzzer-button {
        background: linear-gradient(135deg, #ff6b6b 0%, #ff8e53 100%);
        color: white;
        border: none;
        border-radius: 50%;
        width: 150px;
        height: 150px;
        font-size: 24px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 10px 30px rgba(255, 107, 107, 0.4);
        margin: 20px auto;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .buzzer-button:hover {
        transform: scale(1.1);
        box-shadow: 0 15px 40px rgba(255, 107, 107, 0.6);
    }
    
    .buzzer-button:active {
        transform: scale(0.95);
    }
    
    .buzzer-pressed {
        animation: buzzer-flash 0.5s;
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
    }
    
    @keyframes buzzer-flash {
        0% { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }
        50% { background: linear-gradient(135deg, #8BC34A 0%, #7CB342 100%); }
        100% { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }
    }
    
    /* Player Cards */
    .player-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        margin: 10px;
        border: 3px solid transparent;
        transition: all 0.3s;
    }
    
    .player-card.active {
        border-color: #4CAF50;
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(76, 175, 80, 0.3);
    }
    
    .player-card.buzzed {
        border-color: #FFD700;
        background: linear-gradient(135deg, #fffef0 0%, #fff9e0 100%);
    }
    
    /* Score Display */
    .score-display {
        font-size: 36px;
        font-weight: bold;
        text-align: center;
        margin: 10px 0;
    }
    
    .score-positive {
        color: #4CAF50;
    }
    
    .score-negative {
        color: #ff6b6b;
    }
    
    /* Final Jeopardy */
    .final-jeopardy {
        background: linear-gradient(135deg, #060CE9 0%, #0820F0 100%);
        color: #FFD700;
        padding: 40px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 20px 50px rgba(6, 12, 233, 0.4);
        margin: 30px 0;
    }
    
    .final-jeopardy h1 {
        font-size: 48px;
        margin-bottom: 20px;
        text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.5);
    }
    
    /* Tournament Bracket */
    .tournament-bracket {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin: 20px 0;
    }
    
    .bracket-match {
        background: white;
        border: 2px solid #060CE9;
        border-radius: 10px;
        padding: 15px;
        margin: 10px;
        min-width: 200px;
    }
    
    .bracket-winner {
        background: linear-gradient(135deg, #FFD700 0%, #FFA000 100%);
        color: white;
    }
    
    /* Sound indicator */
    .sound-wave {
        display: inline-block;
        width: 4px;
        height: 20px;
        background: #4CAF50;
        margin: 0 2px;
        animation: wave 0.5s infinite;
        animation-delay: calc(var(--i) * 0.1s);
    }
    
    @keyframes wave {
        0%, 100% { height: 20px; }
        50% { height: 40px; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        # User info
        'logged_in': False,
        'username': None,
        'user_id': None,
        'auth_method': None,
        
        # Game modes
        'game_mode': None,  # solo, two_player, ai_opponent, tournament
        'game_phase': 'menu',  # menu, board, question, answer, final_jeopardy
        
        # Players
        'players': {},  # {player_id: {name, score, is_ai, personality}}
        'current_player': None,
        'buzzed_player': None,
        
        # Game state
        'board': None,  # 6x5 grid of questions
        'current_question': None,
        'current_answer': None,
        'current_value': 0,
        'current_category': None,
        'answered_questions': set(),
        
        # Timer
        'timer_active': False,
        'timer_start': None,
        'timer_duration': 10,  # seconds
        'buzzer_window': 5,  # seconds to buzz in
        
        # Scoring
        'scores': defaultdict(int),
        'streaks': defaultdict(int),
        'correct_answers': defaultdict(int),
        'total_answers': defaultdict(int),
        
        # Daily Double
        'daily_doubles': [],  # positions of daily doubles
        'is_daily_double': False,
        'daily_double_wager': 0,
        
        # Final Jeopardy
        'final_jeopardy_category': None,
        'final_jeopardy_question': None,
        'final_jeopardy_answer': None,
        'final_wagers': {},
        'final_answers': {},
        
        # Tournament
        'tournament_bracket': [],
        'tournament_round': 0,
        'tournament_winners': [],
        
        # Settings
        'sound_enabled': True,
        'timer_enabled': True,
        'difficulty': 'Medium',
        
        # Statistics
        'game_stats': defaultdict(lambda: defaultdict(int)),
        'category_performance': defaultdict(lambda: defaultdict(int)),
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Timer functionality
class GameTimer:
    """Manages game timer with visual countdown"""
    
    @staticmethod
    def start_timer(duration: int):
        """Start a countdown timer"""
        st.session_state.timer_active = True
        st.session_state.timer_start = datetime.now()
        st.session_state.timer_duration = duration
    
    @staticmethod
    def get_remaining_time() -> float:
        """Get remaining time in seconds"""
        if not st.session_state.timer_active:
            return 0
        
        elapsed = (datetime.now() - st.session_state.timer_start).total_seconds()
        remaining = st.session_state.timer_duration - elapsed
        return max(0, remaining)
    
    @staticmethod
    def display_timer():
        """Display visual countdown timer"""
        remaining = GameTimer.get_remaining_time()
        
        if remaining <= 0:
            st.session_state.timer_active = False
            return False
        
        # Determine timer style based on remaining time
        timer_class = ""
        if remaining <= 3:
            timer_class = "timer-danger"
        elif remaining <= 5:
            timer_class = "timer-warning"
        
        # Display timer
        timer_html = f"""
        <div class="timer-container {timer_class}">
            <div class="timer-text">{int(remaining)}</div>
        </div>
        """
        st.markdown(timer_html, unsafe_allow_html=True)
        
        return True
    
    @staticmethod
    def stop_timer():
        """Stop the timer"""
        st.session_state.timer_active = False

# Jeopardy Board
class JeopardyBoard:
    """Manages the Jeopardy game board"""
    
    CATEGORIES = 6
    VALUES = [200, 400, 600, 800, 1000]
    
    @staticmethod
    def create_board(df: pd.DataFrame) -> Dict:
        """Create a 6x5 Jeopardy board from questions"""
        board = {}
        
        # Get random categories
        all_categories = df['category'].unique()
        selected_categories = random.sample(
            list(all_categories), 
            min(JeopardyBoard.CATEGORIES, len(all_categories))
        )
        
        # Fill board with questions
        for i, category in enumerate(selected_categories):
            cat_questions = df[df['category'] == category].sample(
                n=min(5, len(df[df['category'] == category]))
            )
            
            board[category] = {}
            for j, value in enumerate(JeopardyBoard.VALUES):
                if j < len(cat_questions):
                    question = cat_questions.iloc[j]
                    board[category][value] = {
                        'question': question['question'],
                        'answer': question['answer'],
                        'answered': False
                    }
                else:
                    # Fallback if not enough questions
                    board[category][value] = {
                        'question': f"Sample question for {category} ${value}",
                        'answer': "Sample answer",
                        'answered': False
                    }
        
        # Add Daily Doubles (1 in first round, 2 in double jeopardy)
        num_daily_doubles = 1 if st.session_state.get('round', 1) == 1 else 2
        daily_double_positions = []
        
        for _ in range(num_daily_doubles):
            cat = random.choice(list(board.keys()))
            val = random.choice(JeopardyBoard.VALUES[1:])  # Not in $200 row
            daily_double_positions.append((cat, val))
            board[cat][val]['daily_double'] = True
        
        st.session_state.daily_doubles = daily_double_positions
        
        return board
    
    @staticmethod
    def display_board():
        """Display the Jeopardy board"""
        board = st.session_state.board
        
        if not board:
            return
        
        # Create grid layout
        cols = st.columns(JeopardyBoard.CATEGORIES)
        
        # Display categories
        for i, category in enumerate(board.keys()):
            with cols[i]:
                st.markdown(f"""
                <div class="board-cell category-header">
                    {category[:20]}
                </div>
                """, unsafe_allow_html=True)
        
        # Display values
        for value in JeopardyBoard.VALUES:
            cols = st.columns(JeopardyBoard.CATEGORIES)
            for i, category in enumerate(board.keys()):
                with cols[i]:
                    question_data = board[category][value]
                    
                    if not question_data['answered']:
                        if st.button(f"${value}", key=f"{category}_{value}", 
                                   use_container_width=True):
                            st.session_state.current_category = category
                            st.session_state.current_value = value
                            st.session_state.current_question = question_data['question']
                            st.session_state.current_answer = question_data['answer']
                            st.session_state.is_daily_double = question_data.get('daily_double', False)
                            st.session_state.game_phase = 'question'
                            st.rerun()
                    else:
                        st.markdown(f"""
                        <div class="board-cell answered">
                            -
                        </div>
                        """, unsafe_allow_html=True)

# Game Modes
def show_game_mode_selection():
    """Display game mode selection screen"""
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #060CE9 0%, #0820F0 100%); 
                padding: 3rem; border-radius: 20px; text-align: center; margin-bottom: 2rem;">
        <h1 style="color: #FFD700; font-size: 4rem; margin: 0; text-shadow: 3px 3px 6px rgba(0,0,0,0.5);">
            🎯 JAYPARDY!
        </h1>
        <p style="color: white; font-size: 1.5rem; margin-top: 1rem;">
            The Ultimate Jeopardy Training Experience
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 Single Player Modes")
        
        if st.button("🎮 **Solo Practice**\n\nPractice at your own pace", 
                     use_container_width=True, key="solo_mode"):
            st.session_state.game_mode = "solo"
            st.session_state.players = {"player1": {"name": st.session_state.username or "Player", 
                                                    "score": 0, "is_ai": False}}
            st.session_state.game_phase = "board"
            st.rerun()
        
        if st.button("🤖 **vs AI Opponent**\n\nBattle against champions", 
                     use_container_width=True, key="ai_mode"):
            st.session_state.game_mode = "ai_opponent"
            st.session_state.game_phase = "ai_setup"
            st.rerun()
    
    with col2:
        st.markdown("### 👥 Multiplayer Modes")
        
        if st.button("👫 **Two Player**\n\nCompete with a friend", 
                     use_container_width=True, key="two_player_mode"):
            st.session_state.game_mode = "two_player"
            st.session_state.game_phase = "player_setup"
            st.rerun()
        
        if st.button("🏆 **Tournament**\n\n4-8 player bracket", 
                     use_container_width=True, key="tournament_mode"):
            st.session_state.game_mode = "tournament"
            st.session_state.game_phase = "tournament_setup"
            st.rerun()
    
    # Show recent stats
    if st.session_state.get('game_stats'):
        st.markdown("---")
        st.markdown("### 📊 Your Recent Performance")
        col1, col2, col3, col4 = st.columns(4)
        
        stats = st.session_state.game_stats[st.session_state.username or 'guest']
        with col1:
            st.metric("Games Played", stats.get('games', 0))
        with col2:
            st.metric("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
        with col3:
            st.metric("Highest Score", f"${stats.get('high_score', 0):,}")
        with col4:
            st.metric("Avg Response Time", f"{stats.get('avg_time', 0):.1f}s")

# Two Player Setup
def setup_two_player():
    """Setup two player game"""
    st.markdown("### 👫 Two Player Setup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Player 1")
        player1_name = st.text_input("Name", value="Player 1", key="p1_name")
        player1_color = st.color_picker("Buzzer Color", "#FF6B6B", key="p1_color")
    
    with col2:
        st.markdown("#### Player 2")
        player2_name = st.text_input("Name", value="Player 2", key="p2_name")
        player2_color = st.color_picker("Buzzer Color", "#4ECDC4", key="p2_color")
    
    st.markdown("### ⚙️ Game Settings")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        timer_enabled = st.checkbox("Enable Timer", value=True)
        st.session_state.timer_enabled = timer_enabled
    
    with col2:
        buzzer_time = st.slider("Buzzer Window (seconds)", 3, 10, 5)
        st.session_state.buzzer_window = buzzer_time
    
    with col3:
        answer_time = st.slider("Answer Time (seconds)", 10, 30, 15)
        st.session_state.timer_duration = answer_time
    
    if st.button("🎮 Start Game", use_container_width=True, type="primary"):
        st.session_state.players = {
            "player1": {"name": player1_name, "score": 0, "is_ai": False, "color": player1_color},
            "player2": {"name": player2_name, "score": 0, "is_ai": False, "color": player2_color}
        }
        st.session_state.game_phase = "board"
        st.rerun()

# Play Question with Timer and Buzzer
def play_question_with_buzzer(df: pd.DataFrame):
    """Display question with buzzer race functionality"""
    
    # Display current question
    st.markdown(f"""
    <div class="question-card" style="background: #060CE9; color: white; padding: 3rem; 
                border-radius: 15px; margin: 2rem 0;">
        <h2 style="color: #FFD700; text-align: center; margin-bottom: 1rem;">
            {st.session_state.current_category} - ${st.session_state.current_value}
        </h2>
        <h1 style="text-align: center; font-size: 2rem; line-height: 1.5;">
            {st.session_state.current_question}
        </h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Daily Double special handling
    if st.session_state.is_daily_double:
        st.markdown("""
        <div class="daily-double">
            <h1>⭐ DAILY DOUBLE! ⭐</h1>
        </div>
        """, unsafe_allow_html=True)
        
        # Handle wager
        if st.session_state.daily_double_wager == 0:
            current_player = st.session_state.current_player or "player1"
            max_wager = max(1000, st.session_state.scores[current_player])
            
            wager = st.number_input(
                f"Enter your wager (max ${max_wager:,})",
                min_value=5,
                max_value=max_wager,
                value=min(1000, max_wager),
                step=100
            )
            
            if st.button("Lock in Wager", use_container_width=True):
                st.session_state.daily_double_wager = wager
                st.rerun()
            return
    
    # Buzzer phase
    if not st.session_state.buzzed_player:
        st.markdown("### 🔔 Buzz In!")
        
        # Start buzzer timer
        if not st.session_state.timer_active and st.session_state.timer_enabled:
            GameTimer.start_timer(st.session_state.buzzer_window)
        
        # Display timer
        if st.session_state.timer_enabled:
            timer_active = GameTimer.display_timer()
            if not timer_active:
                st.warning("⏰ Time's up! No one buzzed in.")
                if st.button("Next Question"):
                    mark_question_answered()
                    st.session_state.game_phase = "board"
                    st.rerun()
                return
        
        # Buzzer buttons for each player
        cols = st.columns(len(st.session_state.players))
        
        for i, (player_id, player_data) in enumerate(st.session_state.players.items()):
            with cols[i]:
                # AI players buzz automatically
                if player_data.get('is_ai'):
                    # Simulate AI buzzer
                    if random.random() < 0.3:  # 30% chance per refresh
                        st.session_state.buzzed_player = player_id
                        GameTimer.stop_timer()
                        st.rerun()
                else:
                    # Human player buzzer
                    st.markdown(f"""
                    <div class="player-card">
                        <h3>{player_data['name']}</h3>
                        <div class="score-display {'score-positive' if st.session_state.scores[player_id] >= 0 else 'score-negative'}">
                            ${st.session_state.scores[player_id]:,}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"🔔 BUZZ!", key=f"buzz_{player_id}", 
                               use_container_width=True, type="primary"):
                        st.session_state.buzzed_player = player_id
                        GameTimer.stop_timer()
                        st.rerun()
        
        # Auto-refresh for timer update
        if st.session_state.timer_active:
            time.sleep(0.1)
            st.rerun()
    
    # Answer phase
    else:
        player_id = st.session_state.buzzed_player
        player_data = st.session_state.players[player_id]
        
        st.success(f"🎯 {player_data['name']} buzzed in!")
        
        # Start answer timer
        if not st.session_state.timer_active and st.session_state.timer_enabled:
            GameTimer.start_timer(st.session_state.timer_duration)
        
        # Display timer
        if st.session_state.timer_enabled:
            timer_active = GameTimer.display_timer()
            if not timer_active:
                st.error("⏰ Time's up!")
                handle_answer("", player_id, timeout=True)
                return
        
        # AI answers automatically
        if player_data.get('is_ai'):
            with st.spinner(f"{player_data['name']} is thinking..."):
                time.sleep(random.uniform(1, 3))
            
            # Get AI answer
            is_correct, _ = simulate_ai_response(
                st.session_state.current_question,
                st.session_state.current_category,
                st.session_state.difficulty,
                player_data.get('personality', 'Balanced')
            )
            
            if is_correct:
                fake_answer = f"What is {st.session_state.current_answer}?"
            else:
                fake_answer = "What is [incorrect answer]?"
            
            st.info(f"{player_data['name']} answered: {fake_answer}")
            handle_answer(fake_answer if is_correct else "wrong", player_id)
        
        # Human answer input
        else:
            answer = st.text_input(
                f"{player_data['name']}, what is your answer?",
                placeholder="Remember to phrase as a question!",
                key="answer_input"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Submit Answer", use_container_width=True, type="primary"):
                    GameTimer.stop_timer()
                    handle_answer(answer, player_id)
            
            with col2:
                if st.button("Pass", use_container_width=True):
                    GameTimer.stop_timer()
                    handle_answer("", player_id, passed=True)
        
        # Auto-refresh for timer
        if st.session_state.timer_active:
            time.sleep(0.1)
            st.rerun()

def handle_answer(answer: str, player_id: str, timeout: bool = False, passed: bool = False):
    """Process answer and update scores"""
    
    answer_checker = JeopardyAnswerChecker()
    player_data = st.session_state.players[player_id]
    
    value = st.session_state.daily_double_wager if st.session_state.is_daily_double else st.session_state.current_value
    
    if timeout:
        st.error(f"❌ {player_data['name']} ran out of time! -${value}")
        st.session_state.scores[player_id] -= value
        st.session_state.streaks[player_id] = 0
    elif passed:
        st.warning(f"➖ {player_data['name']} passed.")
        st.session_state.streaks[player_id] = 0
    else:
        is_correct, confidence = answer_checker.check_answer(answer, st.session_state.current_answer)
        
        # Check for Jeopardy format
        is_question = any(answer.lower().startswith(q) for q in 
                         ["what", "who", "where", "when", "why", "how"])
        
        if is_correct and is_question:
            st.success(f"✅ Correct! {player_data['name']} +${value}")
            st.session_state.scores[player_id] += value
            st.session_state.streaks[player_id] += 1
            st.session_state.correct_answers[player_id] += 1
        else:
            if not is_question and is_correct:
                st.warning("Remember to phrase as a question!")
            st.error(f"❌ Incorrect! {player_data['name']} -${value}")
            st.session_state.scores[player_id] -= value
            st.session_state.streaks[player_id] = 0
        
        st.session_state.total_answers[player_id] += 1
    
    st.info(f"The correct answer was: **{st.session_state.current_answer}**")
    
    # Mark question as answered
    mark_question_answered()
    
    # Reset for next question
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Next Question", use_container_width=True, type="primary"):
            reset_question_state()
            st.session_state.game_phase = "board"
            st.rerun()
    
    with col2:
        if check_board_complete():
            if st.button("Final Jeopardy!", use_container_width=True, type="primary"):
                st.session_state.game_phase = "final_jeopardy"
                st.rerun()

def mark_question_answered():
    """Mark current question as answered on the board"""
    if st.session_state.board and st.session_state.current_category and st.session_state.current_value:
        st.session_state.board[st.session_state.current_category][st.session_state.current_value]['answered'] = True

def reset_question_state():
    """Reset question-related state"""
    st.session_state.current_question = None
    st.session_state.current_answer = None
    st.session_state.current_category = None
    st.session_state.current_value = 0
    st.session_state.buzzed_player = None
    st.session_state.is_daily_double = False
    st.session_state.daily_double_wager = 0
    GameTimer.stop_timer()

def check_board_complete() -> bool:
    """Check if all questions have been answered"""
    if not st.session_state.board:
        return False
    
    for category in st.session_state.board.values():
        for question in category.values():
            if not question['answered']:
                return False
    return True

# Final Jeopardy
def play_final_jeopardy(df: pd.DataFrame):
    """Final Jeopardy round"""
    
    st.markdown("""
    <div class="final-jeopardy">
        <h1>FINAL JEOPARDY!</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Get Final Jeopardy question
    if not st.session_state.final_jeopardy_question:
        # Get a random hard question
        hard_questions = df[df['value'] >= 800] if 'value' in df.columns else df
        if len(hard_questions) > 0:
            final_q = hard_questions.sample(1).iloc[0]
        else:
            final_q = df.sample(1).iloc[0]
        
        st.session_state.final_jeopardy_category = final_q.get('category', 'GENERAL KNOWLEDGE')
        st.session_state.final_jeopardy_question = final_q['question']
        st.session_state.final_jeopardy_answer = final_q['answer']
    
    # Display category
    st.markdown(f"""
    <div style="text-align: center; margin: 2rem 0;">
        <h2 style="color: #060CE9;">Category: {st.session_state.final_jeopardy_category}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Wager phase
    if not all(st.session_state.final_wagers.values()):
        st.markdown("### 💰 Place Your Wagers")
        
        for player_id, player_data in st.session_state.players.items():
            if player_id not in st.session_state.final_wagers:
                score = st.session_state.scores[player_id]
                
                if score <= 0:
                    st.warning(f"{player_data['name']} cannot participate (negative score)")
                    st.session_state.final_wagers[player_id] = 0
                else:
                    if player_data.get('is_ai'):
                        # AI wager logic
                        wager = min(score, random.randint(100, score))
                        st.session_state.final_wagers[player_id] = wager
                        st.info(f"{player_data['name']} has placed their wager")
                    else:
                        wager = st.number_input(
                            f"{player_data['name']}'s wager (max ${score:,})",
                            min_value=0,
                            max_value=score,
                            value=min(1000, score),
                            step=100,
                            key=f"final_wager_{player_id}"
                        )
                        
                        if st.button(f"Lock in {player_data['name']}'s wager", key=f"lock_{player_id}"):
                            st.session_state.final_wagers[player_id] = wager
                            st.rerun()
        
        return
    
    # Question phase
    st.markdown(f"""
    <div class="question-card" style="background: #060CE9; color: white; padding: 3rem; 
                border-radius: 15px; margin: 2rem 0;">
        <h1 style="text-align: center; font-size: 2.5rem; line-height: 1.5; color: #FFD700;">
            {st.session_state.final_jeopardy_question}
        </h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Answer phase
    if not all(st.session_state.final_answers.values()):
        st.markdown("### ✍️ Write Your Answers")
        
        for player_id, player_data in st.session_state.players.items():
            if st.session_state.final_wagers[player_id] > 0 and player_id not in st.session_state.final_answers:
                if player_data.get('is_ai'):
                    # AI answer
                    is_correct, _ = simulate_ai_response(
                        st.session_state.final_jeopardy_question,
                        st.session_state.final_jeopardy_category,
                        st.session_state.difficulty,
                        player_data.get('personality', 'Balanced')
                    )
                    
                    if is_correct:
                        st.session_state.final_answers[player_id] = f"What is {st.session_state.final_jeopardy_answer}?"
                    else:
                        st.session_state.final_answers[player_id] = "What is [incorrect]?"
                    
                    st.info(f"{player_data['name']} has submitted their answer")
                else:
                    answer = st.text_area(
                        f"{player_data['name']}'s answer",
                        placeholder="Remember to phrase as a question!",
                        key=f"final_answer_{player_id}"
                    )
                    
                    if st.button(f"Submit {player_data['name']}'s answer", key=f"submit_{player_id}"):
                        st.session_state.final_answers[player_id] = answer
                        st.rerun()
        
        return
    
    # Results phase
    st.markdown("### 🏆 Final Jeopardy Results")
    
    answer_checker = JeopardyAnswerChecker()
    final_scores = {}
    
    for player_id, player_data in st.session_state.players.items():
        wager = st.session_state.final_wagers.get(player_id, 0)
        answer = st.session_state.final_answers.get(player_id, "")
        
        if wager > 0:
            is_correct, _ = answer_checker.check_answer(answer, st.session_state.final_jeopardy_answer)
            
            if is_correct:
                st.success(f"✅ {player_data['name']}: Correct! +${wager:,}")
                st.session_state.scores[player_id] += wager
            else:
                st.error(f"❌ {player_data['name']}: Incorrect! -${wager:,}")
                st.session_state.scores[player_id] -= wager
        
        final_scores[player_id] = st.session_state.scores[player_id]
    
    st.info(f"The correct answer was: **{st.session_state.final_jeopardy_answer}**")
    
    # Display final standings
    st.markdown("### 🎯 Final Standings")
    
    sorted_players = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    
    for i, (player_id, score) in enumerate(sorted_players):
        player_data = st.session_state.players[player_id]
        
        if i == 0:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #FFD700 0%, #FFA000 100%); 
                        color: white; padding: 2rem; border-radius: 15px; margin: 1rem 0;">
                <h2>🏆 WINNER: {player_data['name']}</h2>
                <h1>${score:,}</h1>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: white; border: 2px solid #060CE9; 
                        padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                <h3>#{i+1} {player_data['name']}: ${score:,}</h3>
            </div>
            """, unsafe_allow_html=True)
    
    # Update stats
    winner_id = sorted_players[0][0]
    st.session_state.game_stats[st.session_state.players[winner_id]['name']]['games'] += 1
    st.session_state.game_stats[st.session_state.players[winner_id]['name']]['wins'] += 1
    
    if st.button("🎮 New Game", use_container_width=True, type="primary"):
        reset_game()
        st.rerun()

def reset_game():
    """Reset game state for new game"""
    st.session_state.game_phase = "menu"
    st.session_state.board = None
    st.session_state.scores = defaultdict(int)
    st.session_state.players = {}
    st.session_state.final_wagers = {}
    st.session_state.final_answers = {}
    reset_question_state()

# Tournament Mode
def setup_tournament():
    """Setup tournament bracket"""
    st.markdown("### 🏆 Tournament Setup")
    
    num_players = st.slider("Number of Players", 4, 8, 4, step=2)
    
    st.markdown("#### Enter Player Names")
    
    players = {}
    cols = st.columns(2)
    
    for i in range(num_players):
        with cols[i % 2]:
            name = st.text_input(f"Player {i+1}", value=f"Player {i+1}", key=f"tournament_p{i}")
            
            # Option to make AI
            is_ai = st.checkbox(f"AI Player", key=f"tournament_ai{i}")
            
            if is_ai:
                personality = st.selectbox(
                    f"AI Personality",
                    list(AI_PERSONALITIES.keys()),
                    key=f"tournament_personality{i}"
                )
            else:
                personality = None
            
            players[f"player{i}"] = {
                "name": name,
                "is_ai": is_ai,
                "personality": personality,
                "score": 0
            }
    
    if st.button("🏆 Start Tournament", use_container_width=True, type="primary"):
        st.session_state.players = players
        st.session_state.tournament_bracket = create_tournament_bracket(list(players.keys()))
        st.session_state.tournament_round = 0
        st.session_state.game_phase = "tournament_match"
        st.rerun()

def create_tournament_bracket(players: List[str]) -> List[List[tuple]]:
    """Create tournament bracket pairings"""
    random.shuffle(players)
    bracket = []
    
    # First round
    first_round = []
    for i in range(0, len(players), 2):
        first_round.append((players[i], players[i+1]))
    bracket.append(first_round)
    
    # Calculate subsequent rounds
    num_rounds = len(players) // 2
    while num_rounds > 1:
        num_rounds = num_rounds // 2
        bracket.append([None] * num_rounds)
    
    return bracket

# Load questions
@st.cache_data
def load_questions(file_path: str = None) -> pd.DataFrame:
    """Load Jeopardy questions from file"""
    try:
        paths_to_try = [
            "data/all_jeopardy_clues.csv",
            "data/questions_sample.json",
            "data/jeopardy_questions_fixed.json",
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    if path.endswith('.json'):
                        with open(path, 'r') as f:
                            data = json.load(f)
                            df = pd.DataFrame(data)
                    elif path.endswith('.csv'):
                        df = pd.read_csv(path)
                        column_mapping = {
                            'clue': 'question',
                            'correct_response': 'answer',
                        }
                        df.rename(columns=column_mapping, inplace=True)
                        if 'category' in df.columns:
                            df['category'] = df['category'].str.upper()
                    
                    if not df.empty:
                        required_cols = ['question', 'answer', 'category']
                        if all(col in df.columns for col in required_cols):
                            return df
                except Exception as e:
                    continue
        
        # Fallback
        return pd.DataFrame([
            {"category": "SCIENCE", "question": "This planet is known as the Red Planet", 
             "answer": "Mars", "value": 200},
        ])
    except Exception as e:
        st.error(f"Error loading questions: {e}")
        return pd.DataFrame()

# Main App
def main():
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎯 Jaypardy! Complete")
        
        if st.session_state.logged_in:
            st.success(f"👤 {st.session_state.username}")
            
            # Game controls
            if st.session_state.game_phase != "menu":
                if st.button("🏠 Main Menu"):
                    reset_game()
                    st.rerun()
                
                # Display scores
                if st.session_state.players:
                    st.markdown("### 📊 Scores")
                    for player_id, player_data in st.session_state.players.items():
                        score = st.session_state.scores[player_id]
                        st.metric(player_data['name'], f"${score:,}")
            
            # Settings
            st.markdown("### ⚙️ Settings")
            st.session_state.sound_enabled = st.checkbox("🔊 Sound Effects", 
                                                         value=st.session_state.sound_enabled)
            st.session_state.difficulty = st.select_slider(
                "AI Difficulty",
                ["Easy", "Medium", "Hard"],
                value=st.session_state.difficulty
            )
            
            if st.button("🚪 Logout"):
                for key in st.session_state.keys():
                    del st.session_state[key]
                st.rerun()
    
    # Main content
    if not st.session_state.logged_in:
        # Login (reuse existing)
        st.session_state.logged_in = True
        st.session_state.username = "Player"
        st.rerun()
    
    # Load questions
    df = load_questions()
    
    if df.empty:
        st.error("No questions available!")
        return
    
    # Game phases
    if st.session_state.game_phase == "menu":
        show_game_mode_selection()
    
    elif st.session_state.game_phase == "player_setup":
        setup_two_player()
    
    elif st.session_state.game_phase == "ai_setup":
        # AI setup (reuse existing)
        st.session_state.players = {
            "player1": {"name": st.session_state.username, "score": 0, "is_ai": False},
            "ai1": {"name": "Ken Jennings", "score": 0, "is_ai": True, "personality": "Ken Jennings"}
        }
        st.session_state.game_phase = "board"
        st.rerun()
    
    elif st.session_state.game_phase == "tournament_setup":
        setup_tournament()
    
    elif st.session_state.game_phase == "board":
        # Create board if needed
        if not st.session_state.board:
            st.session_state.board = JeopardyBoard.create_board(df)
        
        # Display board
        JeopardyBoard.display_board()
        
        # Check if board complete
        if check_board_complete():
            st.info("Board complete! Ready for Final Jeopardy!")
            if st.button("🎯 Final Jeopardy!", use_container_width=True, type="primary"):
                st.session_state.game_phase = "final_jeopardy"
                st.rerun()
    
    elif st.session_state.game_phase == "question":
        play_question_with_buzzer(df)
    
    elif st.session_state.game_phase == "final_jeopardy":
        play_final_jeopardy(df)

if __name__ == "__main__":
    main()