"""
Authentication and user session management for Jeopardy Trainer
"""
import streamlit as st
import json
import os
import datetime
import hashlib
import pickle
from pathlib import Path

# For Google OAuth
try:
    from streamlit_oauth import OAuth2Component
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False
    st.warning("OAuth not installed. Run: pip install streamlit-oauth")

class AuthManager:
    def __init__(self):
        self.users_dir = Path("user_data")
        self.users_dir.mkdir(exist_ok=True)
        
        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_email' not in st.session_state:
            st.session_state.user_email = None
        if 'user_name' not in st.session_state:
            st.session_state.user_name = None
    
    def get_user_id(self, email):
        """Generate a unique user ID from email"""
        return hashlib.md5(email.encode()).hexdigest()
    
    def save_user_session(self):
        """Save current session data for the user"""
        if not st.session_state.authenticated:
            return
        
        # Don't save for guest users
        if st.session_state.get('is_guest', False):
            return
        
        user_id = self.get_user_id(st.session_state.user_email)
        session_file = self.users_dir / f"{user_id}_session.json"
        
        # Prepare session data
        session_data = {
            'email': st.session_state.user_email,
            'name': st.session_state.user_name,
            'last_login': datetime.datetime.now().isoformat(),
            'history': st.session_state.get('history', []),
            'score': st.session_state.get('score', 0),
            'total': st.session_state.get('total', 0),
            'weak_categories': st.session_state.get('weak_categories', {}),
            'strong_categories': st.session_state.get('strong_categories', {}),
            'settings': {
                'use_timer': st.session_state.get('use_timer', False),
                'timer_seconds': st.session_state.get('timer_seconds', 5),
                'adaptive_mode': st.session_state.get('adaptive_mode', False)
            }
        }
        
        # Save to file
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
    
    def load_user_session(self):
        """Load saved session data for the user"""
        if not st.session_state.authenticated:
            return False
        
        user_id = self.get_user_id(st.session_state.user_email)
        session_file = self.users_dir / f"{user_id}_session.json"
        
        if not session_file.exists():
            return False
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Restore session state
            st.session_state.history = session_data.get('history', [])
            st.session_state.score = session_data.get('score', 0)
            st.session_state.total = session_data.get('total', 0)
            st.session_state.weak_categories = session_data.get('weak_categories', {})
            st.session_state.strong_categories = session_data.get('strong_categories', {})
            
            # Restore settings
            settings = session_data.get('settings', {})
            st.session_state.use_timer = settings.get('use_timer', False)
            st.session_state.timer_seconds = settings.get('timer_seconds', 5)
            st.session_state.adaptive_mode = settings.get('adaptive_mode', False)
            
            return True
        except Exception as e:
            st.error(f"Error loading session: {e}")
            return False
    
    def simple_email_login(self):
        """Simple email/password login (for demo purposes)"""
        st.markdown("### 📧 Sign In")
        
        with st.form("email_login_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            col1, col2 = st.columns(2)
            
            with col1:
                submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            with col2:
                register = st.form_submit_button("Register", use_container_width=True)
        
        if submit and email:
            # For demo: accept any email/password combo
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.session_state.user_name = email.split('@')[0]
            
            # Try to load existing session
            if self.load_user_session():
                st.success(f"Welcome back, {st.session_state.user_name}! Your progress has been restored.")
            else:
                st.success(f"Welcome, {st.session_state.user_name}!")
            
            st.rerun()
        
        elif register and email:
            # Register new user
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.session_state.user_name = email.split('@')[0]
            st.success(f"Account created! Welcome, {st.session_state.user_name}!")
            st.rerun()
    
    def simple_login(self):
        """Backward compatibility - redirects to simple_email_login"""
        return self.simple_email_login()
    
    def google_oauth_login(self):
        """Google OAuth login"""
        if not OAUTH_AVAILABLE:
            st.error("OAuth component not installed. Contact app administrator.")
            return
        
        # Google OAuth configuration - check if secrets exist
        try:
            # Debug: Check what secrets are available
            if hasattr(st, 'secrets'):
                # Try different ways to access secrets
                try:
                    CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
                    CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
                    REDIRECT_URI = st.secrets.get("REDIRECT_URI", "https://jayopardy.streamlit.app")
                except KeyError as ke:
                    st.error(f"Missing secret: {ke}")
                    st.info("Available secrets keys: " + str(list(st.secrets.keys()) if hasattr(st.secrets, 'keys') else "None"))
                    st.info("Please add the following to Streamlit Cloud Secrets:")
                    st.code("""GOOGLE_CLIENT_ID = "your-client-id"
GOOGLE_CLIENT_SECRET = "your-secret"
REDIRECT_URI = "https://jayopardy.streamlit.app" """)
                    return
                
                if not CLIENT_ID or not CLIENT_SECRET:
                    st.warning("OAuth credentials are empty. Please check Streamlit Cloud settings.")
                    return
            else:
                st.info("For local testing, use email login. Google Sign-In requires Streamlit Cloud deployment.")
                return
        except Exception as e:
            st.error(f"Error accessing secrets: {str(e)}")
            st.info("Use email login for now.")
            return
        
        # Create OAuth component
        oauth2 = OAuth2Component(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
            refresh_token_endpoint="https://oauth2.googleapis.com/token",
            revoke_token_endpoint="https://oauth2.googleapis.com/revoke",
        )
        
        # Check if we have a token
        # Use the component redirect URI for Streamlit Cloud
        component_redirect_uri = "https://share.streamlit.io/component/streamlit_oauth.authorize_button/index.html"
        
        result = oauth2.authorize_button(
            name="Continue with Google",
            icon="https://www.google.com/favicon.ico",
            redirect_uri=component_redirect_uri,
            scope="openid email profile",
            key="google_login",
            extras_params={"prompt": "select_account", "access_type": "offline"},
            use_container_width=True,
        )
        
        if result:
            # Decode token to get user info
            token = result.get("token")
            if token:
                import jwt
                user_info = jwt.decode(token["id_token"], options={"verify_signature": False})
                
                st.session_state.authenticated = True
                st.session_state.user_email = user_info.get("email")
                st.session_state.user_name = user_info.get("name", user_info.get("email", "").split('@')[0])
                
                # Load existing session
                if self.load_user_session():
                    st.success(f"Welcome back, {st.session_state.user_name}!")
                else:
                    st.success(f"Welcome, {st.session_state.user_name}!")
                
                st.rerun()
    
    def show_login_page(self):
        """Display the login page"""
        st.title("🧠 Jayopardy! Trainer")
        st.markdown("### Welcome! Choose how to play:")
        
        # Three tabs for different entry methods
        tab1, tab2, tab3 = st.tabs(["🎮 Play as Guest", "📧 Email Login", "🔐 Google Sign-In"])
        
        with tab1:
            st.markdown("### 🎮 Quick Play")
            st.info("Jump right in without creating an account!")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                **✅ What you get:**
                - Full access to all questions
                - Timer and adaptive mode
                - Session statistics
                - All game features
                """)
            with col2:
                st.markdown("""
                **⚠️ Limitations:**
                - Progress not saved
                - No lifetime stats
                - Resets when you leave
                """)
            
            if st.button("🎮 Play as Guest", type="primary", use_container_width=True, key="guest_play"):
                # Set up guest session
                st.session_state.authenticated = True
                st.session_state.is_guest = True
                st.session_state.user_email = "guest@jayopardy.app"
                st.session_state.user_name = "Guest Player"
                st.success("Starting game... Have fun!")
                st.rerun()
        
        with tab2:
            self.simple_email_login()
        
        with tab3:
            st.markdown("### 🔐 Secure Google Sign-In")
            st.info("Sign in with your Google account for the best experience")
            self.google_oauth_login()
        
        # Benefits of signing in
        st.markdown("---")
        st.markdown("### Why sign in?")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**💾 Save Progress**")
            st.caption("Your scores and history are saved automatically")
        with col2:
            st.markdown("**📊 Track Performance**")
            st.caption("See your improvement over time")
        with col3:
            st.markdown("**🎯 Personalized Training**")
            st.caption("Adaptive mode learns your weak areas")
    
    def logout(self):
        """Logout the current user"""
        # Save session before logging out
        self.save_user_session()
        
        # Clear authentication
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_name = None
        
        # Clear game state
        for key in ['history', 'score', 'total', 'current_clue', 'weak_categories', 'strong_categories']:
            if key in st.session_state:
                del st.session_state[key]
        
        st.rerun()
    
    def show_user_menu(self):
        """Show user menu in sidebar"""
        with st.sidebar:
            st.markdown("---")
            
            # Check if guest user
            if st.session_state.get('is_guest', False):
                st.markdown(f"**🎮 {st.session_state.user_name}**")
                st.caption("Playing without account")
                st.warning("⚠️ Progress not saved")
                
                if st.button("📝 Create Account", use_container_width=True, type="primary"):
                    # Clear guest session and show login
                    st.session_state.authenticated = False
                    st.session_state.is_guest = False
                    st.rerun()
            else:
                st.markdown(f"**👤 {st.session_state.user_name}**")
                st.caption(f"📧 {st.session_state.user_email}")
                
                # Save button prominently displayed
                if st.button("💾 Save Progress", use_container_width=True, type="primary"):
                    self.save_user_session()
                    st.success("✅ Progress saved!")
            
            # Session management
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 New Session", use_container_width=True):
                    # Save current progress first
                    self.save_user_session()
                    # Reset current session but keep history
                    st.session_state.score = 0
                    st.session_state.total = 0
                    st.session_state.current_clue = None
                    st.session_state.start_time = datetime.datetime.now()
                    st.success("New session started!")
                    st.rerun()
            
            with col2:
                if st.button("🚪 Logout", use_container_width=True):
                    self.logout()