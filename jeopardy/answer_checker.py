"""
Enhanced Jeopardy Answer Checker with proper fuzzy matching
Fixes the critical bug where "car" matches "carburetor" or "ton" matches "Washington"
"""

import re
from difflib import SequenceMatcher
from typing import Tuple, List, Set
import unicodedata


class JeopardyAnswerChecker:
    """Smart answer checker that handles Jeopardy-specific patterns"""
    
    def __init__(self):
        # Common abbreviations and their full forms
        self.abbreviations = {
            'fdr': 'franklin delano roosevelt',
            'jfk': 'john f kennedy',
            'lbj': 'lyndon b johnson',
            'mlk': 'martin luther king',
            'wwi': 'world war i',
            'wwii': 'world war ii',
            'uk': 'united kingdom',
            'us': 'united states',
            'usa': 'united states of america',
            'ussr': 'soviet union',
            'eu': 'european union',
            'un': 'united nations',
            'nato': 'north atlantic treaty organization',
            'nasa': 'national aeronautics and space administration',
            'fbi': 'federal bureau of investigation',
            'cia': 'central intelligence agency',
            'nfl': 'national football league',
            'nba': 'national basketball association',
            'mlb': 'major league baseball',
            'nhl': 'national hockey league',
        }
        
        # Articles and words to ignore in certain contexts
        self.articles = {'the', 'a', 'an'}
        self.titles = {'mr', 'mrs', 'ms', 'miss', 'dr', 'prof', 'sir', 'dame', 'lord', 'lady'}
        
        # Minimum word length for substring matching
        self.MIN_SUBSTRING_LENGTH = 4
        
        # Minimum ratio of words for partial matches
        self.MIN_WORD_COVERAGE = 0.5

    def normalize_answer(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove Jeopardy question format
        text = re.sub(r'^(what|who|where|when|why|how)\s+(is|are|was|were|am)\s+', '', text)
        text = re.sub(r'^(what|who|where|when|why|how)\s+(\'s|s)\s+', '', text)
        
        # Remove punctuation but keep spaces and apostrophes for contractions
        text = re.sub(r'[^\w\s\']', ' ', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Remove accents
        text = ''.join(c for c in unicodedata.normalize('NFD', text) 
                      if unicodedata.category(c) != 'Mn')
        
        return text

    def extract_alternatives(self, answer: str) -> List[str]:
        """Extract all acceptable alternatives from answer"""
        # Handle parenthetical alternatives
        # Examples: "Zimbabwe (or Rhodesia)", "The Tempest (accept The Winter's Tale)"
        
        alternatives = []
        
        # Remove parenthetical parts to get main answer
        main_answer = re.sub(r'\([^)]*\)', '', answer).strip()
        alternatives.append(main_answer)
        
        # Extract alternatives from parentheses
        paren_matches = re.findall(r'\(([^)]+)\)', answer)
        for match in paren_matches:
            # Look for "or", "accept", "aka" patterns
            if any(word in match.lower() for word in ['or', 'accept', 'aka']):
                # Split on these keywords
                parts = re.split(r'\b(?:or|accept also|accept|aka)\b', match, flags=re.IGNORECASE)
                for part in parts:
                    clean_part = part.strip()
                    if clean_part and clean_part.lower() not in ['also', 'either']:
                        alternatives.append(clean_part)
        
        # Handle forward slashes as alternatives
        if '/' in answer and not re.search(r'\d+/\d+', answer):  # Not a fraction
            for alt in answer.split('/'):
                alternatives.append(alt.strip())
        
        return list(set(alternatives))  # Remove duplicates

    def is_valid_substring_match(self, user_norm: str, correct_norm: str) -> bool:
        """Check if substring match is valid (not just random letters)"""
        
        # Too short to be meaningful
        if len(user_norm) < self.MIN_SUBSTRING_LENGTH:
            return False
        
        # Check if it appears at word boundaries
        # This prevents "car" from matching "carburetor"
        pattern = r'\b' + re.escape(user_norm) + r'\b'
        if re.search(pattern, correct_norm):
            return True
        
        # Check if it's a complete word from the answer
        user_words = set(user_norm.split())
        correct_words = set(correct_norm.split())
        
        # If user answer is a single word, it must be a complete word in the answer
        if len(user_words) == 1:
            return user_words.issubset(correct_words)
        
        return False

    def check_last_name(self, user_norm: str, correct_norm: str) -> bool:
        """Check if user provided just the last name for a person"""
        user_words = user_norm.split()
        correct_words = correct_norm.split()
        
        # User provided single word, answer has multiple words
        if len(user_words) == 1 and len(correct_words) >= 2:
            # Check if it matches the last word (typically last name)
            if user_words[0] == correct_words[-1]:
                # Make sure it's likely a name (not "the great" etc)
                # Also exclude common words that shouldn't match alone
                excluded_words = {'great', 'terrible', 'conqueror', 'bold', 'wise', 
                                'king', 'queen', 'prince', 'princess', 'lord', 'lady',
                                'saint', 'pope', 'emperor', 'dream', 'night', 'day',
                                'war', 'peace', 'love', 'story', 'tale', 'song'}
                if correct_words[-1] not in excluded_words:
                    return True
            
            # Check for special cases like "da Vinci" for "Leonardo da Vinci"
            if len(correct_words) >= 3:
                # Check last two words combined
                last_two = ' '.join(correct_words[-2:])
                if user_norm == last_two:
                    return True
        
        return False

    def check_abbreviation(self, user_norm: str, correct_norm: str) -> bool:
        """Check if user provided a common abbreviation"""
        # Direct abbreviation lookup
        if user_norm in self.abbreviations:
            expanded = self.abbreviations[user_norm]
            if expanded == correct_norm or correct_norm == user_norm:
                return True
        
        # Check if correct answer contains the abbreviation
        for abbr, full in self.abbreviations.items():
            if abbr == user_norm and full in correct_norm:
                return True
            if full == user_norm and abbr in correct_norm:
                return True
        
        return False

    def check_word_subset(self, user_words: Set[str], correct_words: Set[str]) -> Tuple[bool, float]:
        """Check if user words are a meaningful subset of correct answer"""
        # Remove articles for comparison
        user_content = user_words - self.articles
        correct_content = correct_words - self.articles
        
        if not user_content:  # User only provided articles
            return False, 0.0
        
        # Single word answers need special handling
        if len(user_content) == 1:
            single_word = list(user_content)[0]
            
            # Don't match single common words
            common_words = {'king', 'queen', 'night', 'day', 'time', 'man', 'woman',
                          'boy', 'girl', 'love', 'war', 'peace', 'world', 'dream'}
            if single_word in common_words:
                return False, 0.0
            
            # For single word to match, it should be substantial (4+ chars)
            # and be the main word in a short answer
            if len(single_word) >= 4 and single_word in correct_content:
                if len(correct_content) <= 2:  # Very short answer
                    return True, 0.7
        
        # Check if all user words are in correct answer
        if user_content.issubset(correct_content):
            # Calculate coverage
            coverage = len(user_content) / max(1, len(correct_content))
            
            # Need at least 50% of content words for a match
            if coverage >= self.MIN_WORD_COVERAGE:
                return True, coverage
        
        return False, 0.0

    def check_answer(self, user_answer: str, correct_answer: str, threshold: float = 0.85) -> Tuple[bool, float]:
        """
        Main method to check if user's answer is correct
        Returns (is_correct, confidence_score)
        """
        if not user_answer or not correct_answer:
            return False, 0.0
        
        # Extract alternatives from correct answer
        alternatives = self.extract_alternatives(correct_answer)
        
        # Check against each alternative
        best_match = (False, 0.0)
        
        for alt in alternatives:
            is_correct, confidence = self._check_single(user_answer, alt, threshold)
            if confidence > best_match[1]:
                best_match = (is_correct, confidence)
            if is_correct:
                return is_correct, confidence
        
        return best_match

    def _check_single(self, user_answer: str, correct_answer: str, threshold: float) -> Tuple[bool, float]:
        """Check a single answer against a single correct answer"""
        
        # Normalize both answers
        user_norm = self.normalize_answer(user_answer)
        correct_norm = self.normalize_answer(correct_answer)
        
        # 1. Exact match
        if user_norm == correct_norm:
            return True, 1.0
        
        # 2. Check abbreviations
        if self.check_abbreviation(user_norm, correct_norm):
            return True, 0.95
        
        # 3. Last name only (for people)
        if self.check_last_name(user_norm, correct_norm):
            return True, 0.9
        
        # 4. Word subset matching
        user_words = set(user_norm.split())
        correct_words = set(correct_norm.split())
        
        is_subset, coverage = self.check_word_subset(user_words, correct_words)
        if is_subset:
            return True, 0.85 + (coverage * 0.1)  # 0.85-0.95 based on coverage
        
        # 5. Valid substring matching (with word boundary checks)
        if self.is_valid_substring_match(user_norm, correct_norm):
            return True, 0.8
        
        # 6. Fuzzy matching for typos
        similarity = SequenceMatcher(None, user_norm, correct_norm).ratio()
        
        # Need high similarity for fuzzy match to avoid false positives
        if similarity >= max(threshold, 0.85):
            return True, similarity
        
        return False, similarity


def test_answer_checker():
    """Test the answer checker with various cases"""
    checker = JeopardyAnswerChecker()
    
    # Test cases that should PASS
    print("Testing CORRECT answers (should pass):")
    correct_cases = [
        ("Washington", "George Washington", "Last name match"),
        ("What is Mars", "Mars", "Question format"),
        ("kennedy", "John F. Kennedy", "Last name match"),
        ("JFK", "John F. Kennedy", "Abbreviation"),
        ("FDR", "Franklin Delano Roosevelt", "Abbreviation"),
        ("united states", "The United States of America", "Key words"),
        ("Romeo and Juliet", "Romeo and Juliet", "Exact match"),
        ("Zimbabwe", "Zimbabwe (or Rhodesia)", "Alternative answer"),
        ("Rhodesia", "Zimbabwe (or Rhodesia)", "Alternative answer"),
    ]
    
    for user, correct, description in correct_cases:
        result, confidence = checker.check_answer(user, correct)
        status = "✓" if result else "✗"
        print(f"  {status} '{user}' vs '{correct}' - {description}: {confidence:.2f}")
    
    print("\nTesting INCORRECT answers (should fail):")
    incorrect_cases = [
        ("car", "carburetor", "False substring"),
        ("ton", "Washington", "False substring"),
        ("cat", "category", "False substring"),
        ("art", "Mozart", "False substring"),
        ("king", "Martin Luther King", "Incomplete name"),
        ("the", "The United States", "Just article"),
        ("a", "A Midsummer Night's Dream", "Just article"),
        ("night", "A Midsummer Night's Dream", "Random word"),
        ("123", "1234567", "Number substring"),
    ]
    
    for user, correct, description in incorrect_cases:
        result, confidence = checker.check_answer(user, correct)
        status = "✓" if not result else "✗"  # We want these to fail
        print(f"  {status} '{user}' vs '{correct}' - {description}: {confidence:.2f}")
    
    print("\nAll tests completed!")


if __name__ == "__main__":
    test_answer_checker()