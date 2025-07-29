"""
Application factory for Railway deployment.
This ensures proper initialization order.
"""

import os
from flask import Flask
from datetime import timedelta

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')
    app.permanent_session_lifetime = timedelta(days=7)
    
    # Import and register blueprints after app creation
    from auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Import routes after app creation
    import app_routes
    app_routes.init_app(app)
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)