#!/usr/bin/env python3
"""
Database viewer for Railway deployment.
This creates a simple web interface to view database contents.
"""

from flask import Flask, render_template_string, jsonify
import os
from database import JeopardyDatabase

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Jeopardy Database Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f0f0f0; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #007bff; color: white; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-card h3 { margin: 0 0 10px 0; font-size: 18px; }
        .stat-card .number { font-size: 36px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #007bff; color: white; }
        tr:hover { background-color: #f5f5f5; }
        .category { font-weight: bold; color: #007bff; }
        .answer { color: #28a745; font-weight: bold; }
        .error { color: #dc3545; padding: 20px; background: #f8d7da; border-radius: 5px; }
        .nav { margin: 20px 0; }
        .nav a { padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px; }
        .nav a:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Jeopardy Database Viewer</h1>
        
        <div class="nav">
            <a href="/">Overview</a>
            <a href="/questions">Sample Questions</a>
            <a href="/categories">Categories</a>
            <a href="/users">Users</a>
        </div>
        
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

OVERVIEW_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
    <h2>Database Overview</h2>
    
    <div class="stats">
        <div class="stat-card">
            <h3>Total Questions</h3>
            <div class="number">{{ stats.total_questions }}</div>
        </div>
        <div class="stat-card" style="background: #28a745;">
            <h3>Categories</h3>
            <div class="number">{{ stats.total_categories }}</div>
        </div>
        <div class="stat-card" style="background: #ffc107;">
            <h3>Users</h3>
            <div class="number">{{ stats.total_users }}</div>
        </div>
        <div class="stat-card" style="background: #17a2b8;">
            <h3>Database Type</h3>
            <div class="number">{{ stats.db_type }}</div>
        </div>
    </div>
    
    <h3>Top Categories</h3>
    <table>
        <tr>
            <th>Category</th>
            <th>Question Count</th>
        </tr>
        {% for cat, count in stats.top_categories %}
        <tr>
            <td class="category">{{ cat }}</td>
            <td>{{ count }}</td>
        </tr>
        {% endfor %}
    </table>
{% endblock %}
"""

QUESTIONS_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
    <h2>Sample Questions</h2>
    
    {% if questions %}
    <table>
        <tr>
            <th>Category</th>
            <th>Question</th>
            <th>Answer</th>
            <th>Value</th>
        </tr>
        {% for q in questions %}
        <tr>
            <td class="category">{{ q.category }}</td>
            <td>{{ q.question[:100] }}{% if q.question|length > 100 %}...{% endif %}</td>
            <td class="answer">{{ q.answer }}</td>
            <td>${{ q.value }}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p class="error">No questions found in database!</p>
    {% endif %}
{% endblock %}
"""

@app.route('/')
def overview():
    try:
        db = JeopardyDatabase()
        
        # Get statistics
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
        
        stats = {
            'total_questions': total_questions,
            'total_categories': len(categories),
            'total_users': user_count,
            'db_type': db.db_type.upper(),
            'top_categories': categories[:10]
        }
        
        return render_template_string(OVERVIEW_TEMPLATE, stats=stats)
    except Exception as e:
        return f'<div class="container"><h1>Error</h1><p class="error">{str(e)}</p></div>'

@app.route('/questions')
def questions():
    try:
        db = JeopardyDatabase()
        questions = db.get_questions(count=20)
        return render_template_string(QUESTIONS_TEMPLATE, questions=questions)
    except Exception as e:
        return f'<div class="container"><h1>Error</h1><p class="error">{str(e)}</p></div>'

@app.route('/categories')
def categories():
    try:
        db = JeopardyDatabase()
        categories = db.get_categories()
        
        html = """
        {% extends "base.html" %}
        {% block content %}
            <h2>All Categories ({{ categories|length }} total)</h2>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Question Count</th>
                </tr>
                {% for cat, count in categories %}
                <tr>
                    <td class="category">{{ cat }}</td>
                    <td>{{ count }}</td>
                </tr>
                {% endfor %}
            </table>
        {% endblock %}
        """
        
        return render_template_string(html, categories=categories)
    except Exception as e:
        return f'<div class="container"><h1>Error</h1><p class="error">{str(e)}</p></div>'

@app.route('/users')
def users():
    try:
        db = JeopardyDatabase()
        
        # Get users
        with db.get_connection() as conn:
            if db.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute('SELECT id, username, email, created_at, last_login FROM users ORDER BY created_at DESC LIMIT 20')
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'id': row[0],
                        'username': row[1],
                        'email': row[2],
                        'created_at': row[3],
                        'last_login': row[4]
                    })
                cursor.close()
            else:
                cursor = conn.execute('SELECT id, username, email, created_at, last_login FROM users ORDER BY created_at DESC LIMIT 20')
                users = [dict(row) for row in cursor.fetchall()]
        
        html = """
        {% extends "base.html" %}
        {% block content %}
            <h2>Recent Users</h2>
            {% if users %}
            <table>
                <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Created</th>
                    <th>Last Login</th>
                </tr>
                {% for user in users %}
                <tr>
                    <td>{{ user.id }}</td>
                    <td>{{ user.username }}</td>
                    <td>{{ user.email }}</td>
                    <td>{{ user.created_at }}</td>
                    <td>{{ user.last_login or 'Never' }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No users found.</p>
            {% endif %}
        {% endblock %}
        """
        
        return render_template_string(html, users=users)
    except Exception as e:
        return f'<div class="container"><h1>Error</h1><p class="error">{str(e)}</p></div>'

# Fix the template inheritance
app.jinja_env.globals['base.html'] = HTML_TEMPLATE

@app.template_filter('length')
def length_filter(s):
    return len(s)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting database viewer on port {port}")
    print(f"Visit http://localhost:{port} to view your database")
    app.run(host='0.0.0.0', port=port, debug=True)