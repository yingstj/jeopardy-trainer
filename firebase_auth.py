"""Firebase authentication module for Jaypardy application."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import firebase_admin
from firebase_admin import auth, credentials
import os
import logging
from firebase_config import get_firebase_admin_config, get_firebase_config
from database import JeopardyDatabase
from firestore_integration import firestore_manager

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    cred_dict = get_firebase_admin_config()
    if cred_dict.get("private_key"):
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    else:
        # Use default credentials if no service account is configured
        firebase_admin.initialize_app()
    logger.info("Firebase Admin SDK initialized successfully")
except Exception as e:
    logger.warning(f"Firebase Admin SDK initialization failed: {e}. Some features may be limited.")
    firebase_admin.initialize_app()

firebase_auth_bp = Blueprint('firebase_auth', __name__)
db = JeopardyDatabase()

def firebase_login_required(f):
    """Decorator to require Firebase authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'firebase_user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('firebase_auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@firebase_auth_bp.route('/firebase_config')
def firebase_config():
    """Provide Firebase configuration to client."""
    return jsonify(get_firebase_config())

@firebase_auth_bp.route('/login')
def login():
    """Firebase login page."""
    return render_template('firebase_login.html')

@firebase_auth_bp.route('/register')
def register():
    """Firebase registration page."""
    return render_template('firebase_register.html')

@firebase_auth_bp.route('/verify_token', methods=['POST'])
def verify_token():
    """Verify Firebase ID token from client."""
    try:
        data = request.get_json()
        id_token = data.get('idToken')
        
        if not id_token:
            return jsonify({'success': False, 'error': 'No token provided'}), 400
        
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        name = decoded_token.get('name', email.split('@')[0] if email else f'user_{uid[:8]}')
        
        # Check if user exists in our database
        user = db.get_user_by_email(email) if email else None
        
        if not user:
            # Create new user in our database
            username = email.split('@')[0] if email else f'user_{uid[:8]}'
            # Firebase handles password, so we store a placeholder
            user_id = db.create_user(username, email, f'firebase_user_{uid}')
            user = db.get_user_by_id(user_id)
            
            # Also create Firestore profile for cloud persistence
            firestore_manager.create_user_profile(uid, username, email or '')
        
        # Set session variables
        session['firebase_user'] = {
            'uid': uid,
            'email': email,
            'name': name
        }
        session['user_id'] = user['id']
        session['username'] = user['username']
        
        # Create session in database
        if 'session_id' not in session:
            session['session_id'] = os.urandom(16).hex()
        db.create_session(session['session_id'], user['id'])
        
        return jsonify({
            'success': True,
            'user': {
                'uid': uid,
                'email': email,
                'name': name
            }
        })
        
    except auth.InvalidIdTokenError as e:
        logger.error(f"Invalid ID token: {e}")
        return jsonify({'success': False, 'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@firebase_auth_bp.route('/logout', methods=['POST'])
def logout():
    """Firebase logout endpoint."""
    username = session.get('username', 'User')
    session.clear()
    return jsonify({
        'success': True,
        'message': f'Goodbye, {username}! You have been logged out.'
    })

@firebase_auth_bp.route('/profile')
@firebase_login_required
def profile():
    """User profile page with Firebase auth."""
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('firebase_auth.logout'))
    
    # Get user statistics
    stats = db.get_session_stats(session.get('session_id', ''))
    progress = db.get_progress_over_time(session.get('session_id', ''), days=30)
    
    # Add Firebase user info
    firebase_user = session.get('firebase_user', {})
    
    return render_template('firebase_profile.html', 
                         user=user,
                         firebase_user=firebase_user,
                         stats=stats,
                         progress=progress)

@firebase_auth_bp.route('/update_profile', methods=['POST'])
@firebase_login_required
def update_profile():
    """Update user profile information."""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # Update display name if provided
        if 'displayName' in data:
            # Update in our database
            with db.get_connection() as conn:
                conn.execute(
                    'UPDATE users SET username = ? WHERE id = ?',
                    (data['displayName'], user_id)
                )
                conn.commit()
            session['username'] = data['displayName']
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500