#!/usr/bin/env python3
"""Analyze the quality and comprehensiveness of questions."""

import json
import random
from collections import defaultdict

# Load the generated questions
with open('data/jeopardy_100k_generated.json', 'r') as f:
    questions = json.load(f)

# Clean questions by removing ID markers
clean_questions = []
for q in questions:
    clean_q = q.copy()
    if '[#' in q['question']:
        clean_q['question'] = q['question'].split(' [#')[0]
    clean_questions.append(clean_q)

# Get unique base questions
unique_questions = {}
for q in clean_questions:
    key = (q['category'].replace('CLASSIC ', '').replace('MODERN ', '').replace('WORLD ', '').replace('AMERICAN ', '').replace('FAMOUS ', '').replace('NOTABLE ', '').replace('HISTORIC ', '').replace(' POTPOURRI', '').replace(' GRAB BAG', '').replace(' MIX', '').replace(' & MORE', '').replace(' FACTS', '').replace(' TRIVIA', ''), 
           q['question'], 
           q['answer'])
    if key not in unique_questions:
        unique_questions[key] = q

print(f"Total questions in database: {len(questions):,}")
print(f"Unique base questions: {len(unique_questions)}")

# Analyze answer quality
print("\n" + "="*60)
print("ANSWER QUALITY ANALYSIS")
print("="*60)

# Check for numeric answers (bad)
numeric_answers = [q for q in unique_questions.values() if q['answer'].isdigit()]
print(f"\nNumeric-only answers: {len(numeric_answers)} (should be 0)")
if numeric_answers:
    print("Examples of bad numeric answers:")
    for q in numeric_answers[:3]:
        print(f"  - {q['question']} -> {q['answer']}")

# Check for proper answers
proper_answers = [q for q in unique_questions.values() if len(q['answer']) > 3 and not q['answer'].isdigit()]
print(f"\nProper answers: {len(proper_answers)}")

# Category analysis
print("\n" + "="*60)
print("CATEGORY ANALYSIS")
print("="*60)

by_category = defaultdict(list)
for q in unique_questions.values():
    base_cat = q['category'].split(':')[0].split(' ')[0] if ':' in q['category'] else q['category']
    by_category[base_cat].append(q)

print(f"\nNumber of main categories: {len(by_category)}")
print("\nQuestions per category:")
for cat in sorted(by_category.keys()):
    print(f"  {cat}: {len(by_category[cat])} questions")

# Show comprehensive samples
print("\n" + "="*60)
print("SAMPLE QUESTIONS BY CATEGORY")
print("="*60)

categories_to_show = ['SCIENCE', 'HISTORY', 'LITERATURE', 'GEOGRAPHY', 'MOVIES', 'SPORTS', 'TECHNOLOGY', 'MUSIC', 'WORLD CAPITALS', 'U.S. PRESIDENTS']

for cat in categories_to_show:
    if cat in by_category:
        print(f"\n{cat}:")
        # Show 5 random questions from this category
        sample = random.sample(by_category[cat], min(5, len(by_category[cat])))
        for i, q in enumerate(sample, 1):
            print(f"  {i}. Q: {q['question']}")
            print(f"     A: {q['answer']} (${q['value']})")

# Value distribution
print("\n" + "="*60)
print("VALUE DISTRIBUTION")
print("="*60)

value_counts = defaultdict(int)
for q in questions:
    value_counts[q['value']] += 1

print("\nQuestion count by value:")
for value in sorted(value_counts.keys()):
    print(f"  ${value}: {value_counts[value]:,} questions")

# Check answer comprehensiveness
print("\n" + "="*60)
print("ANSWER COMPREHENSIVENESS")
print("="*60)

# Analyze answer lengths
answer_lengths = [len(q['answer']) for q in unique_questions.values()]
avg_length = sum(answer_lengths) / len(answer_lengths)

print(f"\nAverage answer length: {avg_length:.1f} characters")
print(f"Shortest answer: {min(answer_lengths)} characters")
print(f"Longest answer: {max(answer_lengths)} characters")

# Show examples of comprehensive answers
comprehensive = [q for q in unique_questions.values() if len(q['answer']) > 20]
print(f"\nAnswers with detailed information: {len(comprehensive)}")
print("Examples:")
for q in random.sample(comprehensive, min(5, len(comprehensive))):
    print(f"  Q: {q['question']}")
    print(f"  A: {q['answer']}")
    print()

# Check for variety in question types
print("\n" + "="*60)
print("QUESTION TYPE VARIETY")
print("="*60)

question_starters = defaultdict(int)
for q in unique_questions.values():
    first_word = q['question'].split()[0] if q['question'] else ""
    question_starters[first_word] += 1

print("\nMost common question starters:")
for word, count in sorted(question_starters.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  '{word}': {count} times")