"""
Simple user management system for Jeopardy Trainer
Stores user data locally in JSON format
"""

import json
import hashlib
import os
from typing import Dict, Optional
from datetime import datetime

class UserManager:
    def __init__(self, data_file: str = "users_data.json"):
        """Initialize the user manager with a data file"""
        self.data_file = data_file
        self.users_data = self._load_users()
    
    def _load_users(self) -> Dict:
        """Load users from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_users(self):
        """Save users to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.users_data, f, indent=2)
    
    def _hash_password(self, password: str) -> str:
        """Hash a password for secure storage"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username: str, password: str) -> bool:
        """Create a new user account"""
        if username.lower() in self.users_data:
            return False  # User already exists
        
        self.users_data[username.lower()] = {
            "username": username,
            "password": self._hash_password(password),
            "created_at": datetime.now().isoformat(),
            "stats": {
                "total_questions": 0,
                "correct_answers": 0,
                "total_score": 0,
                "best_streak": 0,
                "games_played": 0,
                "achievements": [],
                "bookmarks": []
            },
            "preferences": {
                "favorite_categories": [],
                "default_time_limit": 30
            }
        }
        self._save_users()
        return True
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate a user"""
        user_key = username.lower()
        if user_key not in self.users_data:
            return False
        
        return self.users_data[user_key]["password"] == self._hash_password(password)
    
    def get_user_data(self, username: str) -> Optional[Dict]:
        """Get user data"""
        user_key = username.lower()
        if user_key in self.users_data:
            return self.users_data[user_key]
        return None
    
    def update_user_stats(self, username: str, stats_update: Dict):
        """Update user statistics"""
        user_key = username.lower()
        if user_key in self.users_data:
            for key, value in stats_update.items():
                if key in self.users_data[user_key]["stats"]:
                    if isinstance(value, (int, float)):
                        self.users_data[user_key]["stats"][key] += value
                    elif isinstance(value, list):
                        self.users_data[user_key]["stats"][key].extend(value)
                    else:
                        self.users_data[user_key]["stats"][key] = value
            
            self.users_data[user_key]["last_played"] = datetime.now().isoformat()
            self._save_users()
    
    def save_user_session(self, username: str, session_data: Dict):
        """Save session data for a user"""
        user_key = username.lower()
        if user_key in self.users_data:
            # Update cumulative stats
            if "total_questions" in session_data:
                self.users_data[user_key]["stats"]["total_questions"] += session_data["total_questions"]
            if "correct_answers" in session_data:
                self.users_data[user_key]["stats"]["correct_answers"] += session_data["correct_answers"]
            if "score" in session_data:
                self.users_data[user_key]["stats"]["total_score"] += session_data["score"]
            if "best_streak" in session_data:
                current_best = self.users_data[user_key]["stats"]["best_streak"]
                self.users_data[user_key]["stats"]["best_streak"] = max(current_best, session_data["best_streak"])
            if "bookmarks" in session_data:
                # Add new bookmarks (avoid duplicates)
                existing = self.users_data[user_key]["stats"]["bookmarks"]
                for bookmark in session_data["bookmarks"]:
                    if bookmark not in existing:
                        existing.append(bookmark)
            
            self.users_data[user_key]["stats"]["games_played"] += 1
            self.users_data[user_key]["last_played"] = datetime.now().isoformat()
            self._save_users()
    
    def get_leaderboard(self, metric: str = "total_score", limit: int = 10) -> list:
        """Get leaderboard based on a metric"""
        users_list = []
        for username, data in self.users_data.items():
            users_list.append({
                "username": data["username"],
                "value": data["stats"].get(metric, 0),
                "games_played": data["stats"]["games_played"]
            })
        
        # Sort by the metric
        users_list.sort(key=lambda x: x["value"], reverse=True)
        return users_list[:limit]
    
    def user_exists(self, username: str) -> bool:
        """Check if a user exists"""
        return username.lower() in self.users_data