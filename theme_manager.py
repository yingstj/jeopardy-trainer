"""
Theme Manager for Jeopardy Categories
Groups 57,000+ individual categories into manageable themes
"""
import pandas as pd
import re
from typing import Dict, List, Set
from collections import defaultdict

class ThemeManager:
    """Manages grouping of Jeopardy categories into themes"""
    
    def __init__(self):
        # Define theme rules with keywords and patterns
        self.theme_rules = {
            "HISTORY & POLITICS": {
                "keywords": ["history", "historical", "president", "war", "battle", "empire", 
                           "dynasty", "revolution", "century", "ancient", "medieval", "civil war",
                           "world war", "politics", "political", "government", "congress", "senate",
                           "election", "vote", "constitution", "democracy", "king", "queen", "royal"],
                "patterns": [r"\b\d{4}\b", r"\bwar\b", r"president", r"politic"]
            },
            
            "SCIENCE & NATURE": {
                "keywords": ["science", "biology", "chemistry", "physics", "anatomy", "medicine",
                           "element", "atom", "molecule", "space", "planet", "star", "astronomy",
                           "geology", "weather", "climate", "ocean", "animal", "plant", "nature",
                           "environment", "ecology", "species", "evolution", "cell", "dna"],
                "patterns": [r"scientific", r"biolog", r"chemi", r"physic"]
            },
            
            "LITERATURE & LANGUAGE": {
                "keywords": ["literature", "book", "novel", "author", "writer", "poet", "poetry",
                           "shakespeare", "play", "story", "tale", "fiction", "character", "language",
                           "word", "vocabulary", "grammar", "letter", "alphabet", "spelling", "phrase",
                           "idiom", "english", "french", "spanish", "latin", "greek"],
                "patterns": [r"literat", r"author", r"book", r"word", r"language"]
            },
            
            "ENTERTAINMENT & ARTS": {
                "keywords": ["movie", "film", "cinema", "hollywood", "actor", "actress", "oscar",
                           "tv", "television", "show", "series", "music", "song", "singer", "band",
                           "album", "composer", "opera", "art", "artist", "painting", "sculpture",
                           "museum", "theater", "theatre", "dance", "ballet", "performance"],
                "patterns": [r"movie", r"film", r"tv", r"music", r"art"]
            },
            
            "SPORTS & GAMES": {
                "keywords": ["sport", "football", "baseball", "basketball", "hockey", "soccer",
                           "tennis", "golf", "olympic", "athlete", "team", "game", "player",
                           "championship", "tournament", "league", "coach", "stadium", "score",
                           "chess", "card", "puzzle", "competition"],
                "patterns": [r"sport", r"game", r"olymp", r"champion"]
            },
            
            "GEOGRAPHY & PLACES": {
                "keywords": ["geography", "country", "countries", "city", "cities", "state",
                           "capital", "nation", "continent", "island", "mountain", "river",
                           "lake", "ocean", "map", "world", "travel", "location", "landmark",
                           "border", "region", "hemisphere", "latitude", "longitude"],
                "patterns": [r"geograph", r"countr", r"city", r"capital", r"world"]
            },
            
            "FOOD & DRINK": {
                "keywords": ["food", "eat", "cuisine", "cooking", "chef", "recipe", "restaurant",
                           "meal", "dish", "ingredient", "flavor", "taste", "drink", "beverage",
                           "wine", "beer", "cocktail", "coffee", "tea", "fruit", "vegetable"],
                "patterns": [r"food", r"cook", r"eat", r"drink", r"cuisine"]
            },
            
            "BUSINESS & TECHNOLOGY": {
                "keywords": ["business", "company", "corporation", "brand", "ceo", "economy",
                           "money", "dollar", "bank", "finance", "stock", "market", "trade",
                           "technology", "computer", "internet", "software", "digital", "tech",
                           "innovation", "invention", "gadget", "app", "website"],
                "patterns": [r"business", r"compan", r"tech", r"computer", r"money"]
            },
            
            "RELIGION & MYTHOLOGY": {
                "keywords": ["religion", "religious", "god", "goddess", "bible", "church",
                           "faith", "mythology", "myth", "legend", "zeus", "greek god",
                           "roman god", "norse", "saint", "prophet", "temple", "sacred",
                           "holy", "worship", "prayer", "spiritual"],
                "patterns": [r"relig", r"god", r"myth", r"bible", r"saint"]
            },
            
            "WORDPLAY & PUZZLES": {
                "keywords": ["rhyme", "rhyming", "pun", "anagram", "palindrome", "crossword",
                           "puzzle", "riddle", "wordplay", "scramble", "spell", "letter",
                           "before & after", "before and after"],
                "patterns": [r"rhym", r"pun", r"anagram", r"wordplay", r"before.*after"]
            },
            
            "POP CULTURE & MODERN LIFE": {
                "keywords": ["pop culture", "celebrity", "famous", "trend", "fashion", "style",
                           "social media", "internet", "meme", "viral", "modern", "contemporary",
                           "current", "today", "recent", "millennial", "gen z"],
                "patterns": [r"pop cultur", r"celebrit", r"fashion", r"modern"]
            },
            
            "HOLIDAYS & CELEBRATIONS": {
                "keywords": ["holiday", "christmas", "thanksgiving", "easter", "halloween",
                           "new year", "valentine", "celebration", "festival", "tradition",
                           "birthday", "anniversary", "wedding", "party"],
                "patterns": [r"holiday", r"christmas", r"thanksgiving", r"celebrat"]
            }
        }
    
    def categorize_to_theme(self, category: str) -> str:
        """Determine which theme a category belongs to"""
        if not category:
            return "GENERAL KNOWLEDGE"
        
        category_lower = str(category).lower()
        theme_scores = {}
        
        # Score each theme based on keyword matches
        for theme, rules in self.theme_rules.items():
            score = 0
            
            # Check keywords
            for keyword in rules["keywords"]:
                if keyword in category_lower:
                    score += len(keyword)  # Longer matches score higher
            
            # Check patterns
            for pattern in rules["patterns"]:
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
            theme = self.categorize_to_theme(category)
            theme_groups[theme].append(category)
        
        # Sort themes by number of categories (most popular first)
        sorted_themes = dict(sorted(theme_groups.items(), 
                                  key=lambda x: len(x[1]), 
                                  reverse=True))
        
        return sorted_themes
    
    def get_theme_stats(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Get statistics for each theme"""
        categories = df['category'].unique()
        theme_groups = self.group_categories_by_theme(categories)
        
        stats = {}
        for theme, cats in theme_groups.items():
            # Count total clues in this theme
            theme_clues = df[df['category'].isin(cats)]
            stats[theme] = {
                'category_count': len(cats),
                'clue_count': len(theme_clues),
                'percentage': (len(theme_clues) / len(df)) * 100,
                'sample_categories': cats[:5]  # First 5 categories as examples
            }
        
        return stats
    
    def get_balanced_themes(self, df: pd.DataFrame, min_clues: int = 100) -> List[str]:
        """Get list of themes that have enough clues for good gameplay"""
        theme_stats = self.get_theme_stats(df)
        
        # Filter themes with enough clues
        balanced_themes = [
            theme for theme, stats in theme_stats.items()
            if stats['clue_count'] >= min_clues
        ]
        
        return sorted(balanced_themes)