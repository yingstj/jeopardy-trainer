"""
Authentication and user session management for Jeopardy Trainer
"""
import streamlit as st
import json
import os
import datetime
import time
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
                    st.info("Please add the following to Streamlit Secrets (Cloud or .streamlit/secrets.toml locally):")
                    st.code("""# .streamlit/secrets.toml
GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "your-client-secret"
# Local dev:
REDIRECT_URI = "http://localhost:8501"
# Streamlit Cloud (optional override):
# REDIRECT_URI = "https://your-app.streamlit.app"
""")
                    st.caption("See AUTH_SETUP.md for step-by-step instructions.")
                    return
                
                if not CLIENT_ID or not CLIENT_SECRET:
                    st.warning("OAuth credentials are empty. Please check Streamlit Secrets.")
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
        # Custom CSS for beautiful login page
        st.markdown("""
        <style>
        /* Logo */
        .logo-container { text-align: center; margin-bottom: 1.25rem; }
        .logo {
            width: 88px; height: 88px;
            background: #0f172a;
            border-radius: 20px;
            display: inline-flex; align-items: center; justify-content: center;
            font-size: 38px; color: #f59e0b; margin: 0 auto 14px;
            box-shadow: 0 10px 24px -8px rgba(15, 23, 42, 0.35);
            font-weight: 800; font-family: 'Poppins', sans-serif;
            letter-spacing: -0.02em;
        }

        /* Guest play hero card */
        .guest-card {
            background: #0f172a;
            color: #ffffff;
            padding: 1.5rem 1.6rem;
            border-radius: 14px;
            margin-bottom: 1rem;
            border: 1px solid #0f172a;
            border-left: 4px solid #f59e0b;
            box-shadow: 0 10px 24px -12px rgba(15, 23, 42, 0.35);
        }
        .guest-card h3 { color: #ffffff !important; margin-top: 0; font-weight: 700; }
        .guest-card p { color: rgba(255,255,255,0.78); margin-bottom: 0; }

        /* Soft info / warn boxes inside guest tab */
        .info-box {
            background: #ffffff;
            border: 1px solid #e7e5e4;
            border-left: 4px solid #0f172a;
            border-radius: 12px;
            padding: 0.9rem 1rem;
            box-shadow: 0 1px 2px rgba(15,23,42,0.04);
            color: #0f172a;
            margin-bottom: 0.5rem;
        }
        .info-box.warn { border-left-color: #f59e0b; }
        .info-box .ib-title {
            font-weight: 700; margin-bottom: 0.35rem;
            color: #0f172a; letter-spacing: 0.01em;
        }
        .info-box.warn .ib-title { color: #92400e; }
        .info-box ul { margin: 0; padding-left: 1.1rem; color: #475569; line-height: 1.55; }

        /* Benefit cards */
        .benefit-card {
            background: #ffffff;
            border: 1px solid #e7e5e4;
            padding: 1.25rem;
            border-radius: 14px;
            box-shadow: 0 1px 2px rgba(15,23,42,0.04);
            text-align: center;
            margin-bottom: 1rem;
            transition: transform 0.16s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }
        .benefit-card:hover {
            transform: translateY(-2px);
            border-color: #d6d3d1;
            box-shadow: 0 8px 20px -12px rgba(15,23,42,0.18);
        }
        .benefit-card h3 { color: #0f172a !important; margin: 0 0 0.35rem 0; font-size: 1.05rem; font-weight: 700; }
        .benefit-card p { color: #64748b !important; margin: 0; font-size: 0.92rem; }
        .benefit-icon {
            width: 44px; height: 44px; border-radius: 12px;
            margin: 0 auto 0.6rem;
            display: inline-flex; align-items: center; justify-content: center;
            font-size: 22px;
            background: #fef3c7;
            color: #92400e;
        }

        /* Why-account heading */
        .why-heading {
            color: #0f172a; text-align: center;
            font-family: 'Poppins', sans-serif; font-weight: 700;
            margin: 1.5rem 0 1rem;
        }
        </style>
        """, unsafe_allow_html=True)

        # Logo and title
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="logo-container">
                <div class="logo">J!</div>
                <h1 style='color: #333; font-size: 32px; margin: 0;'>Jayopardy!</h1>
                <p style='color: #666; font-size: 16px; margin-top: 0.5rem;'>Test your knowledge, track your progress</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Create three columns for centered content
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col2:
            # Add container background for better readability
            st.markdown('<div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 20px;">', unsafe_allow_html=True)
            # Tabs for login options
            tab1, tab2 = st.tabs(["🎮 Guest Play", "📧 Email Login"])
            
            with tab1:
                st.markdown("""
                <div class="guest-card">
                    <h3 style='margin-top: 0;'>🎮 Quick Play - No Account Needed!</h3>
                    <p>Jump right into the game without signing up. Perfect for trying out Jayopardy!</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("""
                    <div class="info-box">
                        <div class="ib-title">✅ Includes</div>
                        <ul>
                            <li>All 577,000+ questions</li>
                            <li>Timer &amp; adaptive mode</li>
                            <li>Session statistics</li>
                            <li>All game features</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    st.markdown("""
                    <div class="info-box warn">
                        <div class="ib-title">⚠️ Note</div>
                        <ul>
                            <li>Progress not saved</li>
                            <li>No lifetime stats</li>
                            <li>Resets on exit</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                if st.button("🎮 Play as Guest", type="primary", use_container_width=True, key="guest_play"):
                    st.session_state.authenticated = True
                    st.session_state.is_guest = True
                    st.session_state.user_email = "guest@jayopardy.app"
                    st.session_state.user_name = "Guest Player"
                    st.balloons()
                    st.success("🎉 Starting game... Have fun!")
                    time.sleep(1)
                    st.rerun()
            
            with tab2:
                with st.form("email_login_form", clear_on_submit=False):
                    st.markdown("### 📧 Sign in with Email")
                    email = st.text_input("Email Address", placeholder="your@email.com", key="email_input")
                    password = st.text_input("Password", type="password", placeholder="Enter your password", key="password_input")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        remember = st.checkbox("Remember me")
                    with col_b:
                        st.markdown("<a href='#' style='float: right; color: #667eea;'>Forgot password?</a>", unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    col_1, col_2 = st.columns(2)
                    with col_1:
                        submit = st.form_submit_button("🔐 Sign In", use_container_width=True, type="primary")
                    with col_2:
                        register = st.form_submit_button("✨ Sign Up", use_container_width=True)
                
                if submit and email:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.user_name = email.split('@')[0]
                    st.session_state.is_guest = False
                    
                    if self.load_user_session():
                        st.success(f"👋 Welcome back, {st.session_state.user_name}!")
                    else:
                        st.success(f"🎉 Welcome, {st.session_state.user_name}!")
                    time.sleep(1)
                    st.rerun()
                
                elif register and email:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.user_name = email.split('@')[0]
                    st.session_state.is_guest = False
                    st.balloons()
                    st.success(f"🎊 Account created! Welcome, {st.session_state.user_name}!")
                    time.sleep(1)
                    st.rerun()
            
            # Close container div
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Benefits section
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h3 class='why-heading'>🌟 Why Create an Account?</h3>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="benefit-card">
                <div class="benefit-icon">💾</div>
                <h3>Save Progress</h3>
                <p>Your scores and history are saved automatically.</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="benefit-card">
                <div class="benefit-icon">📊</div>
                <h3>Track Stats</h3>
                <p>See your improvement over time with detailed analytics.</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="benefit-card">
                <div class="benefit-icon">🎯</div>
                <h3>Smart Training</h3>
                <p>Adaptive mode learns and focuses on your weak areas.</p>
            </div>
            """, unsafe_allow_html=True)
    
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
            
            # Session management - only show logout for logged-in users
            if st.session_state.get('is_guest', False):
                # Guest user only gets new session button
                if st.button("🔄 New Session", use_container_width=True):
                    # Reset current session
                    st.session_state.score = 0
                    st.session_state.total = 0
                    st.session_state.current_clue = None
                    st.session_state.start_time = datetime.datetime.now()
                    st.success("New session started!")
                    st.rerun()
            else:
                # Logged-in user gets both buttons
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