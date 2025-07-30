#!/usr/bin/env python3
"""
Load a comprehensive Jeopardy question dataset.
This creates a large set of properly formatted questions.
"""

import json
import random
from database import JeopardyDatabase

# Comprehensive question dataset
FULL_QUESTIONS = [
    # SCIENCE
    {"category": "SCIENCE", "question": "This element with atomic number 79 is a precious metal", "answer": "Gold", "value": 200},
    {"category": "SCIENCE", "question": "The speed of light in a vacuum is approximately 186,000 miles per this", "answer": "Second", "value": 400},
    {"category": "SCIENCE", "question": "This gas makes up about 78% of Earth's atmosphere", "answer": "Nitrogen", "value": 600},
    {"category": "SCIENCE", "question": "Einstein's famous equation E=mc² relates energy to this", "answer": "Mass", "value": 800},
    {"category": "SCIENCE", "question": "This planet is known as the 'Red Planet'", "answer": "Mars", "value": 200},
    {"category": "SCIENCE", "question": "Water freezes at this temperature in Celsius", "answer": "0 degrees (or zero)", "value": 200},
    {"category": "SCIENCE", "question": "This organ pumps blood throughout the human body", "answer": "Heart", "value": 200},
    {"category": "SCIENCE", "question": "DNA stands for this acid", "answer": "Deoxyribonucleic acid", "value": 1000},
    
    # U.S. PRESIDENTS
    {"category": "U.S. PRESIDENTS", "question": "He was the first president born in the 20th century", "answer": "John F. Kennedy", "value": 400},
    {"category": "U.S. PRESIDENTS", "question": "This president served the shortest term, dying after 31 days", "answer": "William Henry Harrison", "value": 600},
    {"category": "U.S. PRESIDENTS", "question": "The only president to serve more than two terms", "answer": "Franklin D. Roosevelt", "value": 400},
    {"category": "U.S. PRESIDENTS", "question": "He was the first president to resign from office", "answer": "Richard Nixon", "value": 200},
    {"category": "U.S. PRESIDENTS", "question": "This president was never elected as president or vice president", "answer": "Gerald Ford", "value": 800},
    {"category": "U.S. PRESIDENTS", "question": "Known as 'The Father of His Country'", "answer": "George Washington", "value": 200},
    {"category": "U.S. PRESIDENTS", "question": "He wrote the Declaration of Independence", "answer": "Thomas Jefferson", "value": 400},
    
    # WORLD CAPITALS
    {"category": "WORLD CAPITALS", "question": "This European capital was once two cities: Buda and Pest", "answer": "Budapest", "value": 400},
    {"category": "WORLD CAPITALS", "question": "The capital of Australia, purpose-built between Sydney and Melbourne", "answer": "Canberra", "value": 600},
    {"category": "WORLD CAPITALS", "question": "This Asian capital was formerly known as Edo", "answer": "Tokyo", "value": 400},
    {"category": "WORLD CAPITALS", "question": "The capital of Egypt, home to the pyramids of Giza", "answer": "Cairo", "value": 200},
    {"category": "WORLD CAPITALS", "question": "This South American capital sits at 11,942 feet above sea level", "answer": "La Paz", "value": 800},
    {"category": "WORLD CAPITALS", "question": "The capital of Canada", "answer": "Ottawa", "value": 200},
    {"category": "WORLD CAPITALS", "question": "Known as the 'City of Light', it's the capital of France", "answer": "Paris", "value": 200},
    
    # LITERATURE
    {"category": "LITERATURE", "question": "This Shakespeare play features 'To be or not to be'", "answer": "Hamlet", "value": 200},
    {"category": "LITERATURE", "question": "George Orwell wrote this dystopian novel in 1949", "answer": "1984", "value": 400},
    {"category": "LITERATURE", "question": "The author of 'Pride and Prejudice'", "answer": "Jane Austen", "value": 400},
    {"category": "LITERATURE", "question": "This epic poem by Homer tells of the Trojan War", "answer": "The Iliad", "value": 600},
    {"category": "LITERATURE", "question": "Mark Twain's real name", "answer": "Samuel Clemens", "value": 600},
    {"category": "LITERATURE", "question": "The author of the Harry Potter series", "answer": "J.K. Rowling", "value": 200},
    {"category": "LITERATURE", "question": "This Russian wrote 'War and Peace'", "answer": "Leo Tolstoy", "value": 800},
    
    # MOVIES
    {"category": "MOVIES", "question": "This 1975 Spielberg film made people afraid to go in the water", "answer": "Jaws", "value": 200},
    {"category": "MOVIES", "question": "Tom Hanks won consecutive Oscars for Philadelphia and this 1994 film", "answer": "Forrest Gump", "value": 400},
    {"category": "MOVIES", "question": "This 1939 film features Dorothy and her dog Toto", "answer": "The Wizard of Oz", "value": 200},
    {"category": "MOVIES", "question": "'May the Force be with you' is from this film series", "answer": "Star Wars", "value": 200},
    {"category": "MOVIES", "question": "This ship sank in James Cameron's 1997 epic", "answer": "Titanic", "value": 200},
    {"category": "MOVIES", "question": "The highest-grossing film of all time (not adjusted for inflation)", "answer": "Avatar", "value": 600},
    {"category": "MOVIES", "question": "Marlon Brando played Don Corleone in this 1972 film", "answer": "The Godfather", "value": 400},
    
    # HISTORY
    {"category": "HISTORY", "question": "This French military leader crowned himself Emperor in 1804", "answer": "Napoleon Bonaparte", "value": 400},
    {"category": "HISTORY", "question": "The ancient city of Troy was located in what is now this country", "answer": "Turkey", "value": 600},
    {"category": "HISTORY", "question": "This wall divided Berlin from 1961 to 1989", "answer": "Berlin Wall", "value": 200},
    {"category": "HISTORY", "question": "The year Columbus reached the Americas", "answer": "1492", "value": 200},
    {"category": "HISTORY", "question": "This empire built Machu Picchu", "answer": "Inca Empire", "value": 400},
    {"category": "HISTORY", "question": "The first man to walk on the moon", "answer": "Neil Armstrong", "value": 200},
    {"category": "HISTORY", "question": "This ship brought the Pilgrims to America in 1620", "answer": "Mayflower", "value": 400},
    
    # GEOGRAPHY
    {"category": "GEOGRAPHY", "question": "The world's largest desert", "answer": "Sahara", "value": 400},
    {"category": "GEOGRAPHY", "question": "This African country is home to Victoria Falls", "answer": "Zimbabwe (or Zambia)", "value": 600},
    {"category": "GEOGRAPHY", "question": "The longest river in the world", "answer": "Nile River", "value": 400},
    {"category": "GEOGRAPHY", "question": "This mountain range contains Mount Everest", "answer": "Himalayas", "value": 200},
    {"category": "GEOGRAPHY", "question": "The smallest continent by area", "answer": "Australia", "value": 400},
    {"category": "GEOGRAPHY", "question": "This ocean is the largest on Earth", "answer": "Pacific Ocean", "value": 200},
    {"category": "GEOGRAPHY", "question": "The capital of Brazil", "answer": "Brasília", "value": 600},
    
    # SPORTS
    {"category": "SPORTS", "question": "Michael Jordan won 6 NBA championships with this team", "answer": "Chicago Bulls", "value": 400},
    {"category": "SPORTS", "question": "This sport is known as 'America's Pastime'", "answer": "Baseball", "value": 200},
    {"category": "SPORTS", "question": "The Olympics are held every this many years", "answer": "Four", "value": 200},
    {"category": "SPORTS", "question": "This tennis tournament is played on grass courts in London", "answer": "Wimbledon", "value": 400},
    {"category": "SPORTS", "question": "The trophy awarded to the NHL champion", "answer": "Stanley Cup", "value": 400},
    {"category": "SPORTS", "question": "This golfer is known as 'The Golden Bear'", "answer": "Jack Nicklaus", "value": 600},
    {"category": "SPORTS", "question": "The number of players on a basketball team on the court", "answer": "Five", "value": 200},
    
    # MUSIC
    {"category": "MUSIC", "question": "This 'King of Pop' released 'Thriller' in 1982", "answer": "Michael Jackson", "value": 200},
    {"category": "MUSIC", "question": "This British band sang 'Bohemian Rhapsody'", "answer": "Queen", "value": 400},
    {"category": "MUSIC", "question": "The number of strings on a standard guitar", "answer": "Six", "value": 200},
    {"category": "MUSIC", "question": "Mozart's first name", "answer": "Wolfgang", "value": 400},
    {"category": "MUSIC", "question": "This instrument has 88 keys", "answer": "Piano", "value": 200},
    {"category": "MUSIC", "question": "The Beatles were from this English city", "answer": "Liverpool", "value": 400},
    {"category": "MUSIC", "question": "Elvis Presley's middle name", "answer": "Aaron", "value": 600},
    
    # FOOD & DRINK
    {"category": "FOOD & DRINK", "question": "This Italian dish is made with rice", "answer": "Risotto", "value": 400},
    {"category": "FOOD & DRINK", "question": "The main ingredient in guacamole", "answer": "Avocado", "value": 200},
    {"category": "FOOD & DRINK", "question": "This French bread is shaped like a crescent", "answer": "Croissant", "value": 200},
    {"category": "FOOD & DRINK", "question": "Sushi originated in this country", "answer": "Japan", "value": 200},
    {"category": "FOOD & DRINK", "question": "The most consumed beverage in the world after water", "answer": "Tea", "value": 400},
    {"category": "FOOD & DRINK", "question": "This spice is derived from the Crocus flower", "answer": "Saffron", "value": 600},
    {"category": "FOOD & DRINK", "question": "Champagne must come from this region of France", "answer": "Champagne", "value": 400},
    
    # TECHNOLOGY
    {"category": "TECHNOLOGY", "question": "This company created the iPhone", "answer": "Apple", "value": 200},
    {"category": "TECHNOLOGY", "question": "HTML stands for this", "answer": "HyperText Markup Language", "value": 400},
    {"category": "TECHNOLOGY", "question": "The founder of Microsoft", "answer": "Bill Gates", "value": 200},
    {"category": "TECHNOLOGY", "question": "This social media platform was originally called 'The Facebook'", "answer": "Facebook", "value": 200},
    {"category": "TECHNOLOGY", "question": "The year the World Wide Web was invented", "answer": "1989", "value": 600},
    {"category": "TECHNOLOGY", "question": "This search engine's name is a play on the word 'googol'", "answer": "Google", "value": 200},
    {"category": "TECHNOLOGY", "question": "The programming language named after a type of coffee", "answer": "Java", "value": 400},
    
    # ANIMALS
    {"category": "ANIMALS", "question": "The largest mammal on Earth", "answer": "Blue whale", "value": 200},
    {"category": "ANIMALS", "question": "A group of lions is called this", "answer": "Pride", "value": 400},
    {"category": "ANIMALS", "question": "The only mammal capable of true flight", "answer": "Bat", "value": 400},
    {"category": "ANIMALS", "question": "This flightless bird is native to Antarctica", "answer": "Penguin", "value": 200},
    {"category": "ANIMALS", "question": "The number of hearts an octopus has", "answer": "Three", "value": 600},
    {"category": "ANIMALS", "question": "The fastest land animal", "answer": "Cheetah", "value": 200},
    {"category": "ANIMALS", "question": "A baby kangaroo is called this", "answer": "Joey", "value": 400},
]

