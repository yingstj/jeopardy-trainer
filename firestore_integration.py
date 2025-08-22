"""Firestore integration for persistent cloud storage of user data and game statistics"""

import firebase_admin
from firebase_admin import firestore
import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class FirestoreManager:
    """Manages all Firestore operations for Jaypardy"""
    
    def __init__(self):
        """Initialize Firestore client"""
        try:
            self.db = firestore.client()
            logger.info("Firestore initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            self.db = None
    
    # User Management
    def create_user_profile(self, uid: str, username: str, email: str) -> bool:
        """Create a new user profile in Firestore"""
        if not self.db:
            return False
        
        try:
            user_ref = self.db.collection('users').document(uid)
            user_ref.set({
                'username': username,
                'email': email,
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_login': firestore.SERVER_TIMESTAMP,
                'stats': {
                    'total_games': 0,
                    'total_correct': 0,
                    'best_streak': 0,
                    'total_points': 0,
                    'accuracy_percentage': 0,
                    'average_response_time': 0,
                    'categories_played': {},
                    'difficulty_breakdown': {
                        'easy': {'played': 0, 'correct': 0},
                        'medium': {'played': 0, 'correct': 0},
                        'hard': {'played': 0, 'correct': 0}
                    }
                },
                'achievements': [],
                'bookmarks': [],
                'ai_opponents_faced': {},
                'multiplayer_stats': {
                    'wins': 0,
                    'losses': 0,
                    'ties': 0,
                    'rating': 1200
                }
            })
            logger.info(f"Created user profile for {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to create user profile: {e}")
            return False
    
    def get_user_profile(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get user profile from Firestore"""
        if not self.db:
            return None
        
        try:
            user_ref = self.db.collection('users').document(uid)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                return user_doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None
    
    def update_user_stats(self, uid: str, session_stats: Dict[str, Any]) -> bool:
        """Update user statistics after a game session"""
        if not self.db:
            return False
        
        try:
            user_ref = self.db.collection('users').document(uid)
            
            # Get current stats
            user_doc = user_ref.get()
            if not user_doc.exists:
                return False
            
            current_stats = user_doc.to_dict().get('stats', {})
            
            # Update cumulative stats
            new_stats = {
                'stats.total_games': firestore.Increment(session_stats.get('games_played', 0)),
                'stats.total_correct': firestore.Increment(session_stats.get('correct_answers', 0)),
                'stats.total_points': firestore.Increment(session_stats.get('points_earned', 0)),
                'last_played': firestore.SERVER_TIMESTAMP
            }
            
            # Update best streak if necessary
            if session_stats.get('best_streak', 0) > current_stats.get('best_streak', 0):
                new_stats['stats.best_streak'] = session_stats['best_streak']
            
            # Update category statistics
            for category, count in session_stats.get('categories', {}).items():
                field_key = f'stats.categories_played.{category.replace(".", "_")}'
                new_stats[field_key] = firestore.Increment(count)
            
            # Update accuracy percentage
            total_games = current_stats.get('total_games', 0) + session_stats.get('games_played', 0)
            total_correct = current_stats.get('total_correct', 0) + session_stats.get('correct_answers', 0)
            if total_games > 0:
                new_stats['stats.accuracy_percentage'] = round((total_correct / total_games) * 100, 2)
            
            user_ref.update(new_stats)
            logger.info(f"Updated stats for user {uid}")
            return True
        except Exception as e:
            logger.error(f"Failed to update user stats: {e}")
            return False
    
    # Game Sessions
    def create_game_session(self, uid: str, session_id: str) -> bool:
        """Create a new game session"""
        if not self.db:
            return False
        
        try:
            session_ref = self.db.collection('sessions').document(session_id)
            session_ref.set({
                'user_id': uid,
                'started_at': firestore.SERVER_TIMESTAMP,
                'status': 'active',
                'questions': [],
                'score': 0,
                'streak': 0,
                'ai_opponent': None,
                'multiplayer_match_id': None
            })
            return True
        except Exception as e:
            logger.error(f"Failed to create game session: {e}")
            return False
    
    def update_session_question(self, session_id: str, question_data: Dict[str, Any]) -> bool:
        """Add a question result to a session"""
        if not self.db:
            return False
        
        try:
            session_ref = self.db.collection('sessions').document(session_id)
            session_ref.update({
                'questions': firestore.ArrayUnion([question_data]),
                'score': firestore.Increment(1 if question_data.get('correct', False) else 0),
                'last_activity': firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            logger.error(f"Failed to update session question: {e}")
            return False
    
    def end_game_session(self, session_id: str, final_stats: Dict[str, Any]) -> bool:
        """End a game session and record final statistics"""
        if not self.db:
            return False
        
        try:
            session_ref = self.db.collection('sessions').document(session_id)
            session_ref.update({
                'status': 'completed',
                'ended_at': firestore.SERVER_TIMESTAMP,
                'final_stats': final_stats
            })
            return True
        except Exception as e:
            logger.error(f"Failed to end game session: {e}")
            return False
    
    # Bookmarks
    def add_bookmark(self, uid: str, bookmark_data: Dict[str, Any]) -> bool:
        """Add a bookmark for a user"""
        if not self.db:
            return False
        
        try:
            bookmark_ref = self.db.collection('users').document(uid).collection('bookmarks')
            bookmark_ref.add({
                **bookmark_data,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            logger.error(f"Failed to add bookmark: {e}")
            return False
    
    def get_bookmarks(self, uid: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's bookmarks"""
        if not self.db:
            return []
        
        try:
            bookmarks_ref = self.db.collection('users').document(uid).collection('bookmarks')
            bookmarks = bookmarks_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).get()
            
            return [bookmark.to_dict() for bookmark in bookmarks]
        except Exception as e:
            logger.error(f"Failed to get bookmarks: {e}")
            return []
    
    # Achievements
    def unlock_achievement(self, uid: str, achievement: Dict[str, Any]) -> bool:
        """Unlock an achievement for a user"""
        if not self.db:
            return False
        
        try:
            user_ref = self.db.collection('users').document(uid)
            user_ref.update({
                'achievements': firestore.ArrayUnion([achievement])
            })
            
            # Also add to achievements collection for global tracking
            achievements_ref = self.db.collection('achievements')
            achievements_ref.add({
                'user_id': uid,
                'achievement': achievement,
                'unlocked_at': firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            logger.error(f"Failed to unlock achievement: {e}")
            return False
    
    # Leaderboards
    def get_leaderboard(self, category: str = 'overall', limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard for a specific category"""
        if not self.db:
            return []
        
        try:
            users_ref = self.db.collection('users')
            
            if category == 'overall':
                query = users_ref.order_by('stats.total_points', direction=firestore.Query.DESCENDING)
            elif category == 'streak':
                query = users_ref.order_by('stats.best_streak', direction=firestore.Query.DESCENDING)
            elif category == 'accuracy':
                query = users_ref.order_by('stats.accuracy_percentage', direction=firestore.Query.DESCENDING)
            elif category == 'multiplayer':
                query = users_ref.order_by('multiplayer_stats.rating', direction=firestore.Query.DESCENDING)
            else:
                query = users_ref.order_by('stats.total_points', direction=firestore.Query.DESCENDING)
            
            leaders = query.limit(limit).get()
            
            leaderboard = []
            for idx, leader in enumerate(leaders, 1):
                data = leader.to_dict()
                leaderboard.append({
                    'rank': idx,
                    'username': data.get('username', 'Unknown'),
                    'value': self._get_leaderboard_value(data, category),
                    'uid': leader.id
                })
            
            return leaderboard
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {e}")
            return []
    
    def _get_leaderboard_value(self, user_data: Dict[str, Any], category: str) -> Any:
        """Extract the relevant value for leaderboard display"""
        stats = user_data.get('stats', {})
        
        if category == 'overall':
            return stats.get('total_points', 0)
        elif category == 'streak':
            return stats.get('best_streak', 0)
        elif category == 'accuracy':
            return f"{stats.get('accuracy_percentage', 0)}%"
        elif category == 'multiplayer':
            return user_data.get('multiplayer_stats', {}).get('rating', 1200)
        else:
            return stats.get('total_points', 0)
    
    # Multiplayer Challenges
    def create_challenge(self, from_uid: str, to_uid: str, challenge_type: str = 'standard') -> Optional[str]:
        """Create a multiplayer challenge"""
        if not self.db:
            return None
        
        try:
            challenges_ref = self.db.collection('challenges')
            challenge_doc = challenges_ref.add({
                'from_user': from_uid,
                'to_user': to_uid,
                'type': challenge_type,
                'status': 'pending',
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            return challenge_doc[1].id
        except Exception as e:
            logger.error(f"Failed to create challenge: {e}")
            return None
    
    def get_pending_challenges(self, uid: str) -> List[Dict[str, Any]]:
        """Get pending challenges for a user"""
        if not self.db:
            return []
        
        try:
            challenges_ref = self.db.collection('challenges')
            query = challenges_ref.where('to_user', '==', uid).where('status', '==', 'pending')
            challenges = query.get()
            
            return [{'id': challenge.id, **challenge.to_dict()} for challenge in challenges]
        except Exception as e:
            logger.error(f"Failed to get pending challenges: {e}")
            return []
    
    # Real-time presence
    def update_user_presence(self, uid: str, status: str = 'online') -> bool:
        """Update user's online presence"""
        if not self.db:
            return False
        
        try:
            user_ref = self.db.collection('users').document(uid)
            user_ref.update({
                'presence': {
                    'status': status,
                    'last_seen': firestore.SERVER_TIMESTAMP
                }
            })
            return True
        except Exception as e:
            logger.error(f"Failed to update user presence: {e}")
            return False
    
    def get_online_users(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of currently online users"""
        if not self.db:
            return []
        
        try:
            users_ref = self.db.collection('users')
            query = users_ref.where('presence.status', '==', 'online').limit(limit)
            online_users = query.get()
            
            return [{'uid': user.id, **user.to_dict()} for user in online_users]
        except Exception as e:
            logger.error(f"Failed to get online users: {e}")
            return []

# Global instance
firestore_manager = FirestoreManager()