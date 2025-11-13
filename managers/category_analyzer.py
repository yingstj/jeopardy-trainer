import re
from collections import defaultdict
from typing import Dict, List, Pattern, Tuple

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

        self._keyword_patterns: Dict[str, List[Tuple[str, Pattern]]] = {}
        self._compiled_patterns: Dict[str, List[Pattern]] = {}
        self._prepare_patterns()
    
    def categorize_single(self, category: str) -> str:
        """Categorize a single category string into a theme"""
        if not category:
            return "GENERAL KNOWLEDGE"
        
        category_text = str(category)
        theme_scores = {}
        
        # Score each theme based on keyword matches
        for theme, criteria in self.theme_patterns.items():
            score = 0
            
            # Check keywords
            for keyword, pattern in self._keyword_patterns[theme]:
                if pattern.search(category_text):
                    score += len(keyword)  # Longer matches score higher
            
            # Check patterns
            for pattern in self._compiled_patterns[theme]:
                if pattern.search(category_text):
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

    def _prepare_patterns(self):
        """Deduplicate keywords/patterns and compile regexes for efficient matching"""
        for theme, data in self.theme_patterns.items():
            keywords = data.get("keywords", [])
            # Deduplicate while preserving order
            unique_keywords = list(dict.fromkeys(keywords))
            data["keywords"] = unique_keywords

            compiled_keywords: List[Tuple[str, Pattern]] = []
            for keyword in unique_keywords:
                compiled_keywords.append((keyword, self._compile_keyword(keyword)))
            self._keyword_patterns[theme] = compiled_keywords

            patterns = data.get("patterns", [])
            unique_patterns = list(dict.fromkeys(patterns))
            data["patterns"] = unique_patterns
            compiled_theme_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in unique_patterns]
            self._compiled_patterns[theme] = compiled_theme_patterns

    @staticmethod
    def _compile_keyword(keyword: str) -> Pattern:
        """Compile a regex for a keyword ensuring word-boundary matching when possible"""
        # Default to escaped keyword
        escaped = re.escape(keyword)

        # Determine if we can safely wrap with word boundaries
        if re.search(r"\w", keyword):
            # Allow common punctuation that can appear within category names
            if re.fullmatch(r"[A-Za-z0-9\s&'\-\.]+", keyword):
                pattern = rf"\b{escaped}\b"
            else:
                pattern = escaped
        else:
            pattern = escaped

        return re.compile(pattern, re.IGNORECASE)
