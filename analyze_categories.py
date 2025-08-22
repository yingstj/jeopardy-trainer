#!/usr/bin/env python3
"""
Analyze and group Jeopardy categories into themes
"""
import pandas as pd
import re
from collections import defaultdict, Counter

def analyze_categories(csv_path="data/all_jeopardy_clues.csv"):
    """Analyze categories and group them into themes"""
    
    print("Loading data...")
    df = pd.read_csv(csv_path)
    
    # Get unique categories
    categories = df['category'].unique()
    print(f"\nTotal unique categories: {len(categories):,}")
    
    # Theme mapping rules
    theme_rules = {
        'HISTORY': [
            r'HISTORY', r'HISTORIC', r'CENTURY', r'ANCIENT', r'WAR', r'BATTLE',
            r'PRESIDENT', r'CIVIL WAR', r'WORLD WAR', r'REVOLUTION', r'DYNASTY',
            r'EMPIRE', r'MEDIEVAL', r'COLONIAL', r'B\.C\.', r'A\.D\.',
            r'\d{4}s?(?:\s|$)', r'YEAR \d+', r'THE \d+s'
        ],
        'SCIENCE': [
            r'SCIENCE', r'BIOLOGY', r'CHEMISTRY', r'PHYSICS', r'ANATOMY',
            r'MEDICINE', r'ELEMENT', r'ANIMAL', r'PLANT', r'NATURE',
            r'ASTRONOMY', r'SPACE', r'PLANET', r'STAR', r'GEOLOGY',
            r'WEATHER', r'CLIMATE', r'OCEAN', r'MARINE', r'SPECIES'
        ],
        'GEOGRAPHY': [
            r'GEOGRAPHY', r'COUNTRY', r'COUNTRIES', r'CITY', r'CITIES',
            r'STATE', r'CAPITAL', r'ISLAND', r'MOUNTAIN', r'RIVER',
            r'LAKE', r'OCEAN', r'CONTINENT', r'MAP', r'BORDER',
            r'NATIONAL', r'WORLD', r'PLACE', r'LOCATION', r'LANDMARK'
        ],
        'LITERATURE': [
            r'LITERATURE', r'BOOK', r'AUTHOR', r'POET', r'POETRY',
            r'NOVEL', r'SHAKESPEARE', r'WRITER', r'PLAY', r'FICTION',
            r'STORY', r'TALES?', r'READING', r'LIBRARY', r'PUBLISH'
        ],
        'MOVIES & TV': [
            r'MOVIE', r'FILM', r'CINEMA', r'ACTOR', r'ACTRESS',
            r'HOLLYWOOD', r'OSCAR', r'ACADEMY AWARD', r'TV', r'TELEVISION',
            r'SHOW', r'SERIES', r'SITCOM', r'DRAMA', r'COMEDY',
            r'DIRECTOR', r'STAR', r'CAST', r'SCREEN'
        ],
        'MUSIC': [
            r'MUSIC', r'SONG', r'SINGER', r'BAND', r'COMPOSER',
            r'OPERA', r'SYMPHONY', r'JAZZ', r'ROCK', r'POP',
            r'CLASSICAL', r'ALBUM', r'CONCERT', r'INSTRUMENT', r'MELODY',
            r'RHYTHM', r'BEAT', r'TUNE', r'LYRIC'
        ],
        'SPORTS': [
            r'SPORT', r'FOOTBALL', r'BASEBALL', r'BASKETBALL', r'HOCKEY',
            r'SOCCER', r'TENNIS', r'GOLF', r'OLYMPIC', r'ATHLETE',
            r'TEAM', r'GAME', r'CHAMPION', r'LEAGUE', r'TOURNAMENT',
            r'PLAYER', r'COACH', r'STADIUM', r'SCORE'
        ],
        'POLITICS & GOVERNMENT': [
            r'POLITIC', r'GOVERNMENT', r'PRESIDENT', r'SENATOR', r'CONGRESS',
            r'ELECTION', r'VOTE', r'DEMOCRAT', r'REPUBLICAN', r'CABINET',
            r'CONSTITUTION', r'LAW', r'COURT', r'JUDGE', r'SUPREME COURT',
            r'GOVERNOR', r'MAYOR', r'MINISTER', r'PARLIAMENT'
        ],
        'BUSINESS & ECONOMICS': [
            r'BUSINESS', r'COMPANY', r'CORPORATION', r'STOCK', r'MARKET',
            r'ECONOMY', r'MONEY', r'DOLLAR', r'BANK', r'FINANCE',
            r'TRADE', r'INDUSTRY', r'PRODUCT', r'BRAND', r'CEO',
            r'ENTREPRENEUR', r'STARTUP', r'INVEST'
        ],
        'FOOD & DRINK': [
            r'FOOD', r'DRINK', r'CUISINE', r'COOK', r'CHEF',
            r'RESTAURANT', r'MEAL', r'DISH', r'RECIPE', r'INGREDIENT',
            r'WINE', r'BEER', r'COCKTAIL', r'COFFEE', r'TEA',
            r'FRUIT', r'VEGETABLE', r'MEAT', r'DESSERT'
        ],
        'ART & CULTURE': [
            r'ART', r'ARTIST', r'PAINT', r'SCULPTURE', r'MUSEUM',
            r'GALLERY', r'CULTURE', r'TRADITION', r'CUSTOM', r'FESTIVAL',
            r'DANCE', r'BALLET', r'THEATER', r'THEATRE', r'PERFORMANCE'
        ],
        'TECHNOLOGY': [
            r'TECHNOLOGY', r'COMPUTER', r'INTERNET', r'SOFTWARE', r'TECH',
            r'DIGITAL', r'ELECTRONIC', r'ROBOT', r'AI', r'APP',
            r'WEBSITE', r'SOCIAL MEDIA', r'PHONE', r'DEVICE'
        ],
        'LANGUAGE & WORDS': [
            r'WORD', r'LANGUAGE', r'ENGLISH', r'FRENCH', r'SPANISH',
            r'LATIN', r'GREEK', r'PHRASE', r'IDIOM', r'SLANG',
            r'VOCABULARY', r'DICTIONARY', r'GRAMMAR', r'LETTER', r'ALPHABET',
            r'RHYME', r'SYNONYM', r'ANTONYM', r'PREFIX', r'SUFFIX'
        ],
        'RELIGION & MYTHOLOGY': [
            r'RELIGION', r'GOD', r'GODDESS', r'BIBLE', r'CHURCH',
            r'MYTH', r'LEGEND', r'GREEK GOD', r'ROMAN GOD', r'SAINT',
            r'PROPHET', r'TEMPLE', r'MOSQUE', r'SYNAGOGUE', r'FAITH',
            r'CHRISTIAN', r'JEWISH', r'MUSLIM', r'BUDDHIS', r'HINDU'
        ],
        'POTPOURRI & GENERAL': [
            r'POTPOURRI', r'HODGEPODGE', r'MIXED BAG', r'GRAB BAG',
            r'MISCELLANE', r'GENERAL', r'TRIVIA', r'RANDOM'
        ]
    }
    
    # Categorize each category
    category_themes = {}
    unmatched_categories = []
    
    for category in categories:
        if not category:
            continue
            
        category_upper = str(category).upper()
        matched = False
        
        # Check each theme's patterns
        for theme, patterns in theme_rules.items():
            for pattern in patterns:
                if re.search(pattern, category_upper):
                    category_themes[category] = theme
                    matched = True
                    break
            if matched:
                break
        
        if not matched:
            # Try to find common words for uncategorized
            if any(word in category_upper for word in ['BEFORE', 'AFTER', 'RHYME', 'TIME']):
                category_themes[category] = 'WORDPLAY'
            elif any(word in category_upper for word in ['QUOTE', 'SAID', 'FAMOUS']):
                category_themes[category] = 'QUOTES & PHRASES'
            elif category_upper.startswith('THE '):
                category_themes[category] = 'POTPOURRI & GENERAL'
            else:
                category_themes[category] = 'POTPOURRI & GENERAL'
                unmatched_categories.append(category)
    
    # Count themes
    theme_counts = Counter(category_themes.values())
    
    print("\n=== THEME DISTRIBUTION ===")
    for theme, count in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(categories)) * 100
        print(f"{theme:25} {count:6,} categories ({percentage:5.1f}%)")
    
    print(f"\nTotal themes: {len(theme_counts)}")
    print(f"Reduction: {len(categories):,} categories → {len(theme_counts)} themes")
    print(f"Compression ratio: {len(categories) / len(theme_counts):.0f}:1")
    
    # Sample some unmatched categories
    if unmatched_categories:
        print(f"\n=== SAMPLE UNMATCHED CATEGORIES (first 20) ===")
        for cat in unmatched_categories[:20]:
            print(f"  - {cat}")
    
    # Save mapping to file
    mapping_df = pd.DataFrame(list(category_themes.items()), columns=['category', 'theme'])
    mapping_df.to_csv('data/category_themes.csv', index=False)
    print(f"\n✅ Saved category-theme mapping to data/category_themes.csv")
    
    # Analyze clues per theme
    print("\n=== CLUES PER THEME ===")
    df_with_themes = df.merge(mapping_df, on='category', how='left')
    theme_clue_counts = df_with_themes.groupby('theme').size().sort_values(ascending=False)
    
    for theme, count in theme_clue_counts.items():
        percentage = (count / len(df)) * 100
        print(f"{theme:25} {count:7,} clues ({percentage:5.1f}%)")
    
    return category_themes, theme_counts

if __name__ == "__main__":
    analyze_categories()