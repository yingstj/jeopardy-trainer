"""AI Opponent system for Jaypardy - extracted from Streamlit app"""

import random
import time

# AI Personalities with different strengths
AI_PERSONALITIES = {
    "Ken Jennings": {
        "description": "All-around expert, especially strong in History and Literature",
        "strengths": ["HISTORY", "LITERATURE", "GEOGRAPHY", "WORDPLAY"],
        "weaknesses": ["POP CULTURE", "SPORTS"],
        "base_accuracy": 0.85,
        "speed": "fast"
    },
    "Watson": {
        "description": "Computer-like precision, excels at facts and data",
        "strengths": ["SCIENCE", "TECHNOLOGY", "BUSINESS", "MEDICINE"],
        "weaknesses": ["WORDPLAY", "POP CULTURE"],
        "base_accuracy": 0.90,
        "speed": "very fast"
    },
    "Brad Rutter": {
        "description": "Strategic player, strong in Entertainment and Pop Culture",
        "strengths": ["ENTERTAINMENT", "POP CULTURE", "SPORTS", "MUSIC"],
        "weaknesses": ["SCIENCE", "TECHNOLOGY"],
        "base_accuracy": 0.82,
        "speed": "medium"
    },
    "James Holzhauer": {
        "description": "Aggressive player, sports and gambling expert",
        "strengths": ["SPORTS", "GEOGRAPHY", "BUSINESS", "POLITICS"],
        "weaknesses": ["ART", "LITERATURE"],
        "base_accuracy": 0.88,
        "speed": "very fast"
    },
    "Balanced": {
        "description": "Average player with no particular strengths",
        "strengths": [],
        "weaknesses": [],
        "base_accuracy": 0.75,
        "speed": "medium"
    }
}

# AI Difficulty Settings
AI_DIFFICULTY = {
    "Easy": {
        "accuracy_modifier": -0.20,
        "buzzer_speed": 10.0,
        "daily_double_aggression": 0.3
    },
    "Medium": {
        "accuracy_modifier": 0,
        "buzzer_speed": 5.0,
        "daily_double_aggression": 0.5
    },
    "Hard": {
        "accuracy_modifier": 0.10,
        "buzzer_speed": 2.0,
        "daily_double_aggression": 0.8
    }
}

def simulate_ai_response(clue, category, difficulty, personality):
    """Simulate AI response based on difficulty and personality"""
    personality_data = AI_PERSONALITIES[personality]
    difficulty_data = AI_DIFFICULTY[difficulty]
    
    # Calculate accuracy based on personality and difficulty
    base_accuracy = personality_data["base_accuracy"]
    
    # Adjust for category strengths/weaknesses
    if category in personality_data["strengths"]:
        base_accuracy += 0.15
    elif category in personality_data["weaknesses"]:
        base_accuracy -= 0.20
    
    # Apply difficulty modifier
    final_accuracy = min(0.99, max(0.20, base_accuracy + difficulty_data["accuracy_modifier"]))
    
    # Determine if AI gets it right
    is_correct = random.random() < final_accuracy
    
    # Simulate thinking time based on personality speed
    speed_map = {
        "very fast": (0.5, 1.5),
        "fast": (1.0, 2.0),
        "medium": (1.5, 3.0),
        "slow": (2.0, 4.0)
    }
    min_time, max_time = speed_map[personality_data["speed"]]
    thinking_time = random.uniform(min_time, max_time)
    
    return is_correct, thinking_time

def simulate_buzzer_race(difficulty):
    """Simulate who wins the buzzer"""
    difficulty_data = AI_DIFFICULTY[difficulty]
    
    # Player reaction time (random between 0.5 and buzzer_speed seconds)
    max_player_time = difficulty_data["buzzer_speed"]
    player_time = random.uniform(0.5, max_player_time)
    
    # AI reaction time based on difficulty
    if difficulty == "Easy":
        # AI buzzes slowly on easy mode (7-10 seconds)
        ai_time = random.uniform(7.0, 10.0)
    elif difficulty == "Medium":
        # AI buzzes moderately on medium (3-5 seconds)
        ai_time = random.uniform(3.0, 5.0)
    else:  # Hard
        # AI buzzes quickly on hard (1-2 seconds)
        ai_time = random.uniform(1.0, 2.0)
    
    if player_time < ai_time:
        return "player", player_time
    else:
        return "ai", ai_time

def get_ai_daily_double_wager(ai_score, player_score, difficulty):
    """Determine AI's wager on Daily Double"""
    difficulty_data = AI_DIFFICULTY[difficulty]
    aggression = difficulty_data["daily_double_aggression"]
    
    # Base wager calculation
    if ai_score <= 0:
        max_wager = 1000
    else:
        max_wager = ai_score
    
    # Adjust based on game situation
    if ai_score < player_score:
        # Behind - more aggressive
        wager_percent = min(1.0, aggression + 0.2)
    elif ai_score > player_score * 2:
        # Way ahead - conservative
        wager_percent = max(0.2, aggression - 0.3)
    else:
        # Close game - normal aggression
        wager_percent = aggression
    
    wager = int(max_wager * wager_percent)
    return max(100, min(wager, max_wager))