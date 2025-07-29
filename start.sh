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

# Try to load sample data if database is empty
python -c "
from database import JeopardyDatabase
db = JeopardyDatabase()
cats = db.get_categories()
if len(cats) == 0:
    print('Database empty, loading sample data...')
    import subprocess
    subprocess.run(['python', 'data_processor.py', '--load-file', 'data/questions_sample.json'])
else:
    print(f'Database has {len(cats)} categories')
"

# Start the web server
echo "Starting web server..."
exec gunicorn app:app --bind 0.0.0.0:$PORT