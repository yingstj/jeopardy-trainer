from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
import json
import os
import random
from datetime import datetime, timedelta
import sqlite3
import logging
from auth import auth_bp, login_required
from firebase_auth import firebase_auth_bp, firebase_login_required
from database import JeopardyDatabase
from ai_engine import AdaptiveLearningEngine
from answer_checker import AnswerChecker

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')  # Change this to a secure random key
app.permanent_session_lifetime = timedelta(days=7)

# Register authentication blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(firebase_auth_bp, url_prefix='/firebase_auth')

# Database setup - use DATABASE_URL if available for Railway deployment
db_url = os.environ.get('DATABASE_URL')
db = JeopardyDatabase(db_url)
ai_engine = AdaptiveLearningEngine()
answer_checker = AnswerChecker()

# Database initialization is handled by JeopardyDatabase class

@app.route('/landing')
def landing():
    """Public landing page."""
    if session.get('user_id') or session.get('firebase_user'):
        return redirect(url_for('index'))
    # Redirect to Firebase login by default
    return redirect(url_for('firebase_auth.login'))

@app.route('/')
def index():
    """Serve the main Jeopardy trainer page."""
    # Check for either traditional or Firebase authentication
    if not session.get('user_id') and not session.get('firebase_user'):
        return redirect(url_for('firebase_auth.login'))
    
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
        user_id = session.get('user_id')
        if user_id:
            db.create_session(session['session_id'], user_id)
    return render_template('jeopardy_simple.html')

@app.route('/api/questions')
def get_questions():
    """Get questions based on filters."""
    category = request.args.get('category')
    count = int(request.args.get('count', 10))
    difficulty = request.args.get('difficulty')  # easy, medium, hard based on value
    
    questions = db.get_questions(
        category=category,
        difficulty=difficulty,
        count=count,
        exclude_recent=session.get('session_id')
    )
    
    return jsonify(questions)

@app.route('/api/categories')
@login_required
def get_categories():
    """Get all available categories."""
    categories = db.get_categories()
    return jsonify([{'name': cat[0], 'count': cat[1]} for cat in categories])

@app.route('/api/check-answer', methods=['POST'])
@login_required
def check_answer():
    """Check user's answer with fuzzy matching."""
    data = request.json
    user_answer = data.get('user_answer', '').strip()
    correct_answer = data.get('correct_answer', '').strip()
    
    if not user_answer or not correct_answer:
        return jsonify({
            'is_correct': False,
            'feedback': 'Please provide an answer'
        })
    
    # Check answer with fuzzy matching
    is_correct, confidence, reason = answer_checker.check_answer(user_answer, correct_answer)
    feedback = answer_checker.get_feedback(user_answer, correct_answer, is_correct, confidence, reason)
    
    return jsonify({
        'is_correct': is_correct,
        'confidence': confidence,
        'reason': reason,
        'feedback': feedback
    })

@app.route('/api/progress', methods=['POST'])
@login_required
def save_progress():
    """Save user's answer and progress."""
    data = request.json
    session_id = session.get('session_id')
    user_id = session.get('user_id')
    
    if not session_id or not user_id:
        return jsonify({'error': 'No session found'}), 400
    
    # Use fuzzy matching if user_answer is provided
    if 'user_answer' in data and 'correct_answer' in data:
        user_answer = data['user_answer'].strip()
        correct_answer = data['correct_answer'].strip()
        is_correct, confidence, reason = answer_checker.check_answer(user_answer, correct_answer)
        data['is_correct'] = is_correct
    
    db.save_answer(
        user_id=user_id,
        session_id=session_id,
        question_id=data['question_id'],
        user_answer=data.get('user_answer', ''),
        is_correct=data['is_correct'],
        time_taken=data.get('time_taken')
    )
    
    return jsonify({'success': True})

@app.route('/api/stats')
@login_required
def get_stats():
    """Get user statistics for current session."""
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No session found'}), 400
    
    stats = db.get_session_stats(session_id)
    return jsonify(stats)

