"""
Simple user management system for Jeopardy Trainer
Stores user data locally in JSON format
"""

import sqlite3
from typing import Dict, List, Optional
from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

class UserManager:
    def __init__(self):
        """Initialize the user manager with a database connection."""
        pass

    def _hash_password(self, password: str) -> str:
        """Hash a password for secure storage."""
        return generate_password_hash(password)

    def create_user(self, username: str, password: str) -> bool:
        """Create a new user account."""
        if self.get_user_data(username):
            return False  # User already exists

        conn = get_db_connection()
        cursor = conn.cursor()
        
        hashed_password = self._hash_password(password)
        
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hashed_password)
        )
        user_id = cursor.lastrowid
        
        # Initialize stats
        cursor.execute(
            "INSERT INTO user_stats (user_id) VALUES (?)",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        return True

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate a user."""
        user_data = self.get_user_data(username)
        if not user_data:
            return False
        
        return user_data and check_password_hash(user_data["password_hash"], password)

    def get_user_data(self, username: str) -> Optional[Dict]:
        """Get user data from the database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return None
        
        cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user["id"],))
        stats = cursor.fetchone()
        
        conn.close()

        user_dict = dict(user)
        user_dict['stats'] = dict(stats) if stats else {}
        return user_dict

    def save_user_session(self, username: str, session_data: Dict):
        """Save session data for a user."""
        user_data = self.get_user_data(username)
        if not user_data:
            return

        user_id = user_data["id"]
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update cumulative stats
        update_query = """
            UPDATE user_stats
            SET
                total_questions = total_questions + ?,
                correct_answers = correct_answers + ?,
                total_score = total_score + ?,
                best_streak = MAX(best_streak, ?),
                games_played = games_played + 1
            WHERE user_id = ?
        """
        cursor.execute(update_query, (
            session_data.get("total_questions", 0),
            session_data.get("correct_answers", 0),
            session_data.get("score", 0),
            session_data.get("best_streak", 0),
            user_id
        ))

        # Handle bookmarks
        if "bookmarks" in session_data:
            for bookmark in session_data["bookmarks"]:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO bookmarks (user_id, category, clue, correct_response)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, bookmark["category"], bookmark["clue"], bookmark["correct_response"])
                )

        conn.commit()
        conn.close()

    def user_exists(self, username: str) -> bool:
        """Check if a user exists."""
        return self.get_user_data(username) is not None

    def list_usernames(self, exclude: Optional[str] = None, limit: int = 20) -> List[str]:
        """Return a list of registered usernames, optionally excluding one."""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT username FROM users"
        params = []
        if exclude:
            query += " WHERE username != ?"
            params.append(exclude)

        query += " ORDER BY username ASC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [row["username"] for row in rows]