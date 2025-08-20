import pandas as pd
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import streamlit as st

class JeopardyCategoryAnalyzer:
    """Analyze and categorize Jeopardy categories into themes"""
    
    def __init__(self):
        # Define theme keywords and patterns
        self.theme_patterns = {
            "HISTORY": {
                "keywords": ["history", "historical", "ancient", "medieval", "war", "battle", 
                            "empire", "dynasty", "revolution", "civil war", "world war", 
                            "century", "era", "period", "ages", "civilization", "historic",
                            "past", "founding", "colonial", "conquest"],
                "patterns": [r"\b\d{4}\b", r"\b\d{1,2}th century\b", r"\bwar\b", r"the \d{2,4}s"]
            },
            
            "GEOGRAPHY": {
                "keywords": ["geography", "countries", "cities", "states", "capitals", 
                            "nations", "world", "islands", "mountains", "rivers", "lakes",
                            "oceans", "continents", "maps", "places", "landmarks", "wonders",
                            "national parks", "territories", "regions", "hemispheres"],
                "patterns": [r"countries", r"u\.s\. states", r"capitals", r"cities of"]
            },
            
            "SCIENCE": {
                "keywords": ["science", "biology", "chemistry", "physics", "anatomy", 
                            "medicine", "astronomy", "geology", "meteorology", "elements",
                            "atoms", "molecules", "space", "planets", "stars", "medical",
                            "body", "human", "animals", "nature", "environment", "ecology",
                            "evolution", "genetics", "dna", "cells", "periodic table"],
                "patterns": [r"scientific", r"the body", r"in space"]
            },
            
            "LITERATURE": {
                "keywords": ["literature", "books", "novels", "authors", "writers", "poets",
                            "poetry", "poems", "shakespeare", "classics", "fiction", 
                            "characters", "novels", "stories", "tales", "fables", "plays",
                            "playwright", "literary", "reading", "bibliography"],
                "patterns": [r"shakespeare", r"authors?", r"literat", r"book"]
            },
            
            "ENTERTAINMENT": {
                "keywords": ["movies", "films", "cinema", "hollywood", "actors", "actresses",
                            "oscars", "academy awards", "directors", "television", "tv",
                            "shows", "series", "sitcom", "drama", "comedy", "entertainment",
                            "celebrities", "stars", "emmys", "tonys", "grammys", "awards"],
                "patterns": [r"at the movies", r"on tv", r"oscar", r"film"]
            },
            
            "MUSIC": {
                "keywords": ["music", "songs", "singers", "bands", "albums", "composers",
                            "symphony", "opera", "jazz", "rock", "pop", "classical",
                            "instruments", "musicians", "concerts", "musical", "melody",
                            "rhythm", "blues", "country", "rap", "hip-hop", "folk"],
                "patterns": [r"music", r"song", r"sing", r"band"]
            },
            
            "SPORTS": {
                "keywords": ["sports", "football", "baseball", "basketball", "hockey",
                            "soccer", "tennis", "golf", "olympics", "athletes", "teams",
                            "championship", "tournament", "league", "nfl", "nba", "mlb",
                            "nhl", "fifa", "espn", "stadium", "arena", "game", "match"],
                "patterns": [r"sports", r"olympi", r"super bowl", r"world cup"]
            },
            
            "POLITICS": {
                "keywords": ["politics", "presidents", "government", "congress", "senate",
                            "political", "election", "campaign", "democrat", "republican",
                            "ministers", "parliament", "constitution", "amendments", "laws",
                            "supreme court", "white house", "capitol", "voting", "cabinet"],
                "patterns": [r"president", r"politic", r"government", r"u\.s\. president"]
            },
            
            "FOOD & DRINK": {
                "keywords": ["food", "cuisine", "cooking", "chef", "recipe", "restaurant",
                            "drinks", "beverages", "wine", "beer", "cocktails", "dining",
                            "meals", "dishes", "ingredients", "flavors", "taste", "kitchen",
                            "culinary", "gastronomy", "eat", "edible"],
                "patterns": [r"food", r"cook", r"eat", r"drink", r"cuisine"]
            },
            
            "TECHNOLOGY": {
                "keywords": ["technology", "computers", "internet", "software", "hardware",
                            "digital", "tech", "innovation", "inventions", "gadgets",
                            "electronics", "silicon valley", "apps", "websites", "coding",
                            "programming", "artificial intelligence", "robots", "cyber"],
                "patterns": [r"tech", r"computer", r"internet", r"digital"]
            },
            
            "BUSINESS": {
                "keywords": ["business", "companies", "corporations", "brands", "ceo",
                            "economy", "finance", "money", "banking", "stocks", "markets",
                            "industry", "commerce", "trade", "entrepreneurs", "startups",
                            "fortune 500", "wall street", "nasdaq", "investments"],
                "patterns": [r"business", r"compan", r"corporate", r"\$\d+"]
            },
            
            "LANGUAGE": {
                "keywords": ["language", "words", "vocabulary", "grammar", "etymology",
                            "dictionary", "spelling", "phrases", "idioms", "slang",
                            "linguistics", "latin", "greek", "french", "spanish", "german",
                            "translation", "alphabet", "letters", "pronunciation"],
                "patterns": [r"word", r"language", r"vocabulary", r"latin", r"greek"]
            },
            
            "MYTHOLOGY": {
                "keywords": ["mythology", "myths", "legends", "gods", "goddesses", "zeus",
                            "greek mythology", "roman mythology", "norse mythology",
                            "ancient gods", "olympus", "titans", "folklore", "fables"],
                "patterns": [r"mytholog", r"gods", r"goddesses", r"ancient.*god"]
            },
            
            "ART": {
                "keywords": ["art", "artists", "paintings", "sculpture", "museums", "gallery",
                            "renaissance", "impressionism", "modern art", "masterpiece",
                            "painters", "sculptors", "artwork", "canvas", "portrait"],
                "patterns": [r"art", r"paint", r"sculptor", r"museum"]
            },
            
            "RELIGION": {
                "keywords": ["religion", "religious", "bible", "church", "faith", "christianity",
                            "islam", "judaism", "buddhism", "hinduism", "theology",
                            "saints", "prophets", "scripture", "holy", "sacred", "worship"],
                "patterns": [r"religio", r"bible", r"church", r"saint"]
            },
            
            "FASHION": {
                "keywords": ["fashion", "clothing", "clothes", "designer", "style", "wear",
                            "dress", "outfit", "accessories", "jewelry", "shoes", "fabric",
                            "textile", "couture", "runway", "model", "trends"],
                "patterns": [r"fashion", r"wear", r"cloth", r"dress"]
            },
            
            "WORDPLAY": {
                "keywords": ["rhyme", "rhyming", "puns", "anagrams", "palindromes", 
                            "alliteration", "wordplay", "letter", "spell", "scramble",
                            "crossword", "puzzle", "riddle"],
                "patterns": [r"rhym", r"pun", r"anagram", r"word.*play"]
            },
            
            "POP CULTURE": {
                "keywords": ["pop culture", "trends", "viral", "memes", "social media",
                            "celebrities", "gossip", "tabloid", "famous", "fame", "icons",
                            "personality", "influencer", "trending"],
                "patterns": [r"pop culture", r"celebrit", r"famous"]
            },
            
            "HOLIDAYS": {
                "keywords": ["holiday", "christmas", "thanksgiving", "easter", "halloween",
                            "new year", "valentine", "independence day", "celebrations",
                            "festivals", "traditions", "seasonal"],
                "patterns": [r"holiday", r"christmas", r"thanksgiving", r"halloween"]
            },
            
            "BEFORE & AFTER": {
                "keywords": ["before", "after", "before & after", "before and after"],
                "patterns": [r"before.*after", r"before & after"]
            }
        }
    
    def categorize_single(self, category: str) -> List[str]:
        """Categorize a single category string into themes"""
        if not category:
            return ["MISCELLANEOUS"]
            
        category_lower = str(category).lower()
        matched_themes = []
        
        # More aggressive matching - check for word boundaries
        for theme, criteria in self.theme_patterns.items():
            # Check keywords with word boundary matching
            for keyword in criteria["keywords"]:
                # Check for whole word match or as part of compound
                if keyword in category_lower.split() or keyword in category_lower:
                    matched_themes.append(theme)
                    break
            
            # Check patterns
            if theme not in matched_themes:
                for pattern in criteria["patterns"]:
                    if re.search(pattern, category_lower):
                        matched_themes.append(theme)
                        break
        
        # If no themes matched, try to be smarter about it
        if not matched_themes:
            # Check for common Jeopardy category patterns
            if any(word in category_lower for word in ['century', 'year', 'war', 'empire', 'king', 'queen', 'president']):
                matched_themes.append("HISTORY")
            elif any(word in category_lower for word in ['movie', 'film', 'tv', 'show', 'actor', 'star']):
                matched_themes.append("ENTERTAINMENT")
            elif any(word in category_lower for word in ['book', 'author', 'novel', 'poet', 'writer', 'literature']):
                matched_themes.append("LITERATURE")
            elif any(word in category_lower for word in ['song', 'music', 'band', 'singer', 'album']):
                matched_themes.append("MUSIC")
            elif any(word in category_lower for word in ['sport', 'game', 'team', 'player', 'league', 'ball']):
                matched_themes.append("SPORTS")
            elif any(word in category_lower for word in ['science', 'element', 'body', 'medical', 'doctor']):
                matched_themes.append("SCIENCE")
            elif any(word in category_lower for word in ['word', 'letter', 'spell', 'rhyme', 'alphabet']):
                matched_themes.append("WORDPLAY")
            elif any(word in category_lower for word in ['geography', 'country', 'city', 'state', 'capital', 'world']):
                matched_themes.append("GEOGRAPHY")
            elif any(word in category_lower for word in ['food', 'eat', 'drink', 'cook', 'chef', 'recipe']):
                matched_themes.append("FOOD & DRINK")
            else:
                matched_themes.append("MISCELLANEOUS")
        
        return matched_themes
    
    def analyze_categories(self, categories: List[str]) -> Dict[str, List[str]]:
        """Analyze all categories and group them by theme"""
        theme_groups = defaultdict(list)
        category_themes = {}
        
        for category in categories:
            themes = self.categorize_single(category)
            category_themes[category] = themes
            for theme in themes:
                theme_groups[theme].append(category)
        
        # Sort themes by number of categories
        sorted_themes = dict(sorted(theme_groups.items(), 
                                  key=lambda x: len(x[1]), 
                                  reverse=True))
        
        return sorted_themes
    
    def get_theme_statistics(self, categories: List[str]) -> pd.DataFrame:
        """Get statistics about theme distribution"""
        theme_groups = self.analyze_categories(categories)
        
        stats = []
        for theme, cats in theme_groups.items():
            stats.append({
                'Theme': theme,
                'Count': len(cats),
                'Percentage': (len(cats) / len(categories)) * 100,
                'Example Categories': ', '.join(cats[:3])
            })
        
        return pd.DataFrame(stats)
    
    def suggest_filter_groups(self, categories: List[str], max_groups: int = 15) -> Dict[str, List[str]]:
        """Suggest optimal filter groups for UI"""
        theme_groups = self.analyze_categories(categories)
        
        # Create optimized groups
        filter_groups = {}
        
        # Sort themes by count (excluding MISCELLANEOUS for now)
        sorted_themes = sorted(
            [(k, v) for k, v in theme_groups.items() if k != "MISCELLANEOUS"],
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        # Keep top themes with significant categories (lower threshold for real data)
        for theme, cats in sorted_themes[:max_groups]:
            if len(cats) >= 10:  # Lower threshold to 10 categories
                filter_groups[theme] = cats
        
        # If we don't have enough themes, add some with fewer categories
        if len(filter_groups) < 5:
            for theme, cats in sorted_themes:
                if theme not in filter_groups and len(cats) >= 5:
                    filter_groups[theme] = cats
                if len(filter_groups) >= 8:
                    break
        
        # Add "ALL CATEGORIES" option at the end
        filter_groups["ALL CATEGORIES"] = categories
        
        # Add MISCELLANEOUS only if it's not too large (less than 60% of total)
        if "MISCELLANEOUS" in theme_groups:
            misc_cats = theme_groups["MISCELLANEOUS"]
            if len(misc_cats) > 0 and len(misc_cats) < len(categories) * 0.6:
                filter_groups["OTHER/MISC"] = misc_cats
        
        return filter_groups


# Enhanced UI Component for Streamlit App
def create_themed_category_selector(df: pd.DataFrame, sidebar=True):
    """Create a themed category selector for Streamlit UI"""
    
    analyzer = JeopardyCategoryAnalyzer()
    categories = sorted(df["category"].unique())
    
    # Analyze categories
    theme_groups = analyzer.suggest_filter_groups(categories)
    
    # Create UI selector
    container = st.sidebar if sidebar else st
    
    with container:
        st.markdown("### 🎯 Category Selection")
        
        # Theme-based selection
        selection_mode = st.radio(
            "Selection Mode:",
            ["By Theme", "By Individual Categories", "Quick Picks"],
            horizontal=True
        )
        
        selected_categories = []
        
        if selection_mode == "By Theme":
            selected_themes = st.multiselect(
                "Select Themes:",
                options=[theme for theme in theme_groups.keys() if theme != "ALL CATEGORIES"],
                default=["HISTORY", "SCIENCE", "ENTERTAINMENT"][:3] if len(theme_groups) > 3 else list(theme_groups.keys())[:1]
            )
            
            # Combine all categories from selected themes
            for theme in selected_themes:
                if theme in theme_groups:
                    selected_categories.extend(theme_groups[theme])
            
            # Remove duplicates
            selected_categories = list(set(selected_categories))
            
            # Show selected category count
            if selected_categories:
                st.info(f"📊 {len(selected_categories)} categories selected from {len(selected_themes)} themes")
                
                # Option to view categories
                with st.expander("View Selected Categories"):
                    for theme in selected_themes:
                        if theme in theme_groups:
                            st.write(f"**{theme}:**")
                            st.write(", ".join(theme_groups[theme][:10]))
                            if len(theme_groups[theme]) > 10:
                                st.write(f"... and {len(theme_groups[theme]) - 10} more")
        
        elif selection_mode == "By Individual Categories":
            selected_categories = st.multiselect(
                "Select Categories:",
                options=categories,
                default=categories[:5] if len(categories) >= 5 else categories
            )
        
        else:  # Quick Picks
            quick_pick = st.selectbox(
                "Choose a preset:",
                [
                    "🎓 Academic Mix (History, Science, Literature)",
                    "🎬 Entertainment Pack (Movies, TV, Music)",
                    "🌍 World Knowledge (Geography, Politics, Language)",
                    "⚡ Pop Culture & Sports",
                    "🧠 Brain Teasers (Wordplay, Before & After)",
                    "🎨 Arts & Culture (Art, Literature, Music)",
                    "💼 Modern Life (Business, Technology, Politics)",
                    "🎲 Random Mix (25 random categories)",
                    "📚 Everything (All categories)"
                ]
            )
            
            # Map quick picks to categories
            if "Academic" in quick_pick:
                themes_to_use = ["HISTORY", "SCIENCE", "LITERATURE"]
            elif "Entertainment Pack" in quick_pick:
                themes_to_use = ["ENTERTAINMENT", "MUSIC"]
            elif "World Knowledge" in quick_pick:
                themes_to_use = ["GEOGRAPHY", "POLITICS", "LANGUAGE"]
            elif "Pop Culture" in quick_pick:
                themes_to_use = ["POP CULTURE", "SPORTS"]
            elif "Brain Teasers" in quick_pick:
                themes_to_use = ["WORDPLAY", "BEFORE & AFTER"]
            elif "Arts & Culture" in quick_pick:
                themes_to_use = ["ART", "LITERATURE", "MUSIC"]
            elif "Modern Life" in quick_pick:
                themes_to_use = ["BUSINESS", "TECHNOLOGY", "POLITICS"]
            elif "Random Mix" in quick_pick:
                import random
                selected_categories = random.sample(categories, min(25, len(categories)))
                themes_to_use = []
            elif "Everything" in quick_pick:
                selected_categories = categories
                themes_to_use = []
            else:
                themes_to_use = []
            
            if themes_to_use:
                for theme in themes_to_use:
                    if theme in theme_groups:
                        selected_categories.extend(theme_groups[theme])
                selected_categories = list(set(selected_categories))
            
            st.info(f"Selected: {len(selected_categories)} categories")
    
    return selected_categories