@app.route('/api/load_questions', methods=['POST'])
@login_required
def load_questions():
    """Load questions from JSON file into database."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        data = json.load(file)
        db = get_db()
        
        count = 0
        for item in data:
            db.execute('''
                INSERT INTO questions (category, question, answer, value, air_date, round, show_number)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('category', ''),
                item.get('question', ''),
                item.get('answer', ''),
                item.get('value', 0),
                item.get('air_date', ''),
                item.get('round', ''),
                item.get('show_number', 0)
            ))
            count += 1
        
        db.commit()
        return jsonify({'success': True, 'loaded': count})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/questions')
@login_required
def get_ai_questions():
    """Get AI-recommended questions based on user performance."""
    user_id = session.get('user_id')
    count = int(request.args.get('count', 30))  # Changed default to 30 for full board
    category = request.args.get('category')
    mode = request.args.get('mode', 'adaptive')
    
    try:
        questions = ai_engine.select_optimal_questions(
            user_id=user_id,
            count=count,
            category_filter=category,
            mode=mode
        )
        
        # Transform to match frontend format
        formatted_questions = []
        for q in questions:
            formatted = {
                'id': q['id'],
                'category': q['category'],
                'question': q['question'],
                'answer': q['answer'],
                'value': q['value'],
                'air_date': q['air_date'],
                'round': q['round'],
                'difficulty_rating': q.get('difficulty_rating', 5.0)
            }
            
            # Add AI metadata if available
            if 'ai_metadata' in q:
                formatted['ai_metadata'] = q['ai_metadata']
            
            formatted_questions.append(formatted)
        
        return jsonify({'questions': formatted_questions})  # Wrap in questions object
    
    except Exception as e:
        logger.error(f"Error getting AI questions: {e}")
        # Fallback to regular questions if AI fails
        questions = db.get_questions(count=count, category=category)
        return jsonify({'questions': questions})

@app.route('/api/ai/insights')
@login_required
def get_ai_insights():
    """Get AI-generated learning insights for the user."""
    user_id = session.get('user_id')
    
    try:
        insights = ai_engine.get_learning_insights(user_id)
        return jsonify(insights)
    
    except Exception as e:
        logger.error(f"Error getting AI insights: {e}")
        return jsonify({'error': 'Failed to get insights'}), 500

@app.route('/api/ai/update', methods=['POST'])
@login_required
def update_ai_parameters():
    """Update AI learning parameters based on user response."""
    user_id = session.get('user_id')
    data = request.json
    
    question_id = data.get('question_id')
    was_correct = data.get('was_correct')
    response_time = data.get('response_time', 0)
    
    if not question_id or was_correct is None:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        ai_engine.update_learning_parameters(
            user_id=user_id,
            question_id=question_id,
            was_correct=was_correct,
            response_time=response_time
        )
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Error updating AI parameters: {e}")
        return jsonify({'error': 'Failed to update AI parameters'}), 500

@app.errorhandler(401)
def unauthorized(e):
    """Redirect to login page for unauthorized access."""
    return redirect(url_for('auth.login'))

@app.route('/admin/fix-db')
@login_required
def fix_database():
    """Fix database by clearing bad questions and loading good ones."""
    try:
        # Security check
        if session.get('user_id') != 1:
            return "Access denied", 403
            
        result = "<h1>Database Fix</h1><pre>"
        
        # Clear bad questions
        result += "Clearing old questions with bad answers...\n"
        with db.get_connection() as conn:
            if db.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_progress')
                cursor.execute('DELETE FROM questions')
                conn.commit()
                cursor.close()
            else:
                conn.execute('DELETE FROM user_progress')
                conn.execute('DELETE FROM questions')
                conn.commit()
        
        result += "Old questions cleared\n\n"
        
        # Load new questions
        result += "Loading properly formatted questions...\n"
        count = db.load_questions_from_json('data/jeopardy_questions_fixed.json')
        result += f"Loaded {count} questions\n\n"
        
        # Verify
        questions = db.get_questions(count=5)
        result += "Sample questions:\n"
        for q in questions[:3]:
            result += f"- {q['category']}: {q['question'][:50]}...\n"
            result += f"  Answer: {q['answer']}\n\n"
        
        result += "</pre>"
        result += '<p><a href="/admin/db">View Database</a></p>'
        result += '<p><a href="/">Back to Game</a></p>'
        
        return result
        
    except Exception as e:
        return f"<h1>Error</h1><pre>{str(e)}</pre>", 500

@app.route('/admin/db')
@login_required
def db_viewer_overview():
    """Database viewer for checking database contents."""
    try:
        # Get database stats
        categories = db.get_categories()
        total_questions = sum(count for _, count in categories)
        
        # Get user count
        with db.get_connection() as conn:
            if db.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]
                cursor.close()
            else:
                user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        
        # Get sample questions
        sample_questions = db.get_questions(count=10)
        
        return f"""
        <html>
        <head>
            <title>Database Viewer</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .stat {{ background: #f0f0f0; padding: 10px; margin: 10px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>Jeopardy Database Viewer</h1>
            
            <div class="stat">
                <strong>Database Type:</strong> {db.db_type.upper()}<br>
                <strong>Total Questions:</strong> {total_questions}<br>
                <strong>Total Categories:</strong> {len(categories)}<br>
                <strong>Total Users:</strong> {user_count}
            </div>
            
            <h2>Top Categories</h2>
            <table>
                <tr><th>Category</th><th>Count</th></tr>
                {''.join(f'<tr><td>{cat}</td><td>{count}</td></tr>' for cat, count in categories[:10])}
            </table>
            
            <h2>Sample Questions</h2>
            <table>
                <tr><th>Category</th><th>Question</th><th>Answer</th><th>Value</th></tr>
                {''.join(f'<tr><td>{q["category"]}</td><td>{q["question"][:50]}...</td><td>{q["answer"]}</td><td>${q["value"]}</td></tr>' for q in sample_questions)}
            </table>
            
            <p><a href="/">Back to Game</a></p>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p><p>Database URL: {os.environ.get('DATABASE_URL', 'Not set')}</p>", 500

if __name__ == '__main__':
    # Database is automatically initialized by JeopardyDatabase class
    # Force Railway redeploy with env vars
    app.run(debug=True, port=5000)