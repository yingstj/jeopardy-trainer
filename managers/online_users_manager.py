import datetime
import random
from typing import List

from user_manager import UserManager


class OnlineUsers:
    """Provides a list of online users, preferring registered accounts."""
    
    def __init__(self):
        self.online_users: List[str] = []
        self.last_update = datetime.datetime.now()
        self.user_manager = UserManager()
    
    def update_online_users(self, current_user: str):
        """Return a list of available opponents, prioritising registered users."""
        registered_users = self.user_manager.list_usernames(exclude=current_user, limit=12)
        if registered_users:
            self.online_users = registered_users
            self.last_update = datetime.datetime.now()
        else:
            bot_names = ["QuizMaster", "TriviaKing", "JeopardyPro", "BrainiacBot", 
                         "SmartPlayer", "QuickThinker", "FactFinder", "WiseOwl"]
            if (datetime.datetime.now() - self.last_update).seconds > 30 or not self.online_users:
                num_online = random.randint(3, 8)
                self.online_users = random.sample(bot_names, num_online)
                self.last_update = datetime.datetime.now()
        
        if current_user and current_user not in self.online_users:
            self.online_users.insert(0, current_user)
        
        return self.online_users
    
    def get_user_stats(self, username: str):
        """Get simulated stats for a user"""
        return {
            "games_played": random.randint(10, 500),
            "win_rate": random.randint(40, 85),
            "avg_score": random.randint(60, 95),
            "rank": random.choice(["Bronze", "Silver", "Gold", "Platinum", "Diamond"])
        }
