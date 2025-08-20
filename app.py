import streamlit as st
import pandas as pd
import random
import re
import os
import datetime
import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import defaultdict
from typing import Dict, List

# Import the R2 data loader
from r2_jeopardy_data_loader import load_jeopardy_data_from_r2
# Import user manager
from user_manager import UserManager

# Challenge/Multiplayer Mode Functions
class ChallengeManager:
    """Manages multiplayer challenges between users"""
    
    def __init__(self):
        self.challenges_file = "challenges.json"
        self.challenges = self._load_challenges()
    
    def _load_challenges(self):
        """Load challenges from JSON file"""
        if os.path.exists(self.challenges_file):
            try:
                with open(self.challenges_file, 'r') as f:
                    return json.load(f)
            except:
                return {"active": [], "completed": []}
        return {"active": [], "completed": []}
    
    def _save_challenges(self):
        """Save challenges to JSON file"""
        with open(self.challenges_file, 'w') as f:
            json.dump(self.challenges, f, indent=2)
    
    def create_challenge(self, challenger: str, opponent: str, categories: list, num_questions: int = 10):
        """Create a new challenge"""
        challenge = {
            "id": datetime.datetime.now().isoformat(),
            "challenger": challenger,
            "opponent": opponent,
            "categories": categories,
            "num_questions": num_questions,
            "challenger_score": 0,
            "opponent_score": 0,
            "challenger_completed": False,
            "opponent_completed": False,
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat()
        }
        self.challenges["active"].append(challenge)
        self._save_challenges()
        return challenge["id"]
    
    def accept_challenge(self, challenge_id: str, username: str):
        """Accept a challenge"""
        for challenge in self.challenges["active"]:
            if challenge["id"] == challenge_id and challenge["opponent"] == username:
                challenge["status"] = "active"
                self._save_challenges()
                return True
        return False
    
    def complete_challenge(self, challenge_id: str, username: str, score: int):
        """Complete one side of a challenge"""
        for challenge in self.challenges["active"]:
            if challenge["id"] == challenge_id:
                if challenge["challenger"] == username:
                    challenge["challenger_score"] = score
                    challenge["challenger_completed"] = True
                elif challenge["opponent"] == username:
                    challenge["opponent_score"] = score
                    challenge["opponent_completed"] = True
                
                # If both completed, move to completed
                if challenge["challenger_completed"] and challenge["opponent_completed"]:
                    challenge["status"] = "completed"
                    challenge["winner"] = (challenge["challenger"] if challenge["challenger_score"] > challenge["opponent_score"]
                                         else challenge["opponent"] if challenge["opponent_score"] > challenge["challenger_score"]
                                         else "tie")
                    self.challenges["completed"].append(challenge)
                    self.challenges["active"].remove(challenge)
                
                self._save_challenges()
                return True
        return False
    
    def get_active_challenges(self, username: str):
        """Get active challenges for a user"""
        return [c for c in self.challenges["active"] 
                if c["challenger"] == username or c["opponent"] == username]
    
    def get_challenge_results(self, username: str):
        """Get completed challenges for a user"""
        return [c for c in self.challenges["completed"]
                if c["challenger"] == username or c["opponent"] == username]

# Online Users Simulation (for demo purposes)
class OnlineUsers:
    """Simulates online users for multiplayer mode"""
    
    def __init__(self):
        self.online_users = []
        self.last_update = datetime.datetime.now()
    
    def update_online_users(self, current_user: str):
        """Update list of online users (simulated)"""
        # In a real app, this would check a database or server
        # For demo, we'll simulate with random names
        bot_names = ["QuizMaster", "TriviaKing", "JeopardyPro", "BrainiacBot", 
                     "SmartPlayer", "QuickThinker", "FactFinder", "WiseOwl"]
        
        # Refresh every 30 seconds
        if (datetime.datetime.now() - self.last_update).seconds > 30:
            num_online = random.randint(3, 8)
            self.online_users = random.sample(bot_names, num_online)
            self.last_update = datetime.datetime.now()
        
        # Always include current user
        if current_user and current_user not in self.online_users:
            self.online_users.insert(0, current_user)
        
        return self.online_users
    
    def get_user_stats(self, username: str):
        """Get simulated stats for a user"""
        # In real app, would fetch from database
        return {
            "games_played": random.randint(10, 500),
            "win_rate": random.randint(40, 85),
            "avg_score": random.randint(60, 95),
            "rank": random.choice(["Bronze", "Silver", "Gold", "Platinum", "Diamond"])
        }

# Page configuration with custom icon
st.set_page_config(
    page_title="Jaypardy!",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 0rem 1rem;
    }
    
    /* Custom header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
        text-align: center;
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        text-align: center;
        margin-top: 0.3rem;
        font-size: 1rem;
    }
    
    /* Theme card */
    .theme-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 0.8rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
        font-weight: bold;
        font-size: 1.1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Clue card */
    .clue-card {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .clue-text {
        font-size: 1.3rem;
        color: #2c3e50;
        line-height: 1.6;
    }
    
    /* Score display */
    .score-container {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .score-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-bottom: 0.3rem;
    }
    
    .score-value {
        font-size: 1.8rem;
        font-weight: bold;
    }
    
    /* Timer styling */
    .timer-container {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 1rem;
    }
    
    /* Success and error messages */
    .stSuccess {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid;
    }
    
    .stError {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        font-weight: bold;
        border-radius: 8px;
        transition: transform 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Progress bar */
    .progress-bar {
        background: #e9ecef;
        height: 25px;
        border-radius: 12px;
        overflow: hidden;
        margin: 0.5rem 0;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 0.9rem;
        transition: width 0.3s ease;
    }
    
    /* Stats cards */
    .stat-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 0.8rem;
    }
    
    .stat-number {
        font-size: 1.5rem;
        font-weight: bold;
        color: #667eea;
    }
    
    .stat-label {
        color: #6c757d;
        font-size: 0.8rem;
        margin-top: 0.2rem;
    }
    
    /* Compact header stats */
    .header-stats {
        display: flex;
        justify-content: space-around;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    .header-stat {
        text-align: center;
    }
    
    .header-stat-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: white;
    }
    
    .header-stat-label {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.8);
    }
