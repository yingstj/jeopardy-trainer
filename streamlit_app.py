"""
Jaypardy! - Streamlit Jeopardy Training App with Firebase Authentication
"""

import streamlit as st
import pandas as pd
import random
import json
import hashlib
import firebase_admin
from firebase_admin import credentials, auth, firestore
import time
from datetime import datetime, timedelta
import os
from typing import Dict, Any, Optional, List, Tuple
import re

# Page configuration
st.set_page_config(
    page_title="Jaypardy!",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Firebase using Streamlit Secrets (only once)
def initialize_firebase():
    """Initialize Firebase using Streamlit secrets"""
    if 'firebase_initialized' not in st.session_state:
        try:
            # Use Streamlit secrets instead of hardcoded values
            firebase_config = {
                "type": "service_account",
                "project_id": st.secrets["firebase_project_id"],
                "private_key_id": st.secrets["firebase_private_key_id"],
                "private_key": st.secrets["firebase_private_key"].replace('\\n', '\n'),
                "client_email": st.secrets["firebase_client_email"],
                "client_id": st.secrets["firebase_client_id"],
                "auth_uri": st.secrets.get("firebase_auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": st.secrets.get("firebase_token_uri", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": st.secrets.get("firebase_auth_provider_cert", "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": st.secrets["firebase_client_cert_url"],
                "universe_domain": "googleapis.com"
            }
            
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            
            st.session_state.firebase_initialized = True
            st.session_state.db = firestore.client()
            
            return True
            
        except ValueError:
            # App already initialized
            st.session_state.firebase_initialized = True
            st.session_state.db = firestore.client()
            return True
            
        except Exception as e:
            st.error(f"Firebase initialization failed: {e}")
            st.info("Using local authentication fallback")
            st.session_state.firebase_initialized = False
            return False
    
    return st.session_state.firebase_initialized

# Local User Manager (Fallback when Firebase is not available)
class LocalUserManager:
    """Local user management fallback"""
    def __init__(self):
        if 'users' not in st.session_state:
            st.session_state.users = {
                'demo': {
                    'password': hashlib.sha256('demo123'.encode()).hexdigest(),
                    'stats': {
                        'total_questions': 0,
                        'correct_answers': 0,
                        'categories': {},
                        'streak': 0,
                        'best_streak': 0
                    }
                }
            }
    
    def authenticate(self, username: str, password: str) -> bool:
        users = st.session_state.get('users', {})
        if username in users:
            hashed = hashlib.sha256(password.encode()).hexdigest()
            return users[username]['password'] == hashed
        return False
    
    def create_user(self, username: str, password: str) -> bool:
        if username in st.session_state.users:
            return False
        st.session_state.users[username] = {
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'stats': {
                'total_questions': 0,
                'correct_answers': 0,
                'categories': {},
                'streak': 0,
                'best_streak': 0
            }
        }
        return True
    
    def get_user_stats(self, username: str) -> Dict:
        return st.session_state.users.get(username, {}).get('stats', {})
    
    def update_user_stats(self, username: str, stats: Dict):
        if username in st.session_state.users:
            st.session_state.users[username]['stats'] = stats

# Firestore Manager for Cloud Persistence
class FirestoreManager:
    """Manage Firestore operations"""
    def __init__(self):
        self.db = st.session_state.get('db')
    
    def save_user_data(self, username: str, data: Dict) -> bool:
        """Save user data to Firestore"""
        if self.db:
            try:
                user_ref = self.db.collection('users').document(username)
                user_ref.set(data, merge=True)
                return True
            except Exception as e:
                st.error(f"Failed to save to Firestore: {e}")
        return False
    
    def load_user_data(self, username: str) -> Optional[Dict]:
        """Load user data from Firestore"""
        if self.db:
            try:
                user_ref = self.db.collection('users').document(username)
                doc = user_ref.get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                st.error(f"Failed to load from Firestore: {e}")
        return None
    
    def save_game_session(self, username: str, session_data: Dict) -> bool:
        """Save game session to Firestore"""
        if self.db:
            try:
                session_ref = self.db.collection('game_sessions').add({
                    'username': username,
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    **session_data
                })
                return True
            except Exception as e:
                st.error(f"Failed to save session: {e}")
        return False
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get global leaderboard from Firestore"""
        if self.db:
            try:
                users = self.db.collection('users').order_by(
                    'stats.total_score', direction=firestore.Query.DESCENDING
                ).limit(limit).stream()
                
                leaderboard = []
                for user in users:
                    data = user.to_dict()
                    leaderboard.append({
                        'username': user.id,
                        'score': data.get('stats', {}).get('total_score', 0),
                        'accuracy': data.get('stats', {}).get('accuracy', 0)
                    })
                return leaderboard
            except Exception as e:
                st.error(f"Failed to get leaderboard: {e}")
        return []

# Answer Checker with Fuzzy Matching
class AnswerChecker:
    """Check answers with fuzzy matching"""
    
    @staticmethod
    def normalize_answer(answer: str) -> str:
        """Normalize answer for comparison"""
        # Remove articles
        answer = re.sub(r'^(a|an|the)\s+', '', answer, flags=re.IGNORECASE)
        # Remove punctuation and extra spaces
        answer = re.sub(r'[^\w\s]', '', answer)
        answer = ' '.join(answer.split())
        return answer.lower().strip()
    
    @staticmethod
    def check_answer(user_answer: str, correct_answer: str, threshold: float = 0.85) -> Tuple[bool, float]:
        """Check if user answer is correct with fuzzy matching"""
        # Normalize both answers
        user_norm = AnswerChecker.normalize_answer(user_answer)
        correct_norm = AnswerChecker.normalize_answer(correct_answer)
        
        # Exact match
        if user_norm == correct_norm:
            return True, 1.0
        
        # Check if user answer contains correct answer or vice versa
        if user_norm in correct_norm or correct_norm in user_norm:
            return True, 0.9
        
        # Calculate similarity
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, user_norm, correct_norm).ratio()
        
        return similarity >= threshold, similarity

# Load Questions
@st.cache_data
def load_questions(file_path: str = None) -> pd.DataFrame:
    """Load Jeopardy questions from file"""
    try:
        # Try to load from multiple possible locations
        paths_to_try = [
            "data/jeopardy_questions.json",
            "jeopardy_questions.json",
            "data/questions.json",
            "questions.json"
        ]
        
        if file_path:
            paths_to_try.insert(0, file_path)
        
        for path in paths_to_try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    return pd.DataFrame(data)
        
        # If no file found, create sample questions
        st.warning("No question file found. Using sample questions.")
        sample_questions = [
            {
                "category": "SCIENCE",
                "question": "This planet is known as the Red Planet",
                "answer": "Mars",
                "value": 200,
                "round": "Jeopardy!"
            },
            {
                "category": "HISTORY",
                "question": "This president was the first President of the United States",
                "answer": "George Washington",
                "value": 200,
                "round": "Jeopardy!"
            },
            {
                "category": "LITERATURE",
                "question": "This Shakespeare play features the characters Romeo and Juliet",
                "answer": "Romeo and Juliet",
                "value": 100,
                "round": "Jeopardy!"
            }
        ]
        return pd.DataFrame(sample_questions)
        
    except Exception as e:
        st.error(f"Error loading questions: {e}")
        return pd.DataFrame()

# Authentication UI
def show_login_page():
    """Display login/signup page"""
    st.title("🎯 Welcome to Jaypardy!")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login", use_container_width=True):
                user_manager = LocalUserManager()
                if user_manager.authenticate(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    
                    # Try to sync with Firestore
                    if st.session_state.get('firebase_initialized'):
                        firestore_manager = FirestoreManager()
                        cloud_data = firestore_manager.load_user_data(username)
                        if cloud_data:
                            user_manager.update_user_stats(username, cloud_data.get('stats', {}))
                    
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        with col2:
            if st.button("Demo Mode", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.username = "demo"
                st.info("Logged in as demo user")
                st.rerun()
    
    with tab2:
        st.subheader("Create New Account")
        new_username = st.text_input("Choose Username", key="signup_username")
        new_password = st.text_input("Choose Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        
        if st.button("Sign Up", use_container_width=True):
            if new_password != confirm_password:
                st.error("Passwords don't match")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                user_manager = LocalUserManager()
                if user_manager.create_user(new_username, new_password):
                    st.session_state.logged_in = True
                    st.session_state.username = new_username
                    
                    # Save to Firestore if available
                    if st.session_state.get('firebase_initialized'):
                        firestore_manager = FirestoreManager()
                        firestore_manager.save_user_data(new_username, {
                            'created_at': firestore.SERVER_TIMESTAMP,
                            'stats': user_manager.get_user_stats(new_username)
                        })
                    
                    st.success("Account created successfully!")
                    st.rerun()
                else:
                    st.error("Username already exists")

# Main Game UI
def show_game():
    """Display the main game interface"""
    username = st.session_state.username
    
    # Sidebar
    with st.sidebar:
        st.title(f"👤 {username}")
        
        # Display stats
        user_manager = LocalUserManager()
        stats = user_manager.get_user_stats(username)
        
        st.subheader("📊 Your Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Questions", stats.get('total_questions', 0))
            st.metric("Current Streak", stats.get('streak', 0))
        with col2:
            st.metric("Correct", stats.get('correct_answers', 0))
            st.metric("Best Streak", stats.get('best_streak', 0))
        
        if stats.get('total_questions', 0) > 0:
            accuracy = (stats.get('correct_answers', 0) / stats['total_questions']) * 100
            st.metric("Accuracy", f"{accuracy:.1f}%")
        
        st.divider()
        
        # Game settings
        st.subheader("⚙️ Game Settings")
        difficulty = st.select_slider(
            "Difficulty",
            options=["Easy", "Medium", "Hard"],
            value="Medium"
        )
        
        # Category filter
        df = load_questions()
        if not df.empty:
            categories = ["All"] + sorted(df['category'].unique().tolist())
            selected_category = st.selectbox("Category", categories)
        else:
            selected_category = "All"
        
        st.divider()
        
        # Leaderboard
        if st.session_state.get('firebase_initialized'):
            st.subheader("🏆 Leaderboard")
            firestore_manager = FirestoreManager()
            leaderboard = firestore_manager.get_leaderboard(5)
            for i, entry in enumerate(leaderboard, 1):
                st.write(f"{i}. {entry['username']}: {entry['score']}")
        
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            # Save stats before logout
            if st.session_state.get('firebase_initialized'):
                firestore_manager = FirestoreManager()
                firestore_manager.save_user_data(username, {
                    'stats': stats,
                    'last_seen': firestore.SERVER_TIMESTAMP
                })
            
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
    
    # Main content
    st.title("🎯 Jaypardy! Training")
    
    # Load questions
    df = load_questions()
    
    if df.empty:
        st.error("No questions available. Please check your data files.")
        return
    
    # Filter by category if selected
    if selected_category != "All":
        df = df[df['category'] == selected_category]
    
    # Filter by difficulty
    if difficulty == "Easy":
        df = df[df['value'] <= 400]
    elif difficulty == "Medium":
        df = df[(df['value'] > 400) & (df['value'] <= 800)]
    else:
        df = df[df['value'] > 800]
    
    if df.empty:
        st.warning("No questions match your filters. Try different settings.")
        return
    
    # Initialize game state
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
        st.session_state.question_answered = False
        st.session_state.user_answer = ""
    
    # Game controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🎲 New Question", use_container_width=True):
            # Select random question
            question = df.sample(1).iloc[0]
            st.session_state.current_question = question.to_dict()
            st.session_state.question_answered = False
            st.session_state.user_answer = ""
    
    # Display current question
    if st.session_state.current_question:
        question = st.session_state.current_question
        
        # Question display
        st.divider()
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Category: {question['category']}")
        with col2:
            st.subheader(f"Value: ${question.get('value', 0)}")
        
        # Question box
        st.info(f"**Question:** {question['question']}")
        
        # Answer input
        if not st.session_state.question_answered:
            user_answer = st.text_input(
                "Your Answer:",
                key="answer_input",
                placeholder="Type your answer here..."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Submit Answer", use_container_width=True):
                    if user_answer:
                        st.session_state.user_answer = user_answer
                        st.session_state.question_answered = True
                        
                        # Check answer
                        checker = AnswerChecker()
                        is_correct, similarity = checker.check_answer(
                            user_answer,
                            question['answer']
                        )
                        
                        # Update stats
                        user_manager = LocalUserManager()
                        stats = user_manager.get_user_stats(username)
                        stats['total_questions'] = stats.get('total_questions', 0) + 1
                        
                        if is_correct:
                            stats['correct_answers'] = stats.get('correct_answers', 0) + 1
                            stats['streak'] = stats.get('streak', 0) + 1
                            stats['best_streak'] = max(
                                stats.get('best_streak', 0),
                                stats['streak']
                            )
                            stats['total_score'] = stats.get('total_score', 0) + question.get('value', 0)
                        else:
                            stats['streak'] = 0
                        
                        # Update category stats
                        category = question['category']
                        if 'categories' not in stats:
                            stats['categories'] = {}
                        if category not in stats['categories']:
                            stats['categories'][category] = {'total': 0, 'correct': 0}
                        stats['categories'][category]['total'] += 1
                        if is_correct:
                            stats['categories'][category]['correct'] += 1
                        
                        # Calculate accuracy
                        if stats['total_questions'] > 0:
                            stats['accuracy'] = (stats['correct_answers'] / stats['total_questions']) * 100
                        
                        # Save stats
                        user_manager.update_user_stats(username, stats)
                        
                        # Save to Firestore if available
                        if st.session_state.get('firebase_initialized'):
                            firestore_manager = FirestoreManager()
                            firestore_manager.save_user_data(username, {'stats': stats})
                            firestore_manager.save_game_session(username, {
                                'question': question,
                                'user_answer': user_answer,
                                'is_correct': is_correct,
                                'similarity': similarity
                            })
                        
                        st.rerun()
                    else:
                        st.warning("Please enter an answer")
            
            with col2:
                if st.button("Skip Question", use_container_width=True):
                    st.session_state.question_answered = True
                    st.rerun()
        
        else:
            # Show result
            checker = AnswerChecker()
            is_correct, similarity = checker.check_answer(
                st.session_state.user_answer,
                question['answer']
            )
            
            if is_correct:
                st.success(f"✅ Correct! (Similarity: {similarity:.0%})")
            else:
                st.error(f"❌ Incorrect (Similarity: {similarity:.0%})")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Your Answer:** {st.session_state.user_answer}")
            with col2:
                st.write(f"**Correct Answer:** {question['answer']}")
            
            if st.button("Next Question", use_container_width=True):
                st.session_state.current_question = None
                st.session_state.question_answered = False
                st.session_state.user_answer = ""
                st.rerun()

# Main App
def main():
    # Initialize Firebase
    firebase_status = initialize_firebase()
    
    # Show Firebase status in header
    if firebase_status:
        st.success("☁️ Connected to Firebase Cloud Storage", icon="✅")
    else:
        st.info("📱 Using local storage mode", icon="ℹ️")
    
    # Check login state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Show appropriate page
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_game()

if __name__ == "__main__":
    main()