#!/usr/bin/env python3
"""
Create a comprehensive set of Jeopardy questions with detailed, educational answers.
"""

import json
from database import JeopardyDatabase

COMPREHENSIVE_QUESTIONS = [
    # SCIENCE - Expanded with detailed answers
    {"category": "BIOLOGY", "question": "This process converts light energy into chemical energy in plants", "answer": "Photosynthesis", "value": 200},
    {"category": "BIOLOGY", "question": "The powerhouse of the cell responsible for producing ATP", "answer": "Mitochondria", "value": 400},
    {"category": "BIOLOGY", "question": "This double helix molecule carries genetic information", "answer": "DNA (Deoxyribonucleic acid)", "value": 200},
    {"category": "BIOLOGY", "question": "The process by which cells divide to produce two identical daughter cells", "answer": "Mitosis", "value": 600},
    {"category": "BIOLOGY", "question": "This organ system includes the heart, blood vessels, and blood", "answer": "Circulatory system (or Cardiovascular system)", "value": 400},
    {"category": "BIOLOGY", "question": "The study of heredity and the variation of inherited characteristics", "answer": "Genetics", "value": 400},
    {"category": "BIOLOGY", "question": "These proteins speed up chemical reactions in living organisms", "answer": "Enzymes", "value": 600},
    {"category": "BIOLOGY", "question": "The largest organ of the human body", "answer": "Skin", "value": 200},
    {"category": "BIOLOGY", "question": "This kingdom includes mushrooms, yeasts, and molds", "answer": "Fungi", "value": 400},
    {"category": "BIOLOGY", "question": "The process by which organisms maintain a stable internal environment", "answer": "Homeostasis", "value": 800},
    
    # PHYSICS
    {"category": "PHYSICS", "question": "The force that attracts objects toward the center of Earth", "answer": "Gravity", "value": 200},
    {"category": "PHYSICS", "question": "This scientist developed the three laws of motion", "answer": "Sir Isaac Newton", "value": 400},
    {"category": "PHYSICS", "question": "The speed of light in a vacuum, approximately 300,000 km per second", "answer": "299,792,458 meters per second", "value": 800},
    {"category": "PHYSICS", "question": "E=mc² is the famous equation from this theory", "answer": "Theory of Relativity", "value": 600},
    {"category": "PHYSICS", "question": "The unit of electrical resistance named after a German physicist", "answer": "Ohm", "value": 400},
    {"category": "PHYSICS", "question": "This fundamental particle has a positive charge and is found in the nucleus", "answer": "Proton", "value": 400},
    {"category": "PHYSICS", "question": "The transfer of thermal energy from a hotter object to a cooler one", "answer": "Heat transfer (or Conduction)", "value": 600},
    {"category": "PHYSICS", "question": "This state of matter has neither definite shape nor volume", "answer": "Gas", "value": 200},
    {"category": "PHYSICS", "question": "The bending of light as it passes from one medium to another", "answer": "Refraction", "value": 600},
    {"category": "PHYSICS", "question": "The amount of matter in an object, measured in kilograms", "answer": "Mass", "value": 200},
    
    # CHEMISTRY
    {"category": "CHEMISTRY", "question": "The periodic table element with symbol 'Au'", "answer": "Gold", "value": 200},
    {"category": "CHEMISTRY", "question": "The most abundant gas in Earth's atmosphere", "answer": "Nitrogen", "value": 400},
    {"category": "CHEMISTRY", "question": "H₂O is the chemical formula for this compound", "answer": "Water", "value": 200},
    {"category": "CHEMISTRY", "question": "The pH value of a neutral solution", "answer": "Seven (7)", "value": 400},
    {"category": "CHEMISTRY", "question": "This type of bond involves the sharing of electron pairs", "answer": "Covalent bond", "value": 600},
    {"category": "CHEMISTRY", "question": "The lightest element on the periodic table", "answer": "Hydrogen", "value": 200},
    {"category": "CHEMISTRY", "question": "The study of carbon-based compounds", "answer": "Organic chemistry", "value": 400},
    {"category": "CHEMISTRY", "question": "This noble gas is used in neon signs", "answer": "Neon", "value": 400},
    {"category": "CHEMISTRY", "question": "The process of a solid changing directly to a gas", "answer": "Sublimation", "value": 800},
    {"category": "CHEMISTRY", "question": "The scientist who developed the periodic table", "answer": "Dmitri Mendeleev", "value": 600},
    
    # AMERICAN HISTORY
    {"category": "AMERICAN HISTORY", "question": "The year the Declaration of Independence was signed", "answer": "Seventeen seventy-six (1776)", "value": 200},
    {"category": "AMERICAN HISTORY", "question": "The first ten amendments to the Constitution", "answer": "Bill of Rights", "value": 400},
    {"category": "AMERICAN HISTORY", "question": "This purchase doubled the size of the United States in 1803", "answer": "Louisiana Purchase", "value": 400},
    {"category": "AMERICAN HISTORY", "question": "The bloodiest single-day battle in American history, fought in Maryland", "answer": "Battle of Antietam", "value": 800},
    {"category": "AMERICAN HISTORY", "question": "This president issued the Emancipation Proclamation", "answer": "Abraham Lincoln", "value": 200},
    {"category": "AMERICAN HISTORY", "question": "The 'shot heard 'round the world' began this war", "answer": "American Revolutionary War", "value": 600},
    {"category": "AMERICAN HISTORY", "question": "This trail led pioneers from Missouri to Oregon in the 1840s", "answer": "Oregon Trail", "value": 400},
    {"category": "AMERICAN HISTORY", "question": "The year women gained the right to vote in the United States", "answer": "Nineteen twenty (1920)", "value": 600},
    {"category": "AMERICAN HISTORY", "question": "This act gave 160 acres of land to settlers willing to farm it", "answer": "Homestead Act", "value": 600},
    {"category": "AMERICAN HISTORY", "question": "The youngest elected president in U.S. history", "answer": "John F. Kennedy", "value": 400},
    
    # WORLD WAR II
    {"category": "WORLD WAR II", "question": "The date of the attack on Pearl Harbor", "answer": "December 7, 1941", "value": 400},
    {"category": "WORLD WAR II", "question": "The Allied invasion of Normandy is better known as this", "answer": "D-Day", "value": 200},
    {"category": "WORLD WAR II", "question": "This was the last major German offensive on the Western Front", "answer": "Battle of the Bulge", "value": 600},
    {"category": "WORLD WAR II", "question": "The code name for the development of the atomic bomb", "answer": "Manhattan Project", "value": 400},
    {"category": "WORLD WAR II", "question": "This British Prime Minister led the country through most of the war", "answer": "Winston Churchill", "value": 200},
    {"category": "WORLD WAR II", "question": "The two Japanese cities where atomic bombs were dropped", "answer": "Hiroshima and Nagasaki", "value": 600},
    {"category": "WORLD WAR II", "question": "This conference divided post-war Germany among the Allies", "answer": "Yalta Conference", "value": 800},
    {"category": "WORLD WAR II", "question": "The German air force during World War II", "answer": "Luftwaffe", "value": 600},
    {"category": "WORLD WAR II", "question": "This was Hitler's failed invasion plan of the Soviet Union", "answer": "Operation Barbarossa", "value": 800},
    {"category": "WORLD WAR II", "question": "The largest tank battle in history, fought in Russia", "answer": "Battle of Kursk", "value": 1000},
    
    # SHAKESPEARE
    {"category": "SHAKESPEARE", "question": "Romeo and Juliet are from these two feuding families", "answer": "Montagues and Capulets", "value": 400},
    {"category": "SHAKESPEARE", "question": "This Danish prince seeks revenge for his father's murder", "answer": "Hamlet", "value": 200},
    {"category": "SHAKESPEARE", "question": "'To be or not to be' is from this play", "answer": "Hamlet", "value": 200},
    {"category": "SHAKESPEARE", "question": "The three witches appear in this Scottish play", "answer": "Macbeth", "value": 400},
    {"category": "SHAKESPEARE", "question": "This jealous Moor kills his wife Desdemona", "answer": "Othello", "value": 400},
    {"category": "SHAKESPEARE", "question": "The setting for Romeo and Juliet", "answer": "Verona, Italy", "value": 600},
    {"category": "SHAKESPEARE", "question": "This comedy features the characters Hermia, Lysander, and Puck", "answer": "A Midsummer Night's Dream", "value": 600},
    {"category": "SHAKESPEARE", "question": "King Lear divides his kingdom among these many daughters", "answer": "Three", "value": 400},
    {"category": "SHAKESPEARE", "question": "The theater where many of Shakespeare's plays were performed", "answer": "The Globe Theatre", "value": 600},
    {"category": "SHAKESPEARE", "question": "Shakespeare's wife's name", "answer": "Anne Hathaway", "value": 800},
    
    # CLASSICAL MUSIC
    {"category": "CLASSICAL MUSIC", "question": "This German composer wrote nine symphonies and became deaf", "answer": "Ludwig van Beethoven", "value": 200},
    {"category": "CLASSICAL MUSIC", "question": "Mozart's nationality", "answer": "Austrian", "value": 400},
    {"category": "CLASSICAL MUSIC", "question": "The 'Four Seasons' was composed by this Italian", "answer": "Antonio Vivaldi", "value": 400},
    {"category": "CLASSICAL MUSIC", "question": "This Russian composed 'The Nutcracker' and 'Swan Lake'", "answer": "Pyotr Ilyich Tchaikovsky", "value": 600},
    {"category": "CLASSICAL MUSIC", "question": "Bach's first name", "answer": "Johann Sebastian", "value": 400},
    {"category": "CLASSICAL MUSIC", "question": "The number of movements in a typical symphony", "answer": "Four", "value": 600},
    {"category": "CLASSICAL MUSIC", "question": "This instrument has 88 keys", "answer": "Piano", "value": 200},
    {"category": "CLASSICAL MUSIC", "question": "The highest singing voice type", "answer": "Soprano", "value": 400},
    {"category": "CLASSICAL MUSIC", "question": "Chopin's nationality and primary instrument", "answer": "Polish pianist", "value": 600},
    {"category": "CLASSICAL MUSIC", "question": "The city known as the 'Music Capital' during Mozart's time", "answer": "Vienna", "value": 800},
    
    # SPACE EXPLORATION
    {"category": "SPACE EXPLORATION", "question": "The first human to walk on the moon", "answer": "Neil Armstrong", "value": 200},
    {"category": "SPACE EXPLORATION", "question": "The first artificial satellite launched into space", "answer": "Sputnik 1", "value": 400},
    {"category": "SPACE EXPLORATION", "question": "NASA's program that landed humans on the moon", "answer": "Apollo Program", "value": 400},
    {"category": "SPACE EXPLORATION", "question": "The first American woman in space", "answer": "Sally Ride", "value": 600},
    {"category": "SPACE EXPLORATION", "question": "This space telescope was launched in 1990", "answer": "Hubble Space Telescope", "value": 400},
    {"category": "SPACE EXPLORATION", "question": "The first human in space", "answer": "Yuri Gagarin", "value": 400},
    {"category": "SPACE EXPLORATION", "question": "The red planet NASA rovers have been exploring", "answer": "Mars", "value": 200},
    {"category": "SPACE EXPLORATION", "question": "The reusable spacecraft program that ran from 1981 to 2011", "answer": "Space Shuttle Program", "value": 600},
    {"category": "SPACE EXPLORATION", "question": "The international space laboratory orbiting Earth", "answer": "International Space Station (ISS)", "value": 400},
    {"category": "SPACE EXPLORATION", "question": "This company, founded by Elon Musk, develops reusable rockets", "answer": "SpaceX", "value": 400},
    
    # MYTHOLOGY
    {"category": "MYTHOLOGY", "question": "The king of the Greek gods", "answer": "Zeus", "value": 200},
    {"category": "MYTHOLOGY", "question": "The Greek goddess of wisdom and warfare", "answer": "Athena", "value": 400},
    {"category": "MYTHOLOGY", "question": "This Greek hero's weakness was his heel", "answer": "Achilles", "value": 400},
    {"category": "MYTHOLOGY", "question": "The Norse god of thunder", "answer": "Thor", "value": 200},
    {"category": "MYTHOLOGY", "question": "The Roman name for the Greek god Zeus", "answer": "Jupiter", "value": 600},
    {"category": "MYTHOLOGY", "question": "This titan was punished to hold up the sky", "answer": "Atlas", "value": 600},
    {"category": "MYTHOLOGY", "question": "The three-headed dog guarding the underworld", "answer": "Cerberus", "value": 600},
    {"category": "MYTHOLOGY", "question": "The home of the Greek gods", "answer": "Mount Olympus", "value": 400},
    {"category": "MYTHOLOGY", "question": "The Egyptian god of the dead, often depicted with a jackal head", "answer": "Anubis", "value": 600},
    {"category": "MYTHOLOGY", "question": "This box released all evils into the world", "answer": "Pandora's Box", "value": 400},
    
    # ARCHITECTURE
    {"category": "ARCHITECTURE", "question": "This tower in Paris was built for the 1889 World's Fair", "answer": "Eiffel Tower", "value": 200},
    {"category": "ARCHITECTURE", "question": "The architect who designed Fallingwater", "answer": "Frank Lloyd Wright", "value": 600},
    {"category": "ARCHITECTURE", "question": "This ancient wonder stood in the harbor of Rhodes", "answer": "Colossus of Rhodes", "value": 800},
    {"category": "ARCHITECTURE", "question": "The architectural style of Notre Dame Cathedral", "answer": "Gothic", "value": 600},
    {"category": "ARCHITECTURE", "question": "The world's tallest building, located in Dubai", "answer": "Burj Khalifa", "value": 400},
    {"category": "ARCHITECTURE", "question": "This Roman temple is famous for its dome and oculus", "answer": "Pantheon", "value": 600},
    {"category": "ARCHITECTURE", "question": "The Opera House in this Australian city is shaped like sails", "answer": "Sydney", "value": 400},
    {"category": "ARCHITECTURE", "question": "The style characterized by pointed arches and flying buttresses", "answer": "Gothic architecture", "value": 600},
    {"category": "ARCHITECTURE", "question": "I.M. Pei designed the glass pyramid at this museum", "answer": "The Louvre", "value": 800},
    {"category": "ARCHITECTURE", "question": "The ancient Incan citadel in Peru", "answer": "Machu Picchu", "value": 400},
    
    # HUMAN BODY
    {"category": "HUMAN BODY", "question": "The number of bones in an adult human body", "answer": "Two hundred and six (206)", "value": 400},
    {"category": "HUMAN BODY", "question": "The longest bone in the human body", "answer": "Femur (thighbone)", "value": 600},
    {"category": "HUMAN BODY", "question": "This organ produces insulin", "answer": "Pancreas", "value": 600},
    {"category": "HUMAN BODY", "question": "The four types of blood groups in the ABO system", "answer": "A, B, AB, and O", "value": 800},
    {"category": "HUMAN BODY", "question": "The muscle that separates the chest from the abdomen", "answer": "Diaphragm", "value": 800},
    {"category": "HUMAN BODY", "question": "The smallest bone in the human body, found in the ear", "answer": "Stapes (stirrup)", "value": 1000},
    {"category": "HUMAN BODY", "question": "This gland is known as the 'master gland'", "answer": "Pituitary gland", "value": 800},
    {"category": "HUMAN BODY", "question": "The number of chambers in the human heart", "answer": "Four", "value": 400},
    {"category": "HUMAN BODY", "question": "The protein that gives skin and hair their color", "answer": "Melanin", "value": 600},
    {"category": "HUMAN BODY", "question": "The only muscle attached at just one end", "answer": "Tongue", "value": 1000},
    
    # ECONOMICS
    {"category": "ECONOMICS", "question": "The study of how society manages its scarce resources", "answer": "Economics", "value": 200},
    {"category": "ECONOMICS", "question": "When demand exceeds supply, prices tend to do this", "answer": "Rise (or increase)", "value": 400},
    {"category": "ECONOMICS", "question": "GDP stands for this", "answer": "Gross Domestic Product", "value": 400},
    {"category": "ECONOMICS", "question": "The father of modern economics who wrote 'The Wealth of Nations'", "answer": "Adam Smith", "value": 600},
    {"category": "ECONOMICS", "question": "A sustained increase in the general price level", "answer": "Inflation", "value": 400},
    {"category": "ECONOMICS", "question": "The central bank of the United States", "answer": "Federal Reserve (The Fed)", "value": 600},
    {"category": "ECONOMICS", "question": "This invisible force guides free markets according to Adam Smith", "answer": "Invisible hand", "value": 800},
    {"category": "ECONOMICS", "question": "A market structure with only one seller", "answer": "Monopoly", "value": 600},
    {"category": "ECONOMICS", "question": "The Nobel Prize-winning economist who developed game theory", "answer": "John Nash", "value": 1000},
    {"category": "ECONOMICS", "question": "When a country exports more than it imports, it has this", "answer": "Trade surplus", "value": 800},
]

