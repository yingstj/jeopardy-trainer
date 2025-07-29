import os
import sqlite3
import urllib.parse

# This file helps your existing SQLite application work with Railway's PostgreSQL
# It provides connection details and compatibility functions

def get_database_url():
    """Get the database URL from Railway or use a local SQLite database."""
    if 'DATABASE_URL' in os.environ:
        # Parse the PostgreSQL URL from Railway
        url = os.environ['DATABASE_URL']
        parsed_url = urllib.parse.urlparse(url)
        
        # Print connection details (remove in production)
        print(f"Using PostgreSQL database at {parsed_url.hostname}")
        return url
    else:
        # Use local SQLite database
        print("Using local SQLite database")
        return "sqlite:///jeopardy.db"

def init_railway_config():
    """Initialize any Railway-specific configuration."""
    # Set environment variables expected by your application
    if 'PORT' in os.environ:
        print(f"Railway PORT: {os.environ['PORT']}")
    
    # You can add more Railway-specific configuration here
    
    return True