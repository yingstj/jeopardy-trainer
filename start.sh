#!/bin/bash
# Startup script for Railway

echo "Starting Jeopardy AI Trainer..."

# Debug: Check environment
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."
echo "PGDATABASE: $PGDATABASE"
echo "PGHOST: $PGHOST"

# Run database initialization
echo "Checking database..."
python init_db.py

# Try to load sample data if database is empty or has bad data
python -c "
from database import JeopardyDatabase
db = JeopardyDatabase()
cats = db.get_categories()

# Check if we have bad data (answers that are just numbers)
questions = db.get_questions(count=5)
has_bad_data = any(q['answer'].isdigit() for q in questions if q['answer'])

if len(cats) == 0 or has_bad_data:
    print('Database empty or has bad data, loading fixed questions...')
    
    # Clear bad data first if using PostgreSQL
    if db.db_type == 'postgresql':
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('TRUNCATE TABLE questions CASCADE')
            conn.commit()
            cursor.close()
    
    import subprocess
    subprocess.run(['python', 'data_processor.py', '--load-file', 'data/jeopardy_questions_fixed.json'])
else:
    print(f'Database has {len(cats)} categories with good data')
"

# Start the web server
echo "Starting web server..."
exec gunicorn app:app --bind 0.0.0.0:$PORT