def load_comprehensive_questions():
    """Load comprehensive questions into the database."""
    print(f"Loading {len(COMPREHENSIVE_QUESTIONS)} comprehensive questions...")
    
    # Save to JSON file
    output_file = 'data/comprehensive_questions.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(COMPREHENSIVE_QUESTIONS, f, indent=2)
    
    print(f"Saved to {output_file}")
    
    # Load into database (append to existing)
    db = JeopardyDatabase()
    
    # First, let's check current count
    with db.get_connection() as conn:
        if db.db_type == 'postgresql':
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM questions')
            before_count = cursor.fetchone()[0]
            cursor.close()
        else:
            before_count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
    
    print(f"Current questions in database: {before_count:,}")
    
    # Load new questions
    count = 0
    with db.get_connection() as conn:
        for q in COMPREHENSIVE_QUESTIONS:
            if db.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO questions (category, question, answer, value, air_date, round, show_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    q['category'],
                    q['question'],
                    q['answer'],
                    q['value'],
                    '2024-01-01',
                    'Jeopardy!' if q['value'] <= 400 else 'Double Jeopardy!',
                    '99999'
                ))
                cursor.close()
            else:
                conn.execute('''
                    INSERT INTO questions (category, question, answer, value, air_date, round, show_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    q['category'],
                    q['question'],
                    q['answer'],
                    q['value'],
                    '2024-01-01',
                    'Jeopardy!' if q['value'] <= 400 else 'Double Jeopardy!',
                    '99999'
                ))
            count += 1
        conn.commit()
    
    # Check new count
    with db.get_connection() as conn:
        if db.db_type == 'postgresql':
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM questions')
            after_count = cursor.fetchone()[0]
            cursor.close()
        else:
            after_count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
    
    print(f"Added {count} comprehensive questions")
    print(f"Total questions now: {after_count:,}")
    
    # Show category distribution
    categories = db.get_categories()
    print(f"\nTotal categories: {len(categories)}")
    print("\nNew categories added:")
    new_cats = ['BIOLOGY', 'PHYSICS', 'CHEMISTRY', 'AMERICAN HISTORY', 'WORLD WAR II', 
                'SHAKESPEARE', 'CLASSICAL MUSIC', 'SPACE EXPLORATION', 'MYTHOLOGY', 
                'ARCHITECTURE', 'HUMAN BODY', 'ECONOMICS']
    for cat, count in categories:
        if cat in new_cats:
            print(f"  {cat}: {count} questions")

if __name__ == "__main__":
    load_comprehensive_questions()