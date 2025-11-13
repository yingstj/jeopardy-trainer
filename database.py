import sqlite3
import os

DB_FILE = "jeopardy_trainer.db"

def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initialize the database with the required tables."""
    if os.path.exists(DB_FILE):
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # User table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # User stats table
    cursor.execute("""
        CREATE TABLE user_stats (
            user_id INTEGER PRIMARY KEY,
            games_played INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Bookmarks table
    cursor.execute("""
        CREATE TABLE bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            clue TEXT NOT NULL,
            correct_response TEXT NOT NULL,
            bookmarked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Challenges table
    cursor.execute("""
        CREATE TABLE challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenger_id INTEGER NOT NULL,
            opponent_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', -- pending, active, completed
            num_questions INTEGER DEFAULT 10,
            categories TEXT,
            challenger_score INTEGER DEFAULT 0,
            opponent_score INTEGER DEFAULT 0,
            challenger_completed INTEGER DEFAULT 0, -- boolean
            opponent_completed INTEGER DEFAULT 0, -- boolean
            winner_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (challenger_id) REFERENCES users (id),
            FOREIGN KEY (opponent_id) REFERENCES users (id),
            FOREIGN KEY (winner_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
