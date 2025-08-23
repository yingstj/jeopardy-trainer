"""
Jaypardy! - Streamlit Jeopardy Training App with Firebase + Google Authentication
Enhanced version with Google Sign-In support
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
import requests
import jwt

# Page configuration
st.set_page_config(
    page_title="Jaypardy!",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Google Sign-In button
st.markdown("""
<style>
    .google-signin-button {
        background-color: #4285f4;
        color: white;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: 500;
        border-radius: 4px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        margin: 10px 0;
        width: 100%;
        justify-content: center;
    }
    .google-signin-button:hover {
        background-color: #357ae8;
    }
    .google-icon {
        width: 20px;
        height: 20px;
        background: white;
        border-radius: 2px;
        padding: 2px;
    }
    .auth-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
        border-radius: 10px;
        background: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Firebase using Streamlit Secrets
def initialize_firebase():
    """Initialize Firebase using Streamlit secrets"""
    if 'firebase_initialized' not in st.session_state:
        try:
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
            st.session_state.firebase_api_key = st.secrets.get("firebase_api_key")
            
            return True
            
        except ValueError:
            st.session_state.firebase_initialized = True
            st.session_state.db = firestore.client()
            return True
            
        except Exception as e:
            st.error(f"Firebase initialization failed: {e}")
            st.info("Using local authentication fallback")
            st.session_state.firebase_initialized = False
            return False
    
    return st.session_state.firebase_initialized

# Firebase Auth Helper for Google Sign-In
class FirebaseAuthHelper:
    """Helper for Firebase Authentication with Google"""
    
    @staticmethod
    def get_google_signin_url():
        """Generate Google Sign-In URL"""
        # This would typically be handled by Firebase Auth UI
        # For Streamlit, we'll provide instructions
        return """
        To enable Google Sign-In:
        1. Go to Firebase Console → Authentication → Sign-in method
        2. Enable Google as a sign-in provider
        3. Add your domain to authorized domains
        """
    
    @staticmethod
    def verify_firebase_token(id_token: str) -> Optional[Dict]:
        """Verify a Firebase ID token"""
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            st.error(f"Token verification failed: {e}")
            return None
    
    @staticmethod
    def create_or_get_user(email: str, display_name: str = None) -> Optional[auth.UserRecord]:
        """Create or get a Firebase user"""
        try:
            # Try to get existing user
            user = auth.get_user_by_email(email)
            return user
        except auth.UserNotFoundError:
            # Create new user
            user = auth.create_user(
                email=email,
                display_name=display_name or email.split('@')[0]
            )
            return user
        except Exception as e:
            st.error(f"User management error: {e}")
            return None

# Enhanced Firestore Manager
class FirestoreManager:
    """Manage Firestore operations"""
    def __init__(self):
        self.db = st.session_state.get('db')
    
    def save_user_data(self, user_id: str, data: Dict) -> bool:
        """Save user data to Firestore"""
        if self.db:
            try:
                user_ref = self.db.collection('users').document(user_id)
                user_ref.set(data, merge=True)
                return True
            except Exception as e:
                st.error(f"Failed to save to Firestore: {e}")
        return False
    
    def load_user_data(self, user_id: str) -> Optional[Dict]:
        """Load user data from Firestore"""
        if self.db:
            try:
                user_ref = self.db.collection('users').document(user_id)
                doc = user_ref.get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                st.error(f"Failed to load from Firestore: {e}")
        return None

# Answer Checker with Fuzzy Matching
class AnswerChecker:
    """Check answers with fuzzy matching"""
    
    @staticmethod
    def normalize_answer(answer: str) -> str:
        """Normalize answer for comparison"""
        answer = re.sub(r'^(a|an|the)\s+', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'[^\w\s]', '', answer)
        answer = ' '.join(answer.split())
        return answer.lower().strip()
    
    @staticmethod
    def check_answer(user_answer: str, correct_answer: str, threshold: float = 0.85) -> Tuple[bool, float]:
        """Check if user answer is correct with fuzzy matching"""
        user_norm = AnswerChecker.normalize_answer(user_answer)
        correct_norm = AnswerChecker.normalize_answer(correct_answer)
        
        if user_norm == correct_norm:
            return True, 1.0
        
        if user_norm in correct_norm or correct_norm in user_norm:
            return True, 0.9
        
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, user_norm, correct_norm).ratio()
        
        return similarity >= threshold, similarity

