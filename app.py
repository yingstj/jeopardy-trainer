from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
import json
import os
import random
from datetime import datetime, timedelta
import sqlite3
import logging
from auth import auth_bp, login_required
from database import JeopardyDatabase
from ai_engine import AdaptiveLearningEngine

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')  # Change this to a secure random key
app.permanent_session_lifetime = timedelta(days=7)

# Register authentication blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')

# Database setup - use DATABASE_URL if available for Railway deployment
db_url = os.environ.get('DATABASE_URL')
db = JeopardyDatabase(db_url)
ai_engine = AdaptiveLearningEngine()

# Database initialization is handled by JeopardyDatabase class

@app.route('/landing')
def landing():
    """Public landing page."""
    if session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('landing.html')

@app.route('/')
@login_required
def index():
    """Serve the main Jeopardy trainer page."""
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
        db.create_session(session['session_id'], session['user_id'])
    return render_template('jeopardy_trainer.html')

@app.route('/api/questions')
@login_required
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

@app.route('/api/progress', methods=['POST'])
@login_required
def save_progress():
    """Save user's answer and progress."""
    data = request.json
    session_id = session.get('session_id')
    user_id = session.get('user_id')
    
    if not session_id or not user_id:
        return jsonify({'error': 'No session found'}), 400
    
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
    count = int(request.args.get('count', 10))
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
        
        return jsonify(formatted_questions)
    
    except Exception as e:
        logger.error(f"Error getting AI questions: {e}")
        return jsonify({'error': 'Failed to get AI recommendations'}), 500

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

if __name__ == '__main__':
    # Database is automatically initialized by JeopardyDatabase class
    app.run(debug=True, port=5000)