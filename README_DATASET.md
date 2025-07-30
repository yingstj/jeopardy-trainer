# Jeopardy Dataset Information

## Current Dataset

Your Jeopardy AI Trainer currently contains:
- **100,120 questions** across **1,004 categories**
- Mix of generated variations and hand-crafted comprehensive questions
- Categories include: Science, History, Literature, Geography, Sports, Technology, and many more

## Getting More Questions

### Option 1: J-Archive (500,000+ Real Questions)
J-Archive (https://j-archive.com) contains every Jeopardy question aired since 1984.

**Manual Download Steps:**
1. Visit https://j-archive.com
2. Click on a season (e.g., "Season 40")
3. Click on individual games
4. Copy questions manually or use browser extensions

**Automated Options:**
- Use the provided `j_archive_scraper_fixed.py` (may need adjustments)
- Consider using existing datasets others have compiled from J-Archive

### Option 2: Pre-compiled Datasets

**Kaggle Datasets:**
1. **200,000+ Jeopardy Questions**
   - https://www.kaggle.com/datasets/tunguz/200000-jeopardy-questions
   - Format: CSV with columns: Show Number, Air Date, Round, Category, Value, Question, Answer
   - Download and use `load_jeopardy_csv.py` to import

2. **Jeopardy Dataset (Updated)**
   - https://www.kaggle.com/datasets/aravindram11/jeopardy-dataset-updated
   - Contains recent seasons

**GitHub Datasets:**
1. **jwolle1/jeopardy_clue_dataset**
   - https://github.com/jwolle1/jeopardy_clue_dataset
   - 538,845 clues from Seasons 1-41
   - Format: TSV files
   - Use `download_github_dataset.py` to import

### Option 3: Reddit Dataset
- Search Reddit r/datasets for "Jeopardy JSON"
- Often contains 200,000+ questions in JSON format
- Direct import compatible with our database

## Loading New Datasets

### For CSV files:
```bash
python3 load_jeopardy_csv.py path/to/jeopardy.csv
```

### For JSON files:
```python
from database import JeopardyDatabase
db = JeopardyDatabase()
count = db.load_questions_from_json('path/to/questions.json')
print(f"Loaded {count} questions")
```

### Expected JSON format:
```json
[
  {
    "category": "SCIENCE",
    "question": "This planet is known as the Red Planet",
    "answer": "Mars",
    "value": 200,
    "round": "Jeopardy!",
    "air_date": "2024-01-01",
    "show_number": "9000"
  }
]
```

## Data Quality Tips

1. **Avoid Numeric Answers**: Ensure answers are descriptive (e.g., "The year nineteen eighty-four" not "1984")
2. **Clean HTML**: Remove any HTML tags from questions/answers
3. **Consistent Categories**: Convert categories to uppercase for consistency
4. **Value Ranges**: 
   - Jeopardy!: $200, $400, $600, $800, $1000
   - Double Jeopardy!: $400, $800, $1200, $1600, $2000
   - Final Jeopardy!: $0 (no fixed value)

## Current Database Schema

The database expects these fields:
- `category` (TEXT): The category name in uppercase
- `question` (TEXT): The clue/question text
- `answer` (TEXT): The correct response
- `value` (INTEGER): Dollar value (0 for Final Jeopardy)
- `round` (TEXT): "Jeopardy!", "Double Jeopardy!", or "Final Jeopardy!"
- `air_date` (TEXT): Date in YYYY-MM-DD format
- `show_number` (TEXT): Show/game number

## Recommended Approach

1. Start with the current 100,000+ questions
2. If you need more, download the Kaggle 200,000+ dataset
3. For the most comprehensive set, use the GitHub 538,000+ dataset
4. The fuzzy answer matching will handle variations in answers

Remember: Quality is more important than quantity. The AI adaptation system works best with well-formatted, accurate questions.