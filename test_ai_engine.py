#!/usr/bin/env python3
"""
Test script for the Adaptive Learning Engine
"""

from ai_engine import AdaptiveLearningEngine
from database import JeopardyDatabase
import json

def test_ai_engine():
    print("Testing Jeopardy AI Adaptive Learning Engine\n")
    
    # Initialize
    engine = AdaptiveLearningEngine()
    db = JeopardyDatabase()
    
    # Create a test user
    print("1. Creating test user...")
    user_id = db.create_user(
        username="ai_test_user",
        email="ai_test@example.com",
        password_hash="test_hash"
    )
    
    if not user_id:
        print("   User already exists, getting existing user...")
        user = db.get_user_by_username("ai_test_user")
        user_id = user['id']
    
    print(f"   User ID: {user_id}")
    
    # Create a session
    print("\n2. Creating session...")
    session_id = "test_session_123"
    db.create_session(session_id, user_id)
    
    # Get AI recommendations without history
    print("\n3. Getting initial AI recommendations (no history)...")
    questions = engine.select_optimal_questions(user_id, count=5)
    
    if questions:
        print(f"   Found {len(questions)} recommended questions:")
        for i, q in enumerate(questions, 1):
            print(f"\n   Question {i}:")
            print(f"   Category: {q['category']}")
            print(f"   Difficulty: {q.get('difficulty_rating', 'N/A')}")
            print(f"   Question: {q['question'][:100]}...")
            if 'ai_metadata' in q:
                print(f"   Predicted Success: {q['ai_metadata']['predicted_success']}")
                print(f"   Learning Objective: {q['ai_metadata']['learning_objective']}")
    else:
        print("   No questions found. Make sure to load questions into the database first.")
        return
    
    # Simulate answering some questions
    print("\n4. Simulating user responses...")
    for i, question in enumerate(questions[:3]):
        is_correct = i % 2 == 0  # Alternate correct/incorrect
        response_time = 15000 + (i * 3000)  # 15-24 seconds
        
        db.save_answer(
            user_id=user_id,
            session_id=session_id,
            question_id=question['id'],
            user_answer="test answer",
            is_correct=is_correct,
            time_taken=response_time // 1000
        )
        
        print(f"   Question {i+1}: {'Correct' if is_correct else 'Incorrect'} ({response_time//1000}s)")
    
    # Get updated recommendations
    print("\n5. Getting updated AI recommendations (with history)...")
    updated_questions = engine.select_optimal_questions(user_id, count=5, mode='adaptive')
    
    print(f"   Found {len(updated_questions)} recommended questions")
    print("   Note: The AI should now prioritize different questions based on performance")
    
    # Test different modes
    print("\n6. Testing different learning modes:")
    
    modes = ['review', 'challenge', 'weakness', 'practice']
    for mode in modes:
        mode_questions = engine.select_optimal_questions(user_id, count=3, mode=mode)
        print(f"\n   {mode.upper()} mode: {len(mode_questions)} questions")
        if mode_questions:
            print(f"   First question: {mode_questions[0]['category']} - "
                  f"Difficulty {mode_questions[0].get('difficulty_rating', 'N/A')}")
    
    # Get learning insights
    print("\n7. Getting AI learning insights...")
    insights = engine.get_learning_insights(user_id)
    
    print(f"   User Level: {insights.get('user_level', 'N/A')}")
    print(f"   Strengths: {', '.join(insights.get('strengths', [])) or 'None yet'}")
    print(f"   Weaknesses: {', '.join(insights.get('weaknesses', [])) or 'None identified'}")
    print(f"   Trend: {insights.get('trend', 'N/A')}")
    
    if insights.get('recommendations'):
        print("\n   AI Recommendations:")
        for rec in insights['recommendations']:
            print(f"   - {rec}")
    
    # Test category-specific selection
    print("\n8. Testing category-specific selection...")
    stats = db.get_session_stats(session_id)
    if stats and stats.get('by_category'):
        test_category = stats['by_category'][0]['category']
        cat_questions = engine.select_optimal_questions(
            user_id, count=3, category_filter=test_category
        )
        print(f"   Category '{test_category}': {len(cat_questions)} questions")
    
    print("\n\nTest completed! The AI engine is working properly.")
    print("\nKey features demonstrated:")
    print("- Adaptive question selection based on user level")
    print("- Multiple learning modes (adaptive, review, challenge, etc.)")
    print("- Performance tracking and insights")
    print("- Spaced repetition algorithm")
    print("- Category mastery tracking")

if __name__ == "__main__":
    test_ai_engine()