# Load Questions
@st.cache_data
def load_questions(file_path: str = None) -> pd.DataFrame:
    """Load Jeopardy questions from file"""
    try:
        paths_to_try = [
            "data/jeopardy_questions_fixed.json",
            "data/questions_sample.json",
            "data/comprehensive_questions.json",
            "data/jeopardy_questions.json",
            "jeopardy_questions.json",
            "data/questions.json",
            "questions.json",
            "data/all_jeopardy_clues.csv",
            "data/jeopardy_with_answers.csv"
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
                        # Standardize column names for CSV files
                        column_mapping = {
                            'Question': 'question',
                            'Answer': 'answer',
                            'Category': 'category',
                            'Value': 'value',
                            'Round': 'round',
                            'Air Date': 'air_date'
                        }
                        df.rename(columns=column_mapping, inplace=True)
                    else:
                        continue
                    
                    if not df.empty:
                        # Ensure required columns exist
                        required_cols = ['question', 'answer', 'category']
                        if all(col in df.columns for col in required_cols):
                            # Add missing columns with defaults
                            if 'value' not in df.columns:
                                df['value'] = 200
                            if 'round' not in df.columns:
                                df['round'] = 'Jeopardy!'
                            st.success(f"Loaded {len(df)} questions from {path}")
                            return df
                except json.JSONDecodeError as e:
                    st.warning(f"Could not parse {path}: {e}")
                    continue
                except Exception as e:
                    st.warning(f"Error reading {path}: {e}")
                    continue
        
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
            },
            {
                "category": "GEOGRAPHY",
                "question": "This is the capital of France",
                "answer": "Paris",
                "value": 100,
                "round": "Jeopardy!"
            },
            {
                "category": "SPORTS",
                "question": "This sport is known as 'America's Pastime'",
                "answer": "Baseball",
                "value": 200,
                "round": "Jeopardy!"
            }
        ]
        return pd.DataFrame(sample_questions)
        
    except Exception as e:
        st.error(f"Error loading questions: {e}")
        return pd.DataFrame()