def create_expanded_dataset():
    """Create an expanded dataset with variations."""
    expanded = []
    
    # Add all base questions
    expanded.extend(FULL_QUESTIONS)
    
    # Create variations by adjusting values and show numbers
    show_number = 9000
    for round_num in range(50):  # Create 50 "shows"
        show_number += 1
        
        # Sample 30 questions per show
        show_questions = random.sample(FULL_QUESTIONS, min(30, len(FULL_QUESTIONS)))
        
        for q in show_questions:
            new_q = q.copy()
            new_q['show_number'] = show_number
            new_q['air_date'] = f'2024-{(round_num % 12) + 1:02d}-{(round_num % 28) + 1:02d}'
            new_q['round'] = 'Jeopardy!' if new_q['value'] <= 400 else 'Double Jeopardy!'
            
            # Vary the values slightly
            if round_num > 20:
                new_q['value'] = new_q['value'] * 2  # Double Jeopardy values
                
            expanded.append(new_q)
    
    return expanded

def load_full_dataset():
    """Load the full dataset into the database."""
    print("Creating comprehensive question dataset...")
    
    questions = create_expanded_dataset()
    print(f"Generated {len(questions)} questions")
    
    # Save to JSON file
    with open('data/jeopardy_full_dataset.json', 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2)
    
    print("Saved to data/jeopardy_full_dataset.json")
    
    # Load into database
    print("Loading into database...")
    db = JeopardyDatabase()
    
    # Clear existing questions
    print("Clearing old questions...")
    with db.get_connection() as conn:
        if db.db_type == 'postgresql':
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_progress')
            cursor.execute('DELETE FROM questions')
            conn.commit()
            cursor.close()
        else:
            conn.execute('DELETE FROM user_progress')
            conn.execute('DELETE FROM questions')
            conn.commit()
    
    # Load new questions
    count = db.load_questions_from_json('data/jeopardy_full_dataset.json')
    print(f"Loaded {count} questions into database")
    
    # Show statistics
    categories = db.get_categories()
    print(f"\nTotal categories: {len(categories)}")
    print("\nTop categories:")
    for cat, count in categories[:10]:
        print(f"  {cat}: {count} questions")

if __name__ == "__main__":
    load_full_dataset()