</style>
""", unsafe_allow_html=True)

class JeopardyCategoryAnalyzer:
    """Analyze and categorize Jeopardy categories into themes"""
    
    def __init__(self):
        # Define theme keywords and patterns
        self.theme_patterns = {
            "HISTORY": {
                "keywords": ["history", "historical", "ancient", "medieval", "war", "battle", 
                            "empire", "dynasty", "revolution", "civil war", "world war", 
                            "century", "era", "period", "ages", "civilization", "historic",
                            "past", "founding", "colonial", "conquest", "president", "king", 
                            "queen", "royal", "monarch"],
                "patterns": [r"\b\d{4}\b", r"\b\d{1,2}th century\b", r"\bwar\b", r"the \d{2,4}s"]
            },
            
            "GEOGRAPHY": {
                "keywords": ["geography", "countries", "cities", "states", "capitals", 
                            "nations", "world", "islands", "mountains", "rivers", "lakes",
                            "oceans", "continents", "maps", "places", "landmarks", "wonders",
                            "national parks", "territories", "regions", "hemispheres", "travel"],
                "patterns": [r"countries", r"u\.s\. states", r"capitals", r"cities of"]
            },
            
            "SCIENCE": {
                "keywords": ["science", "biology", "chemistry", "physics", "anatomy", 
                            "medicine", "astronomy", "geology", "meteorology", "elements",
                            "atoms", "molecules", "space", "planets", "stars", "medical",
                            "body", "human", "animals", "nature", "environment", "ecology",
                            "evolution", "genetics", "dna", "cells", "periodic table", "math",
                            "mathematics", "computer", "technology"],
                "patterns": [r"scientific", r"the body", r"in space"]
            },
            
            "LITERATURE": {
                "keywords": ["literature", "books", "novels", "authors", "writers", "poets",
                            "poetry", "poems", "shakespeare", "classics", "fiction", 
                            "characters", "novels", "stories", "tales", "fables", "plays",
                            "playwright", "literary", "reading", "bibliography", "novel"],
                "patterns": [r"shakespeare", r"authors?", r"literat", r"book"]
            },
            
            "ENTERTAINMENT": {
                "keywords": ["movies", "films", "cinema", "hollywood", "actors", "actresses",
                            "oscars", "academy awards", "directors", "television", "tv",
                            "shows", "series", "sitcom", "drama", "comedy", "entertainment",
                            "celebrities", "stars", "emmys", "tonys", "grammys", "awards",
                            "music", "songs", "singers", "bands", "albums", "composers"],
                "patterns": [r"at the movies", r"on tv", r"oscar", r"film", r"music"]
            },
            
            "SPORTS": {
                "keywords": ["sports", "football", "baseball", "basketball", "hockey",
                            "soccer", "tennis", "golf", "olympics", "athletes", "teams",
                            "championship", "tournament", "league", "nfl", "nba", "mlb",
                            "nhl", "fifa", "espn", "stadium", "arena", "game", "match",
                            "player", "coach", "referee", "score", "bowl", "cup"],
                "patterns": [r"sports", r"olympi", r"super bowl", r"world cup"]
            },
            
            "BUSINESS": {
                "keywords": ["business", "company", "corporation", "brand", "ceo", "economy",
                            "money", "dollar", "bank", "finance", "stock", "market", "trade",
                            "industry", "commerce", "entrepreneur", "startup", "investment",
                            "wall street", "nasdaq", "fortune"],
                "patterns": [r"business", r"compan", r"corporate", r"\$\d+", r"money"]
            },
            
            "FOOD & DRINK": {
                "keywords": ["food", "cuisine", "cooking", "chef", "recipe", "restaurant",
                            "meal", "dish", "ingredient", "flavor", "taste", "drink",
                            "beverage", "wine", "beer", "cocktail", "coffee", "tea",
                            "fruit", "vegetable", "meat", "dessert", "kitchen"],
                "patterns": [r"food", r"cook", r"eat", r"drink", r"cuisine"]
            },
            
            "WORDPLAY": {
                "keywords": ["rhyme", "rhyming", "pun", "anagram", "palindrome", "crossword",
                            "puzzle", "riddle", "wordplay", "scramble", "spell", "letter",
                            "before & after", "before and after", "quotation", "phrase"],
                "patterns": [r"rhym", r"pun", r"anagram", r"wordplay", r"before.*after"]
            },
            
            "POP CULTURE": {
                "keywords": ["pop culture", "celebrity", "famous", "trend", "fashion", "style",
                            "social media", "internet", "meme", "viral", "modern", "contemporary",
                            "current", "today", "recent", "millennial", "gen z", "popular"],
                "patterns": [r"pop cultur", r"celebrit", r"fashion", r"modern"]
            },
            
            "RELIGION & MYTHOLOGY": {
                "keywords": ["religion", "religious", "god", "goddess", "bible", "church",
                            "faith", "mythology", "myth", "legend", "zeus", "greek god",
                            "roman god", "norse", "saint", "prophet", "temple", "sacred",
                            "holy", "worship", "prayer", "spiritual"],
                "patterns": [r"relig", r"god", r"myth", r"bible", r"saint"]
            },
            
            "GENERAL KNOWLEDGE": {
                "keywords": ["potpourri", "hodgepodge", "mixed", "general", "trivia",
                            "miscellaneous", "variety", "assorted"],
                "patterns": [r"potpourri", r"hodgepodge", r"mixed bag"]
            }
        }
    
    def categorize_single(self, category: str) -> str:
        """Categorize a single category string into a theme"""
        if not category:
            return "GENERAL KNOWLEDGE"
        
        category_lower = str(category).lower()
        theme_scores = {}
        
        # Score each theme based on keyword matches
        for theme, criteria in self.theme_patterns.items():
            score = 0
            
            # Check keywords
            for keyword in criteria["keywords"]:
                if keyword in category_lower:
                    score += len(keyword)  # Longer matches score higher
            
            # Check patterns
            for pattern in criteria["patterns"]:
                if re.search(pattern, category_lower):
                    score += 10
            
            if score > 0:
                theme_scores[theme] = score
        
        # Return the theme with highest score, or GENERAL KNOWLEDGE if no match
        if theme_scores:
            return max(theme_scores.items(), key=lambda x: x[1])[0]
        else:
            return "GENERAL KNOWLEDGE"
    
    def group_categories_by_theme(self, categories: List[str]) -> Dict[str, List[str]]:
        """Group all categories into themes"""
        theme_groups = defaultdict(list)
        
        for category in categories:
            theme = self.categorize_single(category)
            theme_groups[theme].append(category)
        
        # Sort themes by number of categories (most popular first)
        sorted_themes = dict(sorted(theme_groups.items(), 
                                  key=lambda x: len(x[1]), 
                                  reverse=True))
        
        return sorted_themes

# Load model once
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_model()

# Normalize text for fuzzy matching
def normalize(text):
    text = text.lower()
    text = re.sub(r"^(what|who|where|when|why|how)\s+(is|are|was|were)\s+", "", text)
    text = re.sub(r"^(a|an|the)\s+", "", text)  # Remove articles
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()

# Fuzzy matching function
def fuzzy_match(user_answer, correct_answer, threshold=70):
    """Check if user answer is close enough to correct answer"""
    # First try exact match after normalization
    user_norm = normalize(user_answer)
    correct_norm = normalize(correct_answer)
    
    if user_norm == correct_norm:
        return True
    
    # Special handling for names - accept last name only
    correct_words = correct_norm.split()
    user_words = user_norm.split()
    
    # If correct answer is a person's name (2-3 words) and user gave last word (last name)
    if len(correct_words) >= 2 and len(user_words) == 1:
        # Check if user answer matches last name
        if user_norm == correct_words[-1]:
            return True
        # Also check if it matches any significant word in the answer
        for word in correct_words:
            if len(word) > 4 and user_norm == word:  # Significant word (>4 chars)
                return True
    
    # Check if user gave multiple words that include the key part
    if len(user_words) > 1 and len(correct_words) > 1:
        # Check if last names match
        if user_words[-1] == correct_words[-1]:
            return True
    
    # Check if user answer contains the key parts of correct answer or vice versa
    if len(user_norm) > 3 and len(correct_norm) > 3:
        # For substring matching, be more lenient
        if user_norm in correct_norm:
            # User answer is contained in correct answer
            # Accept if it's a significant portion (>40% of correct answer)
            if len(user_norm) / len(correct_norm) > 0.4:
                return True
        if correct_norm in user_norm:
            return True
    
    # For very short answers, require exact match
    if len(user_norm) <= 3 or len(correct_norm) <= 3:
        return user_norm == correct_norm
    
    # Calculate word-based similarity for multi-word answers
    if len(correct_words) > 1 and len(user_words) > 0:
        matching_words = sum(1 for word in user_words if word in correct_words)
        if matching_words / len(correct_words) >= 0.5:  # At least 50% of words match
            return True
    
    # Character-based similarity as fallback
    # Use Levenshtein-like distance
    max_len = max(len(user_norm), len(correct_norm))
    if max_len == 0:
        return False
    
    # Count character differences
    differences = abs(len(user_norm) - len(correct_norm))
    min_len = min(len(user_norm), len(correct_norm))
    
    for i in range(min_len):
        if i < len(user_norm) and i < len(correct_norm):
            if user_norm[i] != correct_norm[i]:
                differences += 1
    
    similarity = ((max_len - differences) / max_len) * 100
    return similarity >= threshold

# Load and filter data
@st.cache_data
def load_data():
    # Check if we're in a GitHub Actions environment (for CI testing)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        # Return a small sample dataset for testing
        return pd.DataFrame({
            'category': ['HISTORY', 'SCIENCE', 'MOVIES', 'LITERATURE', 'GEOGRAPHY'],
            'clue': ['First president of the US', 'Element with symbol H', 'This film won Best Picture in 2020', 
                    'Author of Romeo and Juliet', 'Capital of France'],
            'correct_response': ['George Washington', 'Hydrogen', 'Parasite', 'William Shakespeare', 'Paris'],
            'round': ['Jeopardy', 'Jeopardy', 'Double Jeopardy', 'Jeopardy', 'Final Jeopardy'],
            'game_id': ['1', '1', '2', '2', '3']
        })
    
    try:
        # Load from R2
        with st.spinner("🎯 Loading dataset from Cloudflare R2..."):
            df = load_jeopardy_data_from_r2()
        
        if df.empty:
            st.error("Failed to load dataset from R2. Please check your connection and credentials.")
            return pd.DataFrame()
        
        df = df.dropna(subset=["clue", "correct_response"])
        
        # Compute embeddings (can be expensive, so we'll do it on demand)
        with st.spinner("🧮 Computing clue embeddings..."):
            # Process in batches to avoid memory issues
            batch_size = min(1000, len(df))
            sample_df = df.sample(n=batch_size) if len(df) > batch_size else df
            sample_df["clue_embedding"] = sample_df["clue"].apply(lambda x: model.encode(x))
            return sample_df
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Initialize user manager
user_manager = UserManager()

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "user_data" not in st.session_state:
    st.session_state.user_data = None

if "history" not in st.session_state:
    st.session_state.history = []

if "score" not in st.session_state:
    st.session_state.score = 0
    st.session_state.total = 0

if "start_time" not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()

if "current_clue" not in st.session_state:
    st.session_state.current_clue = None

if "progress_data" not in st.session_state:
    st.session_state.progress_data = []

if "streak" not in st.session_state:
    st.session_state.streak = 0
    st.session_state.best_streak = 0

if "bookmarks" not in st.session_state:
    st.session_state.bookmarks = []

if "notes" not in st.session_state:
    st.session_state.notes = {}

if "daily_double_used" not in st.session_state:
    st.session_state.daily_double_used = False

if "achievements" not in st.session_state:
    st.session_state.achievements = []

if "study_mode" not in st.session_state:
    st.session_state.study_mode = False

if "weak_themes" not in st.session_state:
    st.session_state.weak_themes = {}

if "viewing_bookmark" not in st.session_state:
    st.session_state.viewing_bookmark = None

if "ai_mode" not in st.session_state:
    st.session_state.ai_mode = False
    st.session_state.ai_difficulty = "Medium"
    st.session_state.ai_personality = "Balanced"
    st.session_state.ai_score = 0
    st.session_state.ai_streak = 0
    st.session_state.current_turn = "player"
    st.session_state.buzzer_winner = None
    st.session_state.ai_thinking = False
    st.session_state.match_history = []

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
        "buzzer_speed": 10.0,  # 10 seconds to buzz in
        "daily_double_aggression": 0.3
    },
    "Medium": {
        "accuracy_modifier": 0,
        "buzzer_speed": 5.0,  # 5 seconds to buzz in
        "daily_double_aggression": 0.5
    },
    "Hard": {
        "accuracy_modifier": 0.10,
        "buzzer_speed": 2.0,  # 2 seconds to buzz in
        "daily_double_aggression": 0.8
    }
}

def simulate_ai_response(clue, category, difficulty, personality):
    """Simulate AI response based on difficulty and personality"""
    import time
    
    personality_data = AI_PERSONALITIES[personality]
    difficulty_data = AI_DIFFICULTY[difficulty]
    
    # Calculate accuracy based on personality and difficulty
    base_accuracy = personality_data["base_accuracy"]
    
    # Adjust for category strengths/weaknesses
    theme = analyzer.categorize_single(category)
    if theme in personality_data["strengths"]:
        base_accuracy += 0.15
    elif theme in personality_data["weaknesses"]:
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
    
    # AI reaction time based on difficulty (will try to buzz somewhere in the time window)
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

if "selected_categories" not in st.session_state:
    st.session_state.selected_categories = None

if "time_limit" not in st.session_state:
    st.session_state.time_limit = 30

if "speed_round" not in st.session_state:
    st.session_state.speed_round = False

# Login Screen
if not st.session_state.authenticated:
    # Custom CSS for login page
    st.markdown("""
    <style>
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-title {
            font-size: 3rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .login-subtitle {
            color: #6c757d;
            font-size: 1.1rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Login container
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-header">
            <div class="login-title">🎯 Jaypardy!</div>
            <div class="login-subtitle">Test your trivia knowledge with real Jeopardy questions</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Tab selection for Sign In / Sign Up
        tab1, tab2 = st.tabs(["🔑 Sign In", "✨ Create Account"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username:", placeholder="Enter your username")
                password = st.text_input("Password:", type="password", placeholder="Enter your password")
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("🎮 Sign In", use_container_width=True, type="primary")
                with col2:
                    guest = st.form_submit_button("👤 Play as Guest", use_container_width=True)
                
                if submitted:
                    if username.strip() and password:
                        if user_manager.authenticate(username.strip(), password):
                            st.session_state.authenticated = True
                            st.session_state.username = username.strip()
                            st.session_state.user_data = user_manager.get_user_data(username.strip())
                            
                            # Load user's saved data
                            if st.session_state.user_data:
                                stats = st.session_state.user_data["stats"]
                                st.session_state.best_streak = stats.get("best_streak", 0)
                                st.session_state.bookmarks = stats.get("bookmarks", [])
                            
                            st.success(f"Welcome back, {username}! Loading your profile...")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    else:
                        st.error("Please enter both username and password")
                
                if guest:
                    st.session_state.authenticated = True
                    st.session_state.username = f"Guest_{random.randint(1000, 9999)}"
                    st.info("Playing as guest - progress won't be saved")
                    st.rerun()
        
        with tab2:
            with st.form("signup_form"):
                new_username = st.text_input("Choose a username:", placeholder="Pick a unique username")
                new_password = st.text_input("Create password:", type="password", placeholder="At least 4 characters")
                confirm_password = st.text_input("Confirm password:", type="password", placeholder="Re-enter password")
                
                create_account = st.form_submit_button("🌟 Create Account", use_container_width=True, type="primary")
                
                if create_account:
                    if new_username.strip() and new_password:
                        if len(new_password) < 4:
                            st.error("Password must be at least 4 characters long")
                        elif new_password != confirm_password:
                            st.error("Passwords don't match")
                        elif user_manager.user_exists(new_username.strip()):
                            st.error("Username already taken. Please choose another.")
                        else:
                            if user_manager.create_user(new_username.strip(), new_password):
                                st.success("Account created! You can now sign in.")
                                st.balloons()
                            else:
                                st.error("Failed to create account. Please try again.")
                    else:
                        st.error("Please fill in all fields")
        
        # Fun facts while waiting
        st.markdown("---")
        st.markdown("### 📚 Did you know?")
        facts = [
            "Jeopardy! has been on air since 1984",
            "Over 400,000 questions have been asked on Jeopardy!",
            "The highest single-day winnings record is $131,127",
            "Ken Jennings won 74 consecutive games",
            "The show has won 39 Emmy Awards"
        ]
        st.info(random.choice(facts))
    
    st.stop()

# Loading data (only after authentication)
df = load_data()

if df.empty:
    st.error("❌ Failed to load Jeopardy dataset.")
    st.info("Check your internet connection or contact the administrator.")
    st.stop()

# Initialize analyzer and categories
analyzer = JeopardyCategoryAnalyzer()
all_categories = df["category"].unique()
theme_groups = analyzer.group_categories_by_theme(all_categories)

# SIDEBAR FOR SETTINGS
with st.sidebar:
    st.markdown("## 🎯 Jaypardy!")
    if st.session_state.username:
        st.markdown(f"👤 **Player:** {st.session_state.username}")
        
        # Show lifetime stats for registered users
        if st.session_state.user_data and not st.session_state.username.startswith("Guest_"):
            with st.expander("📊 Lifetime Stats", expanded=False):
                stats = st.session_state.user_data["stats"]
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Games", stats.get("games_played", 0))
                    st.metric("Total Score", stats.get("total_score", 0))
                with col2:
                    st.metric("Questions", stats.get("total_questions", 0))
                    if stats.get("total_questions", 0) > 0:
                        acc = (stats.get("correct_answers", 0) / stats.get("total_questions", 1)) * 100
                        st.metric("Accuracy", f"{acc:.1f}%")
    st.markdown("---")
    
    # Score display in sidebar
    st.markdown(f"""
    <div class="score-container">
        <div class="score-label">Score</div>
        <div class="score-value">{st.session_state.score} / {st.session_state.total}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Progress bar
    if st.session_state.total > 0:
        accuracy = (st.session_state.score / st.session_state.total) * 100
        st.markdown(f"""
        <div class="progress-bar">
            <div class="progress-fill" style="width: {accuracy}%">
                {accuracy:.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Streak display
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{st.session_state.streak}</div>
            <div class="stat-label">Streak</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{st.session_state.best_streak}</div>
            <div class="stat-label">Best</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Theme selection
    st.markdown("### 📚 Theme Selection")
    
    # Quick picks - default to All (all themes)
    quick_pick = st.selectbox(
        "Quick Pick:",
        ["📚 All", "Custom Selection", "🎓 Academic", "🎬 Entertainment", "🌍 World"],
        key="quick_pick",
        index=0  # Default to All
    )
    
    if quick_pick == "📚 All":
        selected_categories = list(all_categories)
    elif quick_pick == "Custom Selection":
        # Theme selector - show ALL themes
        theme_options = []
        theme_mapping = {}
        
        # Sort themes by number of categories (most first)
        sorted_themes = sorted(theme_groups.items(), key=lambda x: len(x[1]), reverse=True)
        
        for theme, cats in sorted_themes:
            # Show all themes, even with 1 category
            display_name = f"{theme} ({len(cats)} categories)"
            theme_options.append(display_name)
            theme_mapping[display_name] = theme
        
        # Show total available
        st.caption(f"📊 {len(theme_groups)} themes available from {len(all_categories)} total categories")
        
        selected_theme_displays = st.multiselect(
            "Select themes:",
            theme_options,
            default=theme_options[:5] if len(theme_options) >= 5 else theme_options,  # Default to top 5
            help="Select multiple themes to include their categories"
        )
        
        selected_categories = []
        for display in selected_theme_displays:
            theme_name = theme_mapping.get(display)
            if theme_name and theme_name in theme_groups:
                selected_categories.extend(theme_groups[theme_name])
        
        # Remove duplicates (some categories might be in multiple themes)
        selected_categories = list(set(selected_categories))
    elif quick_pick == "🎓 Academic":
        selected_categories = []
        for theme in ["HISTORY", "SCIENCE", "LITERATURE", "GEOGRAPHY"]:
            if theme in theme_groups:
                selected_categories.extend(theme_groups[theme])
    elif quick_pick == "🎬 Entertainment":
        selected_categories = []
        for theme in ["ENTERTAINMENT", "POP CULTURE", "SPORTS"]:
            if theme in theme_groups:
                selected_categories.extend(theme_groups[theme])
    elif quick_pick == "🌍 World":
        selected_categories = []
        for theme in ["GEOGRAPHY", "HISTORY", "RELIGION & MYTHOLOGY"]:
            if theme in theme_groups:
                selected_categories.extend(theme_groups[theme])
    
    if selected_categories:
        st.session_state.selected_categories = selected_categories
        st.success(f"✅ {len(selected_categories)} categories selected")
        
        # Show sample categories in an expander
        with st.expander("View selected categories", expanded=False):
            # Show first 20 categories as a sample
            sample_size = min(20, len(selected_categories))
            sample_cats = sorted(selected_categories)[:sample_size]
            
            for i in range(0, sample_size, 2):
                col1, col2 = st.columns(2)
                with col1:
                    if i < len(sample_cats):
                        st.caption(f"• {sample_cats[i]}")
                with col2:
                    if i+1 < len(sample_cats):
                        st.caption(f"• {sample_cats[i+1]}")
            
            if len(selected_categories) > sample_size:
                st.caption(f"... and {len(selected_categories) - sample_size} more categories")
    
    st.markdown("---")
    
    # AI Opponent Settings
    st.markdown("### 🤖 AI Opponent")
    st.session_state.ai_mode = st.checkbox(
        "Play against AI",
        value=st.session_state.ai_mode,
        help="Enable AI opponent for competitive play"
    )
    
    if st.session_state.ai_mode:
        # AI Personality selector
        st.session_state.ai_personality = st.selectbox(
            "Choose Opponent:",
            list(AI_PERSONALITIES.keys()),
            index=list(AI_PERSONALITIES.keys()).index(st.session_state.ai_personality)
        )
        
        personality = AI_PERSONALITIES[st.session_state.ai_personality]
        st.caption(f"*{personality['description']}*")
        
        # Difficulty selector
        difficulties = ["Easy", "Medium", "Hard"]
        # Handle if user had Impossible selected before
        if st.session_state.ai_difficulty not in difficulties:
            st.session_state.ai_difficulty = "Medium"
        
        st.session_state.ai_difficulty = st.selectbox(
            "Difficulty:",
            difficulties,
            index=difficulties.index(st.session_state.ai_difficulty)
        )
        
        # Show AI stats
        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            st.metric("AI Score", st.session_state.ai_score)
        with col_ai2:
            st.metric("AI Streak", st.session_state.ai_streak)
    
    st.markdown("---")
    
    # Game settings
    st.markdown("### ⚙️ Settings")
    
    # Timer toggle - default to off
    use_timer = st.checkbox(
        "⏱️ Use Timer",
        value=False,
        help="Enable/disable time limit for answers",
        key="use_timer"
    )
    
    # Time limit (only show if timer is enabled)
    if use_timer:
        # Only update if it's a valid number
        if isinstance(st.session_state.time_limit, (int, float)) and st.session_state.time_limit != 999999:
            default_time = int(st.session_state.time_limit)
        else:
            default_time = 30
        
        st.session_state.time_limit = st.slider(
            "Time (seconds):",
            10, 60, default_time
        )
    else:
        st.session_state.time_limit = 999999  # Very large number instead of infinity
    
    # Study Mode
    st.session_state.study_mode = st.checkbox(
        "📚 Study Mode",
        value=st.session_state.study_mode,
        help="No timer, see answers immediately"
    )
    
    # Speed Round (only available if timer is on)
    if use_timer:
        st.session_state.speed_round = st.checkbox(
            "⚡ Speed Round",
            help="5-second timer, 2x points"
        )
        if st.session_state.speed_round:
            st.session_state.time_limit = 5
    else:
        st.session_state.speed_round = False
    
    # Round selector (difficulty)
    if 'round' in df.columns:
        rounds = df['round'].dropna().unique().tolist()
        round_options = ['All Rounds'] + sorted(rounds)
        selected_round = st.selectbox(
            "📈 Difficulty (Round):",
            round_options,
            help="Filter by Jeopardy round"
        )
        st.session_state.selected_round = selected_round
    
    st.markdown("---")
    
    # Quick actions
    if st.button("🎯 New Question", use_container_width=True):
        st.session_state.current_clue = None
        st.rerun()
    
    if st.button("🔁 Adaptive Mode", use_container_width=True, help="Focus on weak themes & missed questions"):
        if st.session_state.history:
            # Calculate performance by category
            history_df = pd.DataFrame(st.session_state.history)
            category_stats = history_df.groupby("category").agg({
                "was_correct": ["sum", "count"]
            })
            category_stats.columns = ["correct", "total"]
            category_stats["accuracy"] = category_stats["correct"] / category_stats["total"]
            
            # Find weak categories (accuracy < 50% or all wrong)
            weak_categories = category_stats[category_stats["accuracy"] < 0.5].index.tolist()
            
            # Get missed questions from weak categories first, then any missed
            missed = [h for h in st.session_state.history if not h["was_correct"]]
            weak_missed = [h for h in missed if h["category"] in weak_categories]
            
            # Prioritize weak category misses, then regular misses
            retry_pool = weak_missed if weak_missed else missed
            
            if retry_pool:
                # Weight selection towards more recent misses
                weights = [0.5 + 0.5 * (i / len(retry_pool)) for i in range(len(retry_pool))]
                retry = random.choices(retry_pool, weights=weights, k=1)[0]
                
                st.session_state.current_clue = {
                    "category": retry["category"],
                    "clue": retry["clue"],
                    "correct_response": retry["correct_response"]
                }
                st.info(f"📚 Focusing on weak theme: {retry['category']}")
                st.rerun()
            else:
                st.success("🎉 Great job! No missed questions to retry!")
        else:
            st.info("Play some questions first to enable adaptive mode!")
    
    if st.button("🔄 Reset Game", use_container_width=True):
        for key in ["score", "total", "streak", "history", "daily_double_used"]:
            if key in st.session_state:
                if key in ["score", "total", "streak"]:
                    st.session_state[key] = 0
                elif key == "history":
                    st.session_state[key] = []
                else:
                    st.session_state[key] = False
        st.rerun()
    
    st.markdown("---")
    
    # Challenge Mode Section
    st.markdown("### 🏆 Challenge Mode")
    
    # Initialize challenge manager and online users
    if "challenge_manager" not in st.session_state:
        st.session_state.challenge_manager = ChallengeManager()
    if "online_users" not in st.session_state:
        st.session_state.online_users = OnlineUsers()
    
    challenge_manager = st.session_state.challenge_manager
    online_users = st.session_state.online_users
    
    # Update online users list
    online_list = online_users.update_online_users(st.session_state.username)
    
    # Show online users
    with st.expander(f"🟢 Online Users ({len(online_list)})", expanded=False):
        for user in online_list:
            if user != st.session_state.username:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"👤 {user}")
                with col2:
                    if st.button("⚔️", key=f"challenge_{user}", help=f"Challenge {user}"):
                        # Create a challenge
                        challenge_id = challenge_manager.create_challenge(
                            st.session_state.username, 
                            user,
                            selected_categories[:10],  # Use first 10 categories
                            num_questions=10
                        )
                        st.success(f"Challenge sent to {user}!")
    
    # Show active challenges
    active_challenges = challenge_manager.get_active_challenges(st.session_state.username)
    if active_challenges:
        with st.expander(f"⚔️ Active Challenges ({len(active_challenges)})", expanded=False):
            for challenge in active_challenges:
                opponent = challenge["opponent"] if challenge["challenger"] == st.session_state.username else challenge["challenger"]
                status_emoji = "⏳" if challenge["status"] == "pending" else "🎮"
                
                st.write(f"{status_emoji} vs **{opponent}**")
                
                # Show scores if available
                if challenge["challenger_completed"] or challenge["opponent_completed"]:
                    your_score = challenge["challenger_score"] if challenge["challenger"] == st.session_state.username else challenge["opponent_score"]
                    their_score = challenge["opponent_score"] if challenge["challenger"] == st.session_state.username else challenge["challenger_score"]
                    your_done = challenge["challenger_completed"] if challenge["challenger"] == st.session_state.username else challenge["opponent_completed"]
                    their_done = challenge["opponent_completed"] if challenge["challenger"] == st.session_state.username else challenge["challenger_completed"]
                    
                    st.write(f"You: {your_score} {'✅' if your_done else '⏳'}")
                    st.write(f"{opponent}: {their_score if their_done else '---'} {'✅' if their_done else '⏳'}")
                
                # Accept button for pending challenges
                if challenge["status"] == "pending" and challenge["opponent"] == st.session_state.username:
                    if st.button("✅ Accept", key=f"accept_{challenge['id']}"):
                        challenge_manager.accept_challenge(challenge["id"], st.session_state.username)
                        st.success("Challenge accepted!")
                        st.rerun()
                
                # Play button for active challenges
                elif challenge["status"] == "active":
                    your_completed = challenge["challenger_completed"] if challenge["challenger"] == st.session_state.username else challenge["opponent_completed"]
                    if not your_completed:
                        if st.button("🎮 Play", key=f"play_{challenge['id']}"):
                            st.session_state.current_challenge = challenge
                            st.session_state.challenge_mode = True
                            st.session_state.challenge_question_num = 0
                            st.session_state.challenge_score = 0
                            st.rerun()
                
                st.markdown("---")
    
    # Show completed challenges
    completed = challenge_manager.get_challenge_results(st.session_state.username)
    if completed:
        with st.expander(f"🏅 Results ({len(completed)})", expanded=False):
            for challenge in completed[-5:]:  # Show last 5
                opponent = challenge["opponent"] if challenge["challenger"] == st.session_state.username else challenge["challenger"]
                your_score = challenge["challenger_score"] if challenge["challenger"] == st.session_state.username else challenge["opponent_score"]
                their_score = challenge["opponent_score"] if challenge["challenger"] == st.session_state.username else challenge["challenger_score"]
                
                if challenge["winner"] == st.session_state.username:
                    result_emoji = "🏆"
                    result_text = "Won"
                elif challenge["winner"] == "tie":
                    result_emoji = "🤝"
                    result_text = "Tied"
                else:
                    result_emoji = "😔"
                    result_text = "Lost"
                
                st.write(f"{result_emoji} **{result_text}** vs {opponent}")
                st.write(f"Score: {your_score} - {their_score}")
                st.markdown("---")
    
    st.markdown("---")
    
    if st.button("🚪 Logout", use_container_width=True):
        # Save user session before logging out
        if st.session_state.user_data and not st.session_state.username.startswith("Guest_"):
            session_data = {
                "total_questions": st.session_state.total,
                "correct_answers": st.session_state.score,
                "score": st.session_state.score,
                "best_streak": st.session_state.best_streak,
                "bookmarks": st.session_state.bookmarks
            }
            user_manager.save_user_session(st.session_state.username, session_data)
        
        # Clear session
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.user_data = None
        st.rerun()

# MAIN GAME AREA

# Check if viewing a bookmark
if st.session_state.viewing_bookmark:
    st.info("📖 Viewing Bookmarked Question")
    bookmark = st.session_state.viewing_bookmark
    
    st.markdown(f"""
    <div class="theme-card">
        BOOKMARKED: {bookmark['category']}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="clue-card">
        <div class="clue-text">{bookmark['clue']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📖 View Answer", expanded=True):
        st.success(f"**Answer:** {bookmark['correct_response']}")
        
        # Note section for bookmark
        note_key = f"{bookmark['category']}_{bookmark['clue'][:50]}"
        existing_note = st.session_state.notes.get(note_key, "")
        new_note = st.text_area(
            "📝 Edit note for this bookmark:",
            value=existing_note,
            placeholder="Add memory tricks, related facts, etc."
        )
        if new_note != existing_note:
            st.session_state.notes[note_key] = new_note
    
    if st.button("↩️ Back to Game", use_container_width=True):
        st.session_state.viewing_bookmark = None
        st.rerun()
    
    st.stop()  # Don't show the regular game when viewing bookmark

# Show different header for AI mode vs regular mode
if st.session_state.ai_mode:
    # AI Mode - Show both player and AI scores
    st.markdown("""<div class="main-header"><h1>🎯 Jaypardy!</h1></div>""", unsafe_allow_html=True)
    
    col_player, col_vs, col_ai = st.columns([2, 1, 2])
    
    with col_player:
        player_color = "#667eea" if st.session_state.score >= st.session_state.ai_score else "#6c757d"
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, {player_color} 0%, #764ba2 100%); 
                    border-radius: 10px; color: white;">
            <div style="font-size: 0.9rem; opacity: 0.9;">👤 {st.session_state.username}</div>
            <div style="font-size: 2.5rem; font-weight: bold;">${st.session_state.score}</div>
            <div style="font-size: 0.8rem; opacity: 0.8;">Streak: {st.session_state.streak}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_vs:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0;">
            <div style="font-size: 1.5rem; font-weight: bold; color: #6c757d;">VS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_ai:
        ai_color = "#dc3545" if st.session_state.ai_score > st.session_state.score else "#6c757d"
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, {ai_color} 0%, #495057 100%); 
                    border-radius: 10px; color: white;">
            <div style="font-size: 0.9rem; opacity: 0.9;">🤖 {st.session_state.ai_personality}</div>
            <div style="font-size: 2.5rem; font-weight: bold;">${st.session_state.ai_score}</div>
            <div style="font-size: 0.8rem; opacity: 0.8;">Streak: {st.session_state.ai_streak}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Show who's winning
    if st.session_state.buzzer_winner:
        if st.session_state.buzzer_winner == "player":
            st.success(f"🎯 You buzzed in first! Your turn to answer.")
        else:
            st.info(f"🤖 {st.session_state.ai_personality} buzzed in first!")
else:
    # Regular mode header
    st.markdown(f"""
    <div class="main-header">
        <h1>🎯 Jaypardy!</h1>
        <div class="header-stats">
            <div class="header-stat">
                <div class="header-stat-value">{st.session_state.score}</div>
                <div class="header-stat-label">Score</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value">{st.session_state.total}</div>
                <div class="header-stat-label">Questions</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value">{st.session_state.streak}</div>
                <div class="header-stat-label">Streak</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value">{f"{(st.session_state.score/st.session_state.total*100):.0f}%" if st.session_state.total > 0 else "-"}</div>
                <div class="header-stat-label">Accuracy</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Check if categories are selected
if not st.session_state.selected_categories:
    st.warning("⚠️ Please select themes from the sidebar to start playing!")
    st.stop()

filtered_df = df[df["category"].isin(st.session_state.selected_categories)]

# Apply round filter if selected
if 'selected_round' in st.session_state and st.session_state.selected_round != 'All Rounds':
    filtered_df = filtered_df[filtered_df['round'] == st.session_state.selected_round]

if filtered_df.empty:
    st.warning("No clues found for selected themes/round. Please adjust your selection.")
    st.stop()

# Challenge Mode Game Logic
if "challenge_mode" in st.session_state and st.session_state.challenge_mode:
    challenge = st.session_state.current_challenge
    opponent = challenge["opponent"] if challenge["challenger"] == st.session_state.username else challenge["challenger"]
    
    # Display challenge header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FF6B6B 0%, #4ECDC4 100%); 
                color: white; padding: 1.5rem; border-radius: 15px; 
                text-align: center; margin-bottom: 1rem;">
        <h2 style="margin: 0;">⚔️ Challenge Mode</h2>
        <p style="margin: 0.5rem 0;">You vs {opponent}</p>
        <p style="margin: 0;">Question {st.session_state.challenge_question_num + 1} of {challenge['num_questions']}</p>
        <p style="margin: 0; font-size: 1.2rem;">Your Score: {st.session_state.challenge_score}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if challenge is complete
    if st.session_state.challenge_question_num >= challenge["num_questions"]:
        # Complete the challenge
        challenge_manager.complete_challenge(
            challenge["id"],
            st.session_state.username,
            st.session_state.challenge_score
        )
        
        st.success(f"Challenge complete! Your score: {st.session_state.challenge_score}/{challenge['num_questions']}")
        
        # Reset challenge mode
        st.session_state.challenge_mode = False
        st.session_state.current_challenge = None
        st.session_state.challenge_question_num = 0
        st.session_state.challenge_score = 0
        
        if st.button("Back to Normal Mode", type="primary"):
            st.rerun()
        st.stop()
    
    # Use challenge categories
    challenge_df = df[df["category"].isin(challenge["categories"])]
    if challenge_df.empty:
        challenge_df = filtered_df  # Fallback to regular filtered df
    
    # Get challenge question
    if "challenge_current_clue" not in st.session_state or st.session_state.challenge_current_clue is None:
        st.session_state.challenge_current_clue = random.choice(challenge_df.to_dict(orient="records"))
        st.session_state.start_time = datetime.datetime.now()
    
    clue = st.session_state.challenge_current_clue
    
# Regular game mode
else:
    # Get current clue
    if st.session_state.current_clue is None:
        st.session_state.current_clue = random.choice(filtered_df.to_dict(orient="records"))
        st.session_state.start_time = datetime.datetime.now()
    
    clue = st.session_state.current_clue

# Check for Daily Double
is_daily_double = False
if not st.session_state.daily_double_used and random.random() < 0.05:
    is_daily_double = True
    st.session_state.daily_double_used = True

# Display Daily Double if applicable
if is_daily_double:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); 
                color: #1a1a1a; padding: 1.5rem; border-radius: 15px; 
                text-align: center; margin-bottom: 1rem; 
                box-shadow: 0 6px 12px rgba(255, 215, 0, 0.3);">
        <h2 style="margin: 0; font-size: 1.8rem;">⭐ DAILY DOUBLE! ⭐</h2>
        <p style="margin-top: 0.3rem;">Double points for this question!</p>
    </div>
    """, unsafe_allow_html=True)

# Display category
st.markdown(f"""
<div class="theme-card">
    {clue['category']}
</div>
""", unsafe_allow_html=True)

# Display clue
st.markdown(f"""
<div class="clue-card">
    <div class="clue-text">{clue['clue']}</div>
</div>
""", unsafe_allow_html=True)

# Study Mode - show answer immediately
if st.session_state.study_mode:
    with st.expander("📖 View Answer", expanded=False):
        st.success(f"**Answer:** {clue['correct_response']}")
        
        # Note-taking for study mode
        note_key = f"{clue['category']}_{clue['clue'][:50]}"
        existing_note = st.session_state.notes.get(note_key, "")
        new_note = st.text_area(
            "📝 Add a note:",
            value=existing_note,
            placeholder="Add memory tricks, related facts, etc.",
            key=f"note_{note_key}"
        )
        if new_note != existing_note:
            st.session_state.notes[note_key] = new_note

# AI Mode - Handle buzzer and AI responses
if st.session_state.ai_mode and not st.session_state.buzzer_winner and not st.session_state.study_mode:
    # Buzzer phase - AI might buzz automatically
    st.markdown("### 🔔 Ready to buzz in!")
    
    # Check if AI buzzes first (happens automatically based on difficulty)
    import time
    ai_buzz_delay = AI_DIFFICULTY[st.session_state.ai_difficulty]["buzzer_speed"]
    
    # Create a container for dynamic updates
    buzz_container = st.container()
    
    with buzz_container:
        col_buzz1, col_buzz2 = st.columns(2)
        
        # Add a placeholder for AI buzzing notification
        ai_buzz_placeholder = st.empty()
        
        with col_buzz1:
            if st.button("🎯 BUZZ IN!", use_container_width=True, key="buzzer", type="primary"):
                # Player buzzed - determine who was faster
                winner, reaction_time = simulate_buzzer_race(st.session_state.ai_difficulty)
                st.session_state.buzzer_winner = winner
                st.session_state.current_turn = winner
                
                if winner == "player":
                    st.balloons()
                    st.success("🎯 You buzzed in first!")
                else:
                    st.warning(f"🤖 {st.session_state.ai_personality} was faster!")
                st.rerun()
        
        with col_buzz2:
            # Simulate AI potentially buzzing on its own
            # Easy: 30% chance, Medium: 50% chance, Hard: 70% chance
            buzz_chances = {"Easy": 0.3, "Medium": 0.5, "Hard": 0.7}
            if random.random() < buzz_chances[st.session_state.ai_difficulty]:
                # AI decides to buzz
                with st.spinner(f"🤖 {st.session_state.ai_personality} is buzzing in..."):
                    time.sleep(ai_buzz_delay)
                st.session_state.buzzer_winner = "ai"
                st.session_state.current_turn = "ai"
                st.warning(f"🤖 {st.session_state.ai_personality} buzzed in!")
                st.rerun()
            else:
                st.info(f"⏱️ Be quick! {st.session_state.ai_personality} is thinking...")
    
    # Don't show answer form during buzzer phase
    st.stop()

elif st.session_state.ai_mode and st.session_state.buzzer_winner == "ai" and not st.session_state.study_mode:
    # AI is answering
    st.info(f"🤖 {st.session_state.ai_personality} buzzed in first!")
    
    # Simulate AI response
    with st.spinner(f"{st.session_state.ai_personality} is thinking..."):
        is_correct, thinking_time = simulate_ai_response(
            clue["clue"],
            clue["category"],
            st.session_state.ai_difficulty,
            st.session_state.ai_personality
        )
        
        # Add artificial delay for realism
        import time
        time.sleep(min(thinking_time, 2))
    
    if is_correct:
        st.error(f"🤖 {st.session_state.ai_personality} got it right! The answer was: **{clue['correct_response']}**")
        
        # Award points to AI
        points = 2 if is_daily_double else 1
        st.session_state.ai_score += points
        st.session_state.ai_streak += 1
        
        # Reset for next question
        if st.button("Next Question ➡️", use_container_width=True, type="primary"):
            st.session_state.current_clue = None
            st.session_state.buzzer_winner = None
            st.session_state.current_turn = None
            st.rerun()
        st.stop()  # Don't show answer form
    else:
        st.success(f"❌ {st.session_state.ai_personality} got it wrong!")
        st.info("Your chance to steal the point! Answer below:")
        # Let player try to steal - continue to answer form

# Show answer form if:
# 1. Not in AI mode, OR
# 2. Player buzzed in, OR  
# 3. AI got it wrong and player can steal, OR
# 4. In study mode
show_answer_form = (
    not st.session_state.ai_mode or
    st.session_state.buzzer_winner == "player" or
    st.session_state.study_mode or
    (st.session_state.buzzer_winner == "ai" and st.session_state.ai_mode)  # AI wrong, player can steal
)

if show_answer_form:
    with st.form(key="clue_form", clear_on_submit=True):
        col_input, col_submit, col_bookmark = st.columns([3, 1, 1])
        with col_input:
            user_input = st.text_input(
                "Your response:",
                placeholder="Type your answer here...",
                label_visibility="collapsed",
                disabled=st.session_state.study_mode
            )
        with col_submit:
            submit_text = "🎯 Submit"
            if st.session_state.study_mode:
                submit_text = "⏭️ Next"
            elif st.session_state.ai_mode and st.session_state.buzzer_winner == "player":
                submit_text = "🎯 Answer!"
            submitted = st.form_submit_button(
                submit_text, 
                use_container_width=True
            )
        with col_bookmark:
            bookmark_btn = st.form_submit_button("🔖", use_container_width=True, help="Bookmark")

if bookmark_btn:
    bookmark_entry = {
        "category": clue["category"],
        "clue": clue["clue"],
        "correct_response": clue["correct_response"],
        "bookmarked_at": datetime.datetime.now().isoformat()
    }
    if bookmark_entry not in st.session_state.bookmarks:
        st.session_state.bookmarks.append(bookmark_entry)
        st.success("🔖 Bookmarked!")

if submitted:
    if st.session_state.study_mode:
        # In study mode, just move to next question
        if "challenge_mode" in st.session_state and st.session_state.challenge_mode:
            st.session_state.challenge_current_clue = None
            st.session_state.challenge_question_num += 1
        else:
            st.session_state.current_clue = None
        st.rerun()
    else:
        elapsed_time = (datetime.datetime.now() - st.session_state.start_time).seconds
        user_clean = normalize(user_input)
        answer_clean = normalize(clue["correct_response"])
        
        # Calculate points
        points_multiplier = 1
        if st.session_state.speed_round and elapsed_time <= 5:
            points_multiplier = 2
        elif is_daily_double:
            points_multiplier = 2
            
        # Check correctness using fuzzy matching
        answer_matches = fuzzy_match(user_input, clue["correct_response"], threshold=65)
        
        # Only enforce timer if it's enabled (not 999999)
        if st.session_state.time_limit == 999999:  # Timer is off
            correct = answer_matches
        else:  # Timer is on
            correct = answer_matches and elapsed_time <= st.session_state.time_limit

        if correct:
            st.balloons()
            points_earned = 1 * points_multiplier
            st.success(f"🎉 **Correct!** +{points_earned} points")
            st.session_state.score += points_earned
            st.session_state.streak += 1
            st.session_state.best_streak = max(st.session_state.streak, st.session_state.best_streak)
            
            # Check for achievements
            if st.session_state.streak == 5 and "5_streak" not in st.session_state.achievements:
                st.session_state.achievements.append("5_streak")
                st.success("🏆 Achievement: 5 Question Streak!")
            elif st.session_state.streak == 10 and "10_streak" not in st.session_state.achievements:
                st.session_state.achievements.append("10_streak")
                st.success("🏆 Achievement: 10 Question Streak!")
        else:
            # Only show time expired if timer was actually enabled and time ran out
            time_msg = ""
            if st.session_state.time_limit != 999999 and elapsed_time > st.session_state.time_limit:
                time_msg = "(Time expired!)"
            st.error(f"❌ **Incorrect** {time_msg}")
            st.info(f"The correct response was: **{clue['correct_response']}**")
            st.session_state.streak = 0
            points_earned = 0
            
            # Track weak themes
            theme = analyzer.categorize_single(clue["category"])
            if theme not in st.session_state.weak_themes:
                st.session_state.weak_themes[theme] = {"incorrect": 0, "total": 0}
            st.session_state.weak_themes[theme]["incorrect"] += 1

        # Update weak theme totals regardless of correct/incorrect
        theme = analyzer.categorize_single(clue["category"])
        if theme not in st.session_state.weak_themes:
            st.session_state.weak_themes[theme] = {"incorrect": 0, "total": 0}
        st.session_state.weak_themes[theme]["total"] += 1
        
        st.session_state.total += 1
        st.session_state.history.append({
            "category": clue["category"],
            "clue": clue["clue"],
            "correct_response": clue["correct_response"],
            "user_response": user_input,
            "was_correct": correct,
            "time_taken": elapsed_time,
            "points_earned": points_earned
        })

        # Handle challenge mode progression
        if "challenge_mode" in st.session_state and st.session_state.challenge_mode:
            # Update challenge score
            if correct:
                st.session_state.challenge_score += 1
            
            # Move to next question
            st.session_state.challenge_current_clue = None
            st.session_state.challenge_question_num += 1
            
            # Show next button
            if st.button("Next Challenge Question →", type="primary", use_container_width=True):
                st.rerun()
        else:
            st.session_state.current_clue = None
            
            # Reset AI mode states
            if st.session_state.ai_mode:
                st.session_state.buzzer_winner = None
                st.session_state.current_turn = None
            
            # Add a next button for better flow
            if st.button("Next Question →", type="primary", use_container_width=True):
                st.rerun()

# Expandable sections at the bottom
col_exp1, col_exp2, col_exp3 = st.columns(3)

with col_exp1:
    # Session history
    if st.session_state.history:
        with st.expander("📊 Session History", expanded=False):
            history_df = pd.DataFrame(st.session_state.history)
            
            # Summary metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Questions", len(history_df))
                avg_time = history_df["time_taken"].mean()
                st.metric("Avg Time", f"{avg_time:.1f}s")
            with col2:
                st.metric("Correct", len(history_df[history_df["was_correct"]]))
                acc = (len(history_df[history_df["was_correct"]]) / len(history_df)) * 100
                st.metric("Accuracy", f"{acc:.1f}%")
            
            # Show last 5 questions
            st.markdown("#### Recent Questions")
            recent = history_df.tail(5)[["category", "clue", "correct_response", "was_correct"]]
            st.dataframe(recent, use_container_width=True, height=200)

with col_exp2:
    # Bookmarks viewer
    if st.session_state.bookmarks:
        with st.expander(f"🔖 Bookmarks ({len(st.session_state.bookmarks)})", expanded=False):
            st.markdown("#### Your Bookmarked Questions")
            
            for i, bookmark in enumerate(st.session_state.bookmarks[-5:], 1):  # Show last 5
                st.markdown(f"**{i}. {bookmark['category']}**")
                st.markdown(f"Q: {bookmark['clue']}")
                st.markdown(f"A: *{bookmark['correct_response']}*")
                
                # Option to practice this question
                if st.button(f"Practice #{i}", key=f"practice_bookmark_{i}"):
                    st.session_state.current_clue = {
                        "category": bookmark["category"],
                        "clue": bookmark["clue"],
                        "correct_response": bookmark["correct_response"]
                    }
                    st.rerun()
                st.markdown("---")
            
            if len(st.session_state.bookmarks) > 5:
                st.info(f"Showing 5 of {len(st.session_state.bookmarks)} bookmarks")
    else:
        with st.expander("🔖 Bookmarks (0)", expanded=False):
            st.info("No bookmarks yet! Click the 🔖 button during gameplay to bookmark questions.")

with col_exp3:
    # Weak themes analysis
    if st.session_state.weak_themes:
        with st.expander("📈 Theme Performance", expanded=False):
            st.markdown("#### Your Performance by Theme")
            
            # Calculate accuracy per theme
            theme_data = []
            for theme, stats in st.session_state.weak_themes.items():
                if stats["total"] > 0:
                    accuracy = ((stats["total"] - stats["incorrect"]) / stats["total"]) * 100
                    theme_data.append({
                        "Theme": theme,
                        "Accuracy": f"{accuracy:.0f}%",
                        "Questions": stats["total"],
                        "Missed": stats["incorrect"]
                    })
            
            if theme_data:
                # Sort by accuracy (lowest first - these are weak areas)
                theme_data.sort(key=lambda x: float(x["Accuracy"].rstrip("%")))
                
                # Show weak themes
                weak_themes = [t for t in theme_data if float(t["Accuracy"].rstrip("%")) < 50]
                if weak_themes:
                    st.warning(f"🎯 Focus areas: {', '.join([t['Theme'] for t in weak_themes[:3]])}")
                
                # Display as dataframe
                theme_df = pd.DataFrame(theme_data)
                st.dataframe(theme_df, use_container_width=True, height=200)
    else:
        with st.expander("📈 Theme Performance", expanded=False):
            st.info("Play some questions to see your performance by theme!")