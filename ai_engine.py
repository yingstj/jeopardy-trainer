import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import math
from collections import defaultdict
import logging
from database import JeopardyDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdaptiveLearningEngine:
    """
    Adaptive learning engine that selects questions based on:
    - User performance history
    - Spaced repetition algorithms
    - Difficulty progression
    - Category mastery
    - Response time analysis
    - Forgetting curve modeling
    """
    
    def __init__(self, db_path: str = 'data/jeopardy.db'):
        self.db = JeopardyDatabase(db_path)
        
        # Learning parameters
        self.target_success_rate = 0.75  # Aim for 75% success rate
        self.difficulty_step = 0.1  # How much to adjust difficulty
        self.min_attempts_for_mastery = 5  # Minimum attempts before considering mastery
        
        # Spaced repetition parameters (SuperMemo SM-2 inspired)
        self.initial_interval = 1  # Days
        self.easy_bonus = 1.3
        self.min_ease_factor = 1.3
        self.max_ease_factor = 2.5
        
        # Category weights
        self.category_importance = {}  # Can be customized per user
        self.time_decay_factor = 0.1  # How quickly old performance loses relevance
        
    def calculate_user_level(self, user_stats: Dict) -> float:
        """
        Calculate user's overall skill level (0-10 scale).
        """
        if not user_stats or user_stats['overall']['total_questions'] == 0:
            return 1.0  # Beginner level
        
        accuracy = user_stats['overall']['accuracy'] / 100.0
        total_questions = user_stats['overall']['total_questions']
        avg_time = user_stats['overall']['avg_time']
        
        # Weight factors
        accuracy_weight = 0.5
        experience_weight = 0.3
        speed_weight = 0.2
        
        # Normalize experience (logarithmic scale)
        experience_score = min(1.0, math.log(total_questions + 1) / math.log(1000))
        
        # Normalize speed (faster is better, cap at 30 seconds)
        speed_score = max(0, min(1.0, (30 - avg_time) / 25)) if avg_time > 0 else 0.5
        
        # Calculate weighted score
        level = (accuracy * accuracy_weight + 
                experience_score * experience_weight + 
                speed_score * speed_weight) * 10
        
        return round(level, 1)
    
    def calculate_category_mastery(self, category_stats: List[Dict]) -> Dict[str, float]:
        """
        Calculate mastery level for each category.
        """
        mastery = {}
        
        for stat in category_stats:
            category = stat['category']
            accuracy = stat['accuracy'] / 100.0
            total = stat['total']
            
            if total < self.min_attempts_for_mastery:
                # Not enough data - apply penalty
                confidence_penalty = 0.5 * (total / self.min_attempts_for_mastery)
                mastery[category] = accuracy * confidence_penalty
            else:
                # Enough data - use accuracy with slight boost for experience
                experience_bonus = min(0.1, total / 100)
                mastery[category] = min(1.0, accuracy + experience_bonus)
        
        return mastery
    
    def calculate_forgetting_curve(self, last_seen: datetime, 
                                 success_rate: float, 
                                 ease_factor: float = 2.5) -> float:
        """
        Calculate retention probability based on forgetting curve.
        Uses Ebbinghaus forgetting curve with modifications.
        """
        if not last_seen:
            return 0.0
        
        days_elapsed = (datetime.now() - last_seen).days
        
        # Modified forgetting curve formula
        # R = e^(-t/S) where S is stability
        stability = ease_factor * (1 + success_rate) * 5  # Base stability in days
        retention = math.exp(-days_elapsed / stability)
        
        return max(0.0, min(1.0, retention))
    
    def calculate_question_priority(self, question: Dict, 
                                  user_history: List[Dict],
                                  user_level: float,
                                  category_mastery: Dict[str, float]) -> float:
        """
        Calculate priority score for a question based on multiple factors.
        Higher score = higher priority.
        """
        question_id = question['id']
        category = question['category']
        difficulty_rating = question.get('difficulty_rating', 5.0)
        
        # Find user's history with this question
        question_history = [h for h in user_history if h.get('question_id') == question_id]
        
        # Base priority factors
        factors = {
            'difficulty_match': 0.0,
            'category_weakness': 0.0,
            'spaced_repetition': 0.0,
            'novelty': 0.0,
            'error_correction': 0.0
        }
        
        # 1. Difficulty matching (aim for appropriate challenge)
        difficulty_diff = abs(difficulty_rating - user_level)
        if difficulty_diff <= 1.5:
            factors['difficulty_match'] = 1.0 - (difficulty_diff / 3.0)
        else:
            factors['difficulty_match'] = 0.2  # Too easy or too hard
        
        # 2. Category weakness priority
        mastery = category_mastery.get(category, 0.5)
        if mastery < 0.6:
            factors['category_weakness'] = 1.0 - mastery
        else:
            factors['category_weakness'] = 0.2
        
        # 3. Spaced repetition timing
        if question_history:
            last_attempt = question_history[-1]
            last_seen = datetime.fromisoformat(last_attempt['timestamp'])
            success_rate = sum(1 for h in question_history if h['is_correct']) / len(question_history)
            
            retention = self.calculate_forgetting_curve(last_seen, success_rate)
            
            # Prioritize if retention is dropping below threshold
            if retention < 0.8 and retention > 0.3:
                factors['spaced_repetition'] = 1.0 - retention
            elif retention <= 0.3:
                factors['spaced_repetition'] = 0.8  # Due for review
            else:
                factors['spaced_repetition'] = 0.1  # Still fresh
            
            # 4. Error correction priority
            if not last_attempt['is_correct']:
                days_since = (datetime.now() - last_seen).days
                if days_since >= 1:
                    factors['error_correction'] = min(1.0, days_since / 7)
        else:
            # 5. Novelty bonus for unseen questions
            factors['novelty'] = 0.8
            factors['spaced_repetition'] = 0.5
        
        # Weight the factors
        weights = {
            'difficulty_match': 0.25,
            'category_weakness': 0.20,
            'spaced_repetition': 0.25,
            'novelty': 0.15,
            'error_correction': 0.15
        }
        
        # Calculate weighted priority
        priority = sum(factors[f] * weights[f] for f in factors)
        
        # Apply category importance modifier if set
        if category in self.category_importance:
            priority *= self.category_importance[category]
        
        return priority
    
    def select_optimal_questions(self, user_id: int, 
                               count: int = 10,
                               category_filter: Optional[str] = None,
                               mode: str = 'adaptive') -> List[Dict]:
        """
        Select optimal questions for the user based on adaptive learning algorithm.
        
        Modes:
        - adaptive: Full adaptive algorithm
        - review: Focus on spaced repetition
        - challenge: Slightly harder questions
        - practice: Random selection at user level
        - weakness: Focus on weak categories
        """
        # Get user statistics
        user = self.db.get_user_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return []
        
        # Get user's current session
        with self.db.get_connection() as conn:
            session = conn.execute(
                'SELECT session_id FROM user_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
                (user_id,)
            ).fetchone()
            
            if not session:
                logger.error(f"No session found for user {user_id}")
                return []
            
            session_id = session['session_id']
        
        # Get user statistics and history
        user_stats = self.db.get_session_stats(session_id)
        user_level = self.calculate_user_level(user_stats)
        category_mastery = self.calculate_category_mastery(user_stats.get('by_category', []))
        
        # Get user's question history
        with self.db.get_connection() as conn:
            history = conn.execute('''
                SELECT up.*, q.category, q.difficulty_rating
                FROM user_progress up
                JOIN questions q ON up.question_id = q.id
                WHERE up.user_id = ?
                ORDER BY up.timestamp DESC
                LIMIT 1000
            ''', (user_id,)).fetchall()
            
            user_history = [dict(h) for h in history]
        
        # Get available questions
        params = {'count': count * 10}  # Get more to filter from
        if category_filter:
            params['category'] = category_filter
        
        available_questions = self.db.get_questions(**params)
        
        if not available_questions:
            return []
        
        # Apply mode-specific filtering
        if mode == 'review':
            # Focus on questions due for review
            answered_ids = set(h['question_id'] for h in user_history)
            available_questions = [q for q in available_questions if q['id'] in answered_ids]
        
        elif mode == 'challenge':
            # Select slightly harder questions
            target_difficulty = min(10, user_level + 1.5)
            available_questions = [q for q in available_questions 
                                 if abs(q.get('difficulty_rating', 5) - target_difficulty) <= 2]
        
        elif mode == 'weakness':
            # Focus on weak categories
            weak_categories = [cat for cat, mastery in category_mastery.items() if mastery < 0.6]
            if weak_categories:
                available_questions = [q for q in available_questions 
                                     if q['category'] in weak_categories]
        
        elif mode == 'practice':
            # Random selection at appropriate level
            target_difficulty = user_level
            available_questions = [q for q in available_questions 
                                 if abs(q.get('difficulty_rating', 5) - target_difficulty) <= 2]
            np.random.shuffle(available_questions)
            return available_questions[:count]
        
        # Calculate priority for each question
        question_priorities = []
        for question in available_questions:
            priority = self.calculate_question_priority(
                question, user_history, user_level, category_mastery
            )
            question_priorities.append((question, priority))
        
        # Sort by priority and select top questions
        question_priorities.sort(key=lambda x: x[1], reverse=True)
        selected_questions = [q for q, _ in question_priorities[:count]]
        
        # Add learning metadata to questions
        for question in selected_questions:
            question['ai_metadata'] = {
                'user_level': user_level,
                'category_mastery': category_mastery.get(question['category'], 0.5),
                'predicted_success': self.predict_success_rate(
                    question, user_history, user_level, category_mastery
                ),
                'learning_objective': self.determine_learning_objective(
                    question, user_history, category_mastery
                )
            }
        
        logger.info(f"Selected {len(selected_questions)} questions for user {user_id} in {mode} mode")
        return selected_questions
    
    def predict_success_rate(self, question: Dict, 
                            user_history: List[Dict],
                            user_level: float,
                            category_mastery: Dict[str, float]) -> float:
        """
        Predict the probability of user answering correctly.
        """
        category = question['category']
        difficulty = question.get('difficulty_rating', 5.0)
        
        # Base prediction from category mastery
        base_rate = category_mastery.get(category, 0.5)
        
        # Adjust for difficulty difference
        level_diff = difficulty - user_level
        difficulty_modifier = 1 / (1 + math.exp(0.5 * level_diff))  # Sigmoid function
        
        # Check previous attempts on this question
        question_attempts = [h for h in user_history if h.get('question_id') == question['id']]
        if question_attempts:
            recent_success = sum(1 for h in question_attempts[-3:] if h['is_correct']) / min(3, len(question_attempts))
            prediction = 0.7 * difficulty_modifier + 0.3 * recent_success
        else:
            prediction = base_rate * difficulty_modifier
        
        return round(max(0.1, min(0.95, prediction)), 2)
    
    def determine_learning_objective(self, question: Dict,
                                   user_history: List[Dict],
                                   category_mastery: Dict[str, float]) -> str:
        """
        Determine the learning objective for presenting this question.
        """
        category = question['category']
        mastery = category_mastery.get(category, 0.5)
        question_attempts = [h for h in user_history if h.get('question_id') == question['id']]
        
        if not question_attempts:
            if mastery < 0.4:
                return "Build foundation in " + category
            else:
                return "Expand knowledge in " + category
        
        success_rate = sum(1 for h in question_attempts if h['is_correct']) / len(question_attempts)
        last_attempt = question_attempts[-1]
        days_since = (datetime.now() - datetime.fromisoformat(last_attempt['timestamp'])).days
        
        if not last_attempt['is_correct']:
            return "Master previously missed concept"
        elif days_since > 7 and success_rate < 1.0:
            return "Reinforce through spaced repetition"
        elif success_rate == 1.0 and len(question_attempts) >= 3:
            return "Maintain mastery"
        else:
            return "Strengthen understanding"
    
    def update_learning_parameters(self, user_id: int, 
                                 question_id: int,
                                 was_correct: bool,
                                 response_time: int):
        """
        Update learning parameters based on user's response.
        This helps the algorithm adapt to the user's learning patterns.
        """
        with self.db.get_connection() as conn:
            # Get question details
            question = conn.execute(
                'SELECT category, difficulty_rating FROM questions WHERE id = ?',
                (question_id,)
            ).fetchone()
            
            if not question:
                return
            
            category = question['category']
            difficulty = question['difficulty_rating'] or 5.0
            
            # Update category importance based on performance
            if category not in self.category_importance:
                self.category_importance[category] = 1.0
            
            # Adjust importance based on struggle/success
            if not was_correct and difficulty <= 6:
                # Struggling with easier questions - increase importance
                self.category_importance[category] = min(2.0, 
                    self.category_importance[category] * 1.1)
            elif was_correct and difficulty >= 7:
                # Succeeding with harder questions - can reduce focus
                self.category_importance[category] = max(0.5,
                    self.category_importance[category] * 0.95)
    
    def get_learning_insights(self, user_id: int) -> Dict:
        """
        Generate learning insights and recommendations for the user.
        """
        # Get user session
        with self.db.get_connection() as conn:
            session = conn.execute(
                'SELECT session_id FROM user_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
                (user_id,)
            ).fetchone()
            
            if not session:
                return {}
            
            session_id = session['session_id']
        
        user_stats = self.db.get_session_stats(session_id)
        category_mastery = self.calculate_category_mastery(user_stats.get('by_category', []))
        user_level = self.calculate_user_level(user_stats)
        
        # Identify strengths and weaknesses
        strengths = [cat for cat, mastery in category_mastery.items() if mastery >= 0.8]
        weaknesses = [cat for cat, mastery in category_mastery.items() if mastery < 0.5]
        
        # Calculate learning velocity
        with self.db.get_connection() as conn:
            recent_performance = conn.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as attempts,
                    SUM(is_correct) as correct,
                    AVG(time_taken_seconds) as avg_time
                FROM user_progress
                WHERE user_id = ? AND timestamp >= DATE('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            ''', (user_id,)).fetchall()
        
        # Calculate trend
        if len(recent_performance) >= 3:
            recent_accuracy = [row['correct'] / row['attempts'] for row in recent_performance[:3]]
            trend = 'improving' if recent_accuracy[0] > recent_accuracy[-1] else 'stable'
        else:
            trend = 'insufficient_data'
        
        insights = {
            'user_level': user_level,
            'strengths': strengths[:3],
            'weaknesses': weaknesses[:3],
            'trend': trend,
            'recommendations': [],
            'study_time_recommendation': None
        }
        
        # Generate recommendations
        if weaknesses:
            insights['recommendations'].append(
                f"Focus on {weaknesses[0]} - current mastery is only "
                f"{int(category_mastery[weaknesses[0]] * 100)}%"
            )
        
        if user_stats['overall']['avg_time'] > 20:
            insights['recommendations'].append(
                "Try to improve response speed - aim for under 15 seconds per question"
            )
        
        if user_stats['recent_performance']['accuracy'] < 60:
            insights['recommendations'].append(
                "Consider reviewing easier questions to build confidence"
            )
        
        # Optimal study time based on performance patterns
        if recent_performance:
            avg_daily_questions = sum(row['attempts'] for row in recent_performance) / len(recent_performance)
            if avg_daily_questions < 10:
                insights['study_time_recommendation'] = "Try to answer at least 10-15 questions daily"
            elif avg_daily_questions > 50:
                insights['study_time_recommendation'] = "Consider shorter, focused sessions"
            else:
                insights['study_time_recommendation'] = "Your study frequency is optimal"
        
        return insights

def create_ai_recommendations(user_id: int) -> Dict:
    """
    Convenience function to get AI recommendations for a user.
    """
    engine = AdaptiveLearningEngine()
    
    # Get optimal questions
    questions = engine.select_optimal_questions(user_id, count=10)
    
    # Get learning insights
    insights = engine.get_learning_insights(user_id)
    
    return {
        'recommended_questions': questions,
        'insights': insights
    }