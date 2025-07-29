"""
Fix the questions in the database by downloading a proper dataset.
For now, we'll create sample questions with real answers.
"""

import json
import os

# Sample Jeopardy questions with proper answers
SAMPLE_QUESTIONS = [
    {
        "category": "U.S. PRESIDENTS",
        "question": "He was the first president born in the 20th century",
        "answer": "John F. Kennedy",
        "value": 200,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "U.S. PRESIDENTS", 
        "question": "This president served the shortest term in office, dying after just 31 days",
        "answer": "William Henry Harrison",
        "value": 400,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "SCIENCE",
        "question": "This element with atomic number 79 is a precious metal often used in jewelry",
        "answer": "Gold",
        "value": 200,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "SCIENCE",
        "question": "The speed of light in a vacuum is approximately 186,000 miles per this unit of time",
        "answer": "Second",
        "value": 400,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "WORLD CAPITALS",
        "question": "This European capital on the Danube River was once two separate cities: Buda and Pest",
        "answer": "Budapest",
        "value": 200,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "WORLD CAPITALS",
        "question": "The capital of Australia, it was purpose-built and is located between Sydney and Melbourne",
        "answer": "Canberra",
        "value": 400,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "LITERATURE",
        "question": "This Shakespeare play features the famous line 'To be or not to be'",
        "answer": "Hamlet",
        "value": 200,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "LITERATURE",
        "question": "George Orwell wrote this dystopian novel featuring Big Brother in 1949",
        "answer": "1984",
        "value": 400,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "MOVIES",
        "question": "This 1975 Steven Spielberg film made people afraid to go in the water",
        "answer": "Jaws",
        "value": 200,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "MOVIES",
        "question": "Tom Hanks won consecutive Best Actor Oscars for Philadelphia and this 1994 film",
        "answer": "Forrest Gump",
        "value": 400,
        "round": "Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "SPORTS",
        "question": "This NFL team has won the most Super Bowl championships with 6 titles",
        "answer": "New England Patriots",
        "value": 600,
        "round": "Double Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "SPORTS",
        "question": "Michael Jordan won 6 NBA championships with this team in the 1990s",
        "answer": "Chicago Bulls",
        "value": 800,
        "round": "Double Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "HISTORY",
        "question": "This French military leader crowned himself Emperor in 1804",
        "answer": "Napoleon Bonaparte",
        "value": 600,
        "round": "Double Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "HISTORY",
        "question": "The ancient city of Troy was located in what is now this country",
        "answer": "Turkey",
        "value": 800,
        "round": "Double Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "GEOGRAPHY",
        "question": "This African country is home to Victoria Falls",
        "answer": "Zimbabwe (or Zambia)",
        "value": 600,
        "round": "Double Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "GEOGRAPHY",
        "question": "The world's largest desert, it covers most of North Africa",
        "answer": "Sahara",
        "value": 800,
        "round": "Double Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "MUSIC",
        "question": "This 'King of Pop' released the best-selling album of all time, 'Thriller'",
        "answer": "Michael Jackson",
        "value": 600,
        "round": "Double Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "MUSIC",
        "question": "This British band sang 'Bohemian Rhapsody' and was fronted by Freddie Mercury",
        "answer": "Queen",
        "value": 800,
        "round": "Double Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "TECHNOLOGY",
        "question": "This company, founded by Steve Jobs, Steve Wozniak, and Ronald Wayne, introduced the iPhone in 2007",
        "answer": "Apple",
        "value": 600,
        "round": "Double Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    },
    {
        "category": "FINAL JEOPARDY",
        "question": "This American author wrote 'The Great Gatsby' and was named after the author of 'The Star-Spangled Banner'",
        "answer": "F. Scott Fitzgerald",
        "value": 0,
        "round": "Final Jeopardy!",
        "air_date": "2024-01-01",
        "show_number": 9000
    }
]

def create_fixed_questions():
    """Create a file with properly formatted questions."""
    # Expand the sample to have more variety
    expanded_questions = []
    
    # Add the original samples
    expanded_questions.extend(SAMPLE_QUESTIONS)
    
    # Add more questions by varying the existing ones
    for i in range(10):  # Create 10 more games worth
        show_num = 9001 + i
        for q in SAMPLE_QUESTIONS:
            new_q = q.copy()
            new_q['show_number'] = show_num
            # Slightly modify values
            if new_q['round'] == 'Jeopardy!':
                new_q['value'] = (i % 5 + 1) * 200
            elif new_q['round'] == 'Double Jeopardy!':
                new_q['value'] = (i % 5 + 1) * 400
            expanded_questions.append(new_q)
    
    # Save to file
    output_file = 'data/jeopardy_questions_fixed.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(expanded_questions, f, indent=2, ensure_ascii=False)
    
    print(f"Created {output_file} with {len(expanded_questions)} properly formatted questions")
    
    # Show some examples
    print("\nSample questions:")
    for q in SAMPLE_QUESTIONS[:3]:
        print(f"\nCategory: {q['category']}")
        print(f"Question: {q['question']}")
        print(f"Answer: {q['answer']}")
        print(f"Value: ${q['value']}")

if __name__ == "__main__":
    create_fixed_questions()