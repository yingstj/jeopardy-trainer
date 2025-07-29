import csv
import json

def convert_csv_to_json():
    """Convert the CSV file to JSON format for the data processor."""
    questions = []
    
    with open('data/all_jeopardy_clues.csv', 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for i, row in enumerate(reader):
            # Limit to first 1000 questions for testing
            if i >= 1000:
                break
                
            # Extract value from the correct_response field (contains value + answer)
            correct_response = row.get('correct_response', '').strip()
            value = 0
            answer = correct_response
            
            # Try to extract value if it starts with $
            if correct_response.startswith('$'):
                parts = correct_response.split('\n')
                if len(parts) >= 2:
                    try:
                        value = int(parts[0].replace('$', '').replace(',', ''))
                        answer = '\n'.join(parts[1:])
                    except:
                        pass
            
            question = {
                'category': row.get('category', '').strip(),
                'question': row.get('clue', '').strip(),
                'answer': answer,
                'value': value,
                'round': row.get('round', '').strip(),
                'show_number': row.get('game_id', '').strip(),
                'air_date': ''  # Not in CSV
            }
            
            # Only add if we have the essential fields
            if question['category'] and question['question'] and question['answer']:
                questions.append(question)
    
    # Save to JSON file
    with open('data/questions_sample.json', 'w', encoding='utf-8') as jsonfile:
        json.dump(questions, jsonfile, indent=2, ensure_ascii=False)
    
    print(f"Converted {len(questions)} questions to JSON format")
    print("Saved to data/questions_sample.json")

if __name__ == "__main__":
    convert_csv_to_json()