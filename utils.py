import re

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
