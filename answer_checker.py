"""
Fuzzy answer matching for Jeopardy questions.
Handles partial matches, common variations, and minor typos.
"""

import re
import difflib
from typing import List, Tuple, Optional

class AnswerChecker:
    def __init__(self):
        # Common articles and words to ignore
        self.ignore_words = {'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for'}
        
        # Common abbreviations and their full forms
        self.abbreviations = {
            'st': 'saint',
            'mt': 'mount',
            'mr': 'mister',
            'mrs': 'missus',
            'ms': 'miss',
            'dr': 'doctor',
            'jr': 'junior',
            'sr': 'senior',
            'usa': 'united states',
            'uk': 'united kingdom',
            'nyc': 'new york city',
            'la': 'los angeles',
            'sf': 'san francisco',
            'dc': 'district of columbia',
            'jfk': 'john f kennedy',
            'fdr': 'franklin d roosevelt',
            'mlk': 'martin luther king',
            'wwi': 'world war one',
            'wwii': 'world war two'
        }
        
        # Threshold for fuzzy matching (0.0 to 1.0)
        self.similarity_threshold = 0.80  # Lowered for better matching
        
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove punctuation except apostrophes
        text = re.sub(r"[^\w\s'-]", " ", text)
        
        # Handle possessives
        text = re.sub(r"'s\b", "", text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """Split text into meaningful tokens."""
        text = self.normalize_text(text)
        tokens = text.split()
        
        # Expand abbreviations
        expanded_tokens = []
        for token in tokens:
            if token in self.abbreviations:
                expanded_tokens.append(self.abbreviations[token])
            else:
                expanded_tokens.append(token)
        
        return expanded_tokens
    
    def remove_common_words(self, tokens: List[str]) -> List[str]:
        """Remove common articles and prepositions."""
        return [t for t in tokens if t not in self.ignore_words]
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two strings."""
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def check_answer(self, user_answer: str, correct_answer: str) -> Tuple[bool, float, str]:
        """
        Check if user answer matches correct answer.
        
        Returns:
            Tuple of (is_correct, confidence, reason)
        """
        if not user_answer or not correct_answer:
            return False, 0.0, "Empty answer"
        
        # Handle multiple acceptable answers (e.g., "Zimbabwe (or Zambia)")
        correct_options = []
        if '(or' in correct_answer:
            # Extract main answer and alternatives
            main_part = correct_answer.split('(or')[0].strip()
            alt_part = correct_answer.split('(or')[1].strip(' )')
            correct_options = [main_part, alt_part]
        elif ' or ' in correct_answer.lower():
            correct_options = [opt.strip() for opt in correct_answer.split(' or ')]
        else:
            correct_options = [correct_answer]
        
        # Check each possible correct answer
        best_match = 0.0
        best_reason = ""
        
        for correct_option in correct_options:
            # 1. Exact match (case-insensitive)
            if self.normalize_text(user_answer) == self.normalize_text(correct_option):
                return True, 1.0, "Exact match"
            
            # 2. Partial name match (e.g., "Washington" for "George Washington")
            user_tokens = self.tokenize(user_answer)
            correct_tokens = self.tokenize(correct_option)
            
            # Check if user answer is contained in correct answer
            user_normalized = self.normalize_text(user_answer)
            correct_normalized = self.normalize_text(correct_option)
            
            if user_normalized in correct_normalized:
                confidence = len(user_normalized) / len(correct_normalized)
                if confidence > 0.5:  # At least half the answer
                    return True, confidence, "Partial match (substring)"
            
            # 3. Last name only for people (e.g., "Kennedy" for "John F. Kennedy")
            if len(correct_tokens) >= 2 and len(user_tokens) == 1:
                # Check if user gave last name
                if user_tokens[0] == correct_tokens[-1]:
                    return True, 0.9, "Last name match"
                # Check if user gave first name (less common but acceptable)
                if user_tokens[0] == correct_tokens[0]:
                    return True, 0.8, "First name match"
            
            # 4. Key words match (removing common words)
            user_key_words = set(self.remove_common_words(user_tokens))
            correct_key_words = set(self.remove_common_words(correct_tokens))
            
            if user_key_words and correct_key_words:
                # Check if all user keywords are in correct answer
                if user_key_words.issubset(correct_key_words):
                    confidence = len(user_key_words) / len(correct_key_words)
                    if confidence > 0.5:
                        return True, confidence, "Key words match"
                
                # Check overlap
                overlap = user_key_words.intersection(correct_key_words)
                if len(overlap) >= len(user_key_words) * 0.8:  # 80% of user words match
                    confidence = len(overlap) / len(correct_key_words)
                    if confidence > best_match:
                        best_match = confidence
                        best_reason = "Partial key words match"
            
            # 5. Fuzzy string matching for typos
            similarity = self.calculate_similarity(user_normalized, correct_normalized)
            if similarity > best_match:
                best_match = similarity
                best_reason = f"Fuzzy match ({similarity:.0%} similar)"
        
        # Return best match result
        if best_match >= self.similarity_threshold:
            return True, best_match, best_reason
        else:
            return False, best_match, f"Not similar enough ({best_match:.0%})"
    
    def get_feedback(self, user_answer: str, correct_answer: str, is_correct: bool, confidence: float, reason: str) -> str:
        """Generate helpful feedback for the user."""
        if is_correct:
            if confidence == 1.0:
                return "✓ Correct!"
            elif confidence > 0.9:
                return f"✓ Correct! ({reason})"
            else:
                return f"✓ Acceptable answer! ({reason})"
        else:
            if confidence > 0.7:
                return f"✗ Close, but not quite. The answer was: {correct_answer}"
            else:
                return f"✗ The correct answer was: {correct_answer}"


# Example usage and tests
if __name__ == "__main__":
    checker = AnswerChecker()
    
    test_cases = [
        # (user_answer, correct_answer, should_be_correct)
        ("washington", "George Washington", True),
        ("Washington", "George Washington", True),
        ("george washington", "George Washington", True),
        ("G Washington", "George Washington", True),
        ("kennedy", "John F. Kennedy", True),
        ("JFK", "John F. Kennedy", True),
        ("gold", "Gold", True),
        ("the gold", "Gold", True),
        ("budapest", "Budapest", True),
        ("buda pest", "Budapest", True),  # Common misspelling
        ("1984", "1984", True),
        ("nineteen eighty four", "1984", True),
        ("forrest gump", "Forrest Gump", True),
        ("forest gump", "Forrest Gump", True),  # Common misspelling
        ("chicago bulls", "Chicago Bulls", True),
        ("bulls", "Chicago Bulls", True),
        ("Bulls", "Chicago Bulls", True),
        ("Napoleon", "Napoleon Bonaparte", True),
        ("Napoleon Bonaparte", "Napoleon Bonaparte", True),
        ("zimbabwe", "Zimbabwe (or Zambia)", True),
        ("zambia", "Zimbabwe (or Zambia)", True),
        ("wrong answer", "George Washington", False),
    ]
    
    print("Testing Answer Checker:\n")
    for user_answer, correct_answer, expected in test_cases:
        is_correct, confidence, reason = checker.check_answer(user_answer, correct_answer)
        status = "✓" if is_correct == expected else "✗"
        print(f"{status} '{user_answer}' vs '{correct_answer}' -> {is_correct} ({confidence:.0%}) - {reason}")
        if is_correct != expected:
            print(f"   ERROR: Expected {expected}")
    
    print("\n\nFeedback Examples:\n")
    feedback_examples = [
        ("washington", "George Washington"),
        ("kenedy", "John F. Kennedy"),  # Typo
        ("paris", "London"),
    ]
    
    for user_answer, correct_answer in feedback_examples:
        is_correct, confidence, reason = checker.check_answer(user_answer, correct_answer)
        feedback = checker.get_feedback(user_answer, correct_answer, is_correct, confidence, reason)
        print(f"'{user_answer}' vs '{correct_answer}' -> {feedback}")