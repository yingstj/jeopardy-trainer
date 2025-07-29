from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import re
import os
from database import JeopardyDatabase

auth_bp = Blueprint('auth', __name__)
db = JeopardyDatabase()

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        
        if not email or not validate_email(email):
            errors.append("Please enter a valid email address")
        
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        valid_password, password_msg = validate_password(password)
        if not valid_password:
            errors.append(password_msg)
        
        # Check if username or email already exists
        if db.get_user_by_username(username):
            errors.append("Username already exists")
        
        if db.get_user_by_email(email):
            errors.append("Email already registered")
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', 
                                 username=username, 
                                 email=email)
        
        # Create user
        password_hash = generate_password_hash(password)
        user_id = db.create_user(username, email, password_hash)
        
        if user_id:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        user = db.get_user_by_username(username)
        
        if user and check_password_hash(user['password_hash'], password):
            # Login successful
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            # Create new session for this user
            if 'session_id' not in session:
                session['session_id'] = os.urandom(16).hex()
            db.create_session(session['session_id'], user['id'])
            
            # Handle remember me
            if remember:
                session.permanent = True
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}! You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Get user statistics
    stats = db.get_session_stats(session.get('session_id', ''))
    progress = db.get_progress_over_time(session.get('session_id', ''), days=30)
    
    return render_template('profile.html', 
                         user=user, 
                         stats=stats,
                         progress=progress)

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    user_id = session.get('user_id')
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    user = db.get_user_by_id(user_id)
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Verify current password
    if not check_password_hash(user['password_hash'], current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Validate new password
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('auth.profile'))
    
    valid_password, password_msg = validate_password(new_password)
    if not valid_password:
        flash(password_msg, 'danger')
        return redirect(url_for('auth.profile'))
    
    # Update password
    new_password_hash = generate_password_hash(new_password)
    with db.get_connection() as conn:
        conn.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (new_password_hash, user_id)
        )
        conn.commit()
    
    flash('Password changed successfully', 'success')
    return redirect(url_for('auth.profile'))