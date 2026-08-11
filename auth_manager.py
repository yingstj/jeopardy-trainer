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

# For Google OAuth — lazy import to keep server cold-start fast
OAUTH_AVAILABLE = True
OAuth2Component = None

def _ensure_oauth():
    global OAuth2Component, OAUTH_AVAILABLE
    if OAuth2Component is not None:
        return True
    try:
        from streamlit_oauth import OAuth2Component as _OAuth2
        OAuth2Component = _OAuth2
        return True
    except ImportError:
        OAUTH_AVAILABLE = False
        return False

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
        if not _ensure_oauth():
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
        /* Login page — Bold Jeopardy Energy */
        .logo-container { text-align: center; margin-bottom: 2.2rem; padding-top: 1.5rem; }
        .logo {
            display: inline-block;
            font-family: 'Fraunces', Georgia, serif;
            font-size: 52px;
            font-style: normal;
            font-weight: 600;
            color: #e5b94f;
            letter-spacing: -0.06em;
            text-shadow: 0 4px 24px rgba(229,185,79,.22);
            margin-bottom: 0.4rem;
            line-height: 1;
        }
        .logo-rule {
            width: 44px; height: 3px;
            background: #e5b94f;
            margin: 0.85rem auto 1rem;
        }
        .login-title {
            font-family: 'Fraunces', Georgia, serif !important;
            font-size: 3.15rem !important;
            font-weight: 500 !important;
            font-style: normal;
            color: #f7f4ea !important;
            margin: 0 !important;
            letter-spacing: -0.02em;
        }
        .login-subtitle {
            color: #a7aec6 !important;
            font-size: 0.92rem !important;
            margin-top: 0.4rem !important;
            font-style: italic;
        }

        /* Guest play hero — quiet card */
        .guest-card {
            background: linear-gradient(145deg, #172154, #0f163c);
            color: #f7f4ea;
            padding: 1.7rem 1.8rem;
            border-radius: 10px;
            margin: 1.25rem 0 1rem;
            border: 1px solid #39457c;
            position: relative;
        }
        .guest-card::before {
            content: ""; position: absolute;
            left: 1.8rem; top: -1px;
            width: 32px; height: 2px;
            background: #e5b94f;
        }
        .guest-card h3 {
            color: #f7f4ea !important;
            margin-top: 0; margin-bottom: 0.4rem;
            font-family: 'Fraunces', Georgia, serif !important;
            font-weight: 400 !important;
            font-style: normal;
            font-size: 1.5rem;
            letter-spacing: -0.01em;
        }
        .guest-card p {
            color: #a7aec6;
            margin-bottom: 0;
            font-size: 0.95rem;
            line-height: 1.55;
        }

        /* Info / warn boxes */
        .info-box {
            background: rgba(17,25,68,.58);
            border: 1px solid #293363;
            border-top: 2px solid #e5b94f;
            border-radius: 8px;
            padding: 1rem 0.25rem 0.5rem;
            color: #f7f4ea;
            margin-bottom: 0.5rem;
        }
        .info-box.warn { }
        .info-box .ib-title {
            font-family: 'Space Mono', monospace;
            font-weight: 600;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            margin-bottom: 0.6rem;
            color: #a7aec6;
        }
        .info-box.warn .ib-title { color: #e5b94f; }
        .info-box ul {
            margin: 0; padding-left: 1.1rem;
            color: #d9d5c8; line-height: 1.7;
            font-size: 0.92rem;
        }
        .info-box ul li::marker { color: #e5b94f; }

        /* Benefit cards */
        .benefit-card {
            background: rgba(17,25,68,.42);
            border: 1px solid #293363;
            border-top: 2px solid #293363;
            padding: 1.5rem 0.5rem 0.5rem;
            text-align: center;
            margin-bottom: 1rem;
            position: relative;
            transition: opacity 0.18s ease;
        }
        .benefit-card:hover { opacity: 0.7; }
        .benefit-card h3 {
            color: #f7f4ea !important;
            margin: 0.5rem 0 0.4rem;
            font-family: 'Fraunces', Georgia, serif !important;
            font-size: 1.15rem;
            font-style: normal;
            font-weight: 400;
        }
        .benefit-card p {
            color: #a7aec6 !important;
            margin: 0;
            font-size: 0.88rem;
            line-height: 1.5;
        }
        .benefit-icon {
            display: inline-block;
            font-family: 'Fraunces', Georgia, serif;
            font-size: 0.72rem;
            color: #e5b94f;
            letter-spacing: 0.25em;
            text-transform: uppercase;
            font-weight: 600;
        }

        /* Why-account heading */
        .why-heading {
            color: #f7f4ea;
            text-align: center;
            font-family: 'Fraunces', Georgia, serif !important;
            font-style: normal;
            font-weight: 400 !important;
            font-size: 1.4rem;
            margin: 2.5rem 0 1.25rem;
            letter-spacing: -0.01em;
        }
        </style>
        """, unsafe_allow_html=True)

        # Logo and title
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="logo-container">
                <div class="logo">J!</div>
                <div class="logo-rule"></div>
                <h1 class="login-title">Jayopardy</h1>
                <p class="login-subtitle">A quiz, considered.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Create three columns for centered content
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col2:
            tab1, tab2 = st.tabs(["Guest Play", "Email Login"])
            
            with tab1:
                st.markdown("""
                <div class="guest-card">
                    <h3>Quick play, no account needed.</h3>
                    <p>Jump straight into the game. Perfect for trying out Jayopardy.</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("""
                    <div class="info-box">
                        <div class="ib-title">Included</div>
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
                        <div class="ib-title">Note</div>
                        <ul>
                            <li>Progress not saved</li>
                            <li>No lifetime stats</li>
                            <li>Resets on exit</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Play as Guest", type="primary", use_container_width=True, key="guest_play"):
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
                    st.markdown("<div style='margin: 1.25rem 0 0.5rem;'></div>", unsafe_allow_html=True)
                    email = st.text_input("Email", placeholder="your@email.com", key="email_input")
                    password = st.text_input("Password", type="password", placeholder="••••••••", key="password_input")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        remember = st.checkbox("Remember me")
                    with col_b:
                        st.markdown("<a href='#' style='float: right; color: #e5b94f; font-size: 0.88rem; text-decoration: none;'>Forgot password?</a>", unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    col_1, col_2 = st.columns(2)
                    with col_1:
                        submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                    with col_2:
                        register = st.form_submit_button("Sign Up", use_container_width=True)
                
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
            
        # Benefits section
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h3 class='why-heading'>Why create an account</h3>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="benefit-card">
                <div class="benefit-icon">I.</div>
                <h3>Saved progress</h3>
                <p>Your scores and history are saved automatically.</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="benefit-card">
                <div class="benefit-icon">II.</div>
                <h3>Tracked stats</h3>
                <p>See your improvement over time with detailed analytics.</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="benefit-card">
                <div class="benefit-icon">III.</div>
                <h3>Smart training</h3>
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
        
        # Clear access state so next login re-checks
        st.session_state.is_signed_in = False
        
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