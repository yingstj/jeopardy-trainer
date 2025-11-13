import sqlite3
import json
from database import get_db_connection
from user_manager import UserManager

class ChallengeManager:
    """Manages multiplayer challenges between users using a database."""

    def __init__(self):
        self.user_manager = UserManager()

    def create_challenge(self, challenger_username: str, opponent_username: str, categories: list, num_questions: int = 10) -> int:
        """Create a new challenge."""
        challenger = self.user_manager.get_user_data(challenger_username)
        opponent = self.user_manager.get_user_data(opponent_username)

        if not challenger or not opponent:
            return 0

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO challenges (challenger_id, opponent_id, categories, num_questions) VALUES (?, ?, ?, ?)",
            (challenger['id'], opponent['id'], json.dumps(categories), num_questions)
        )
        challenge_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return challenge_id

    def accept_challenge(self, challenge_id: int, username: str) -> bool:
        """Accept a challenge if the user is the opponent."""
        user = self.user_manager.get_user_data(username)
        if not user:
            return False

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE challenges SET status = 'active' WHERE id = ? AND opponent_id = ?",
            (challenge_id, user['id'])
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def complete_challenge(self, challenge_id: int, username: str, score: int) -> bool:
        """Complete one side of a challenge for a user and update their score."""
        user = self.user_manager.get_user_data(username)
        if not user:
            return False

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,))
        challenge = cursor.fetchone()
        if not challenge:
            conn.close()
            return False

        is_challenger = (user['id'] == challenge['challenger_id'])
        is_opponent = (user['id'] == challenge['opponent_id'])

        if not is_challenger and not is_opponent:
            conn.close()
            return False

        if is_challenger:
            cursor.execute(
                "UPDATE challenges SET challenger_score = ?, challenger_completed = 1 WHERE id = ?",
                (score, challenge_id)
            )
        else:
            cursor.execute(
                "UPDATE challenges SET opponent_score = ?, opponent_completed = 1 WHERE id = ?",
                (score, challenge_id)
            )
        
        conn.commit()

        cursor.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,))
        updated_challenge = cursor.fetchone()

        if updated_challenge['challenger_completed'] and updated_challenge['opponent_completed']:
            winner_id = None
            challenger_score = updated_challenge['challenger_score']
            opponent_score = updated_challenge['opponent_score']
            
            if challenger_score > opponent_score:
                winner_id = updated_challenge['challenger_id']
            elif opponent_score > challenger_score:
                winner_id = updated_challenge['opponent_id']

            cursor.execute(
                "UPDATE challenges SET status = 'completed', winner_id = ? WHERE id = ?",
                (winner_id, challenge_id)
            )
            conn.commit()

        conn.close()
        return True

    def get_active_challenges(self, username: str):
        return self._get_challenges_by_status(username, 'active')

    def get_pending_challenges(self, username: str):
        return self._get_challenges_by_status(username, 'pending')

    def get_completed_challenges(self, username: str):
        return self._get_challenges_by_status(username, 'completed')

    def _get_challenges_by_status(self, username: str, status: str):
        """Internal method to get challenges for a user by status."""
        user = self.user_manager.get_user_data(username)
        if not user:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT c.*, 
                   challenger.username as challenger, 
                   opponent.username as opponent
            FROM challenges c
            JOIN users challenger ON c.challenger_id = challenger.id
            JOIN users opponent ON c.opponent_id = opponent.id
            WHERE (c.challenger_id = ? OR c.opponent_id = ?) AND c.status = ?
            ORDER BY c.created_at DESC
        """
        cursor.execute(query, (user['id'], user['id'], status))
        challenges = cursor.fetchall()
        conn.close()
        
        # Deserialize categories JSON
        deserialized_challenges = []
        for challenge in challenges:
            challenge_dict = dict(challenge)
            if challenge_dict['categories']:
                challenge_dict['categories'] = json.loads(challenge_dict['categories'])
            deserialized_challenges.append(challenge_dict)
            
        return deserialized_challenges