# Google Sign-In Component (Simulated)
def show_google_signin():
    """Show Google Sign-In button and handle authentication"""
    
    st.markdown("""
    <div class="auth-container">
        <h3 style="text-align: center;">🔐 Sign In with Google</h3>
        <p style="text-align: center; color: #666;">
            For the best experience, sign in with your Google account
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Since Streamlit doesn't support direct OAuth, we'll use a workaround
    st.info("""
    **Google Sign-In Instructions:**
    1. Visit: [Firebase Auth](https://jaypardy-53a55.firebaseapp.com/login)
    2. Sign in with Google
    3. Copy your authentication token
    4. Paste it below
    """)
    
    # Token input for Google Sign-In
    auth_token = st.text_input(
        "Paste your authentication token:",
        type="password",
        placeholder="Enter token from Firebase Auth"
    )
    
    if st.button("🔑 Verify Token", use_container_width=True):
        if auth_token:
            helper = FirebaseAuthHelper()
            user_data = helper.verify_firebase_token(auth_token)
            if user_data:
                st.session_state.logged_in = True
                st.session_state.username = user_data.get('email', 'User')
                st.session_state.user_id = user_data.get('uid')
                st.session_state.auth_method = 'google'
                st.success(f"Welcome, {user_data.get('name', st.session_state.username)}!")
                st.rerun()
            else:
                st.error("Invalid token. Please try again.")
        else:
            st.warning("Please enter your authentication token")
    
    return False

# Authentication UI
def show_login_page():
    """Display login/signup page with Google Sign-In"""
    st.title("🎯 Welcome to Jaypardy!")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="color: #667eea;">Test your trivia knowledge!</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Tab selection for different auth methods
        tab1, tab2, tab3 = st.tabs(["🔑 Email Sign In", "✨ Create Account", "🔷 Google Sign In"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Email:", placeholder="Enter your email")
                password = st.text_input("Password:", type="password", placeholder="Enter your password")
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("🎮 Sign In", use_container_width=True, type="primary")
                with col2:
                    guest = st.form_submit_button("👤 Play as Guest", use_container_width=True)
                
                if submitted:
                    if username and password:
                        # Here you would verify with Firebase Auth
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.auth_method = 'email'
                        st.success(f"Welcome back, {username}!")
                        st.rerun()
                    else:
                        st.error("Please enter both email and password")
                
                if guest:
                    st.session_state.logged_in = True
                    st.session_state.username = f"Guest_{random.randint(1000, 9999)}"
                    st.session_state.auth_method = 'guest'
                    st.info("Playing as guest - progress won't be saved")
                    st.rerun()
        
        with tab2:
            with st.form("signup_form"):
                new_email = st.text_input("Email:", placeholder="your@email.com")
                new_password = st.text_input("Create password:", type="password", placeholder="At least 6 characters")
                confirm_password = st.text_input("Confirm password:", type="password", placeholder="Re-enter password")
                
                create_account = st.form_submit_button("🌟 Create Account", use_container_width=True, type="primary")
                
                if create_account:
                    if new_email and new_password:
                        if len(new_password) < 6:
                            st.error("Password must be at least 6 characters long")
                        elif new_password != confirm_password:
                            st.error("Passwords don't match")
                        else:
                            # Create Firebase user
                            helper = FirebaseAuthHelper()
                            user = helper.create_or_get_user(new_email)
                            if user:
                                st.session_state.logged_in = True
                                st.session_state.username = new_email
                                st.session_state.user_id = user.uid
                                st.session_state.auth_method = 'email'
                                st.success("Account created! Welcome to Jaypardy!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("Failed to create account. Email may already exist.")
                    else:
                        st.error("Please fill in all fields")
        
        with tab3:
            st.markdown("""
            <div style="text-align: center; padding: 20px;">
                <h3>🔷 Sign in with Google</h3>
                <p>Quick and secure authentication</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Two options for Google Sign-In
            st.markdown("### Option 1: Use Authentication Token")
            
            with st.expander("Get Google Auth Token", expanded=True):
                st.markdown("""
                1. **[Click here to sign in with Google](https://jaypardy-53a55.web.app/google_auth_helper.html)** 
                   (Opens in new tab)
                2. Sign in with your Google account
                3. Copy the token that appears
                4. Paste it below
                """)
                
                auth_token = st.text_input(
                    "Paste your authentication token:",
                    type="password",
                    placeholder="Paste token here",
                    key="google_token"
                )
                
                if st.button("🔷 Sign In with Token", use_container_width=True, key="google_token_btn"):
                    if auth_token:
                        try:
                            # Verify the token
                            helper = FirebaseAuthHelper()
                            user_data = helper.verify_firebase_token(auth_token)
                            if user_data:
                                st.session_state.logged_in = True
                                st.session_state.username = user_data.get('email', 'User')
                                st.session_state.user_id = user_data.get('uid')
                                st.session_state.auth_method = 'google'
                                st.success(f"Welcome, {user_data.get('name', st.session_state.username)}!")
                                st.rerun()
                            else:
                                st.error("Invalid token. Please try again.")
                        except Exception as e:
                            st.error(f"Authentication failed: {str(e)}")
                    else:
                        st.warning("Please paste your authentication token")
            
            st.markdown("### Option 2: Quick Demo")
            
            # Demo Google Sign-In
            if st.button("🎮 Try Demo Mode", use_container_width=True, key="google_demo"):
                st.session_state.logged_in = True
                st.session_state.username = f"demo_{random.randint(1000, 9999)}@demo.com"
                st.session_state.user_id = "demo_" + str(random.randint(10000, 99999))
                st.session_state.auth_method = 'google'
                st.success("Signed in with demo Google account!")
                st.rerun()
        
        # Footer
        st.markdown("---")
        st.markdown("### 📚 Did you know?")
        facts = [
            "Jeopardy! has been on air since 1984",
            "Over 400,000 questions have been asked on Jeopardy!",
            "The highest single-day winnings record is $131,127",
            "Ken Jennings won 74 consecutive games",
            "The show has won 39 Emmy Awards"
        ]
        st.info(random.choice(facts))

# Main Game UI
def show_game():
    """Display the main game interface"""
    username = st.session_state.username
    auth_method = st.session_state.get('auth_method', 'local')
    
    # Sidebar
    with st.sidebar:
        st.title(f"👤 {username}")
        
        # Show auth method badge
        auth_badges = {
            'google': '🔷 Google Account',
            'email': '📧 Email Account',
            'guest': '👤 Guest Mode',
            'local': '💾 Local Account'
        }
        st.caption(auth_badges.get(auth_method, ''))
        
        # Load user data from Firestore if authenticated
        if auth_method in ['google', 'email'] and st.session_state.get('firebase_initialized'):
            firestore_manager = FirestoreManager()
            user_id = st.session_state.get('user_id', username)
            user_data = firestore_manager.load_user_data(user_id)
            if user_data:
                stats = user_data.get('stats', {})
            else:
                stats = {}
        else:
            stats = st.session_state.get('stats', {})
        
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
        
        # Account actions
        if auth_method == 'google':
            if st.button("🔷 Google Account Settings", use_container_width=True):
                st.info("Manage your Google account at accounts.google.com")
        
        if st.button("🚪 Logout", use_container_width=True):
            # Save stats before logout
            if st.session_state.get('firebase_initialized') and auth_method in ['google', 'email']:
                firestore_manager = FirestoreManager()
                user_id = st.session_state.get('user_id', username)
                firestore_manager.save_user_data(user_id, {
                    'stats': stats,
                    'last_seen': firestore.SERVER_TIMESTAMP
                })
            
            # Clear session
            for key in list(st.session_state.keys()):
                if key not in ['firebase_initialized', 'db']:
                    del st.session_state[key]
            st.rerun()
    
    # Main content
    st.title("🎯 Jaypardy! Training")
    
    # Add authentication status
    if auth_method == 'google':
        st.success("🔷 Signed in with Google - Progress auto-saved to cloud", icon="✅")
    elif auth_method == 'guest':
        st.warning("👤 Guest Mode - Progress not saved", icon="⚠️")
    
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
        st.session_state.stats = stats
    
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
                        if 'stats' not in st.session_state:
                            st.session_state.stats = {}
                        
                        stats = st.session_state.stats
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
                        
                        # Calculate accuracy
                        if stats['total_questions'] > 0:
                            stats['accuracy'] = (stats['correct_answers'] / stats['total_questions']) * 100
                        
                        # Save to Firestore if using Google/Email auth
                        if st.session_state.get('firebase_initialized') and auth_method in ['google', 'email']:
                            firestore_manager = FirestoreManager()
                            user_id = st.session_state.get('user_id', username)
                            firestore_manager.save_user_data(user_id, {'stats': stats})
                        
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