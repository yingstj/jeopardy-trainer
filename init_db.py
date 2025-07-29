#!/usr/bin/env python3
"""
Database initialization script for Railway deployment.
This script initializes the database tables and can optionally load sample data.
"""

import os
import sys
import logging
from database import JeopardyDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with tables and indexes."""
    try:
        # Get database URL from environment or use default
        db_url = os.environ.get('DATABASE_URL')
        
        if db_url:
            logger.info(f"Initializing database with URL: {db_url[:20]}...")
        else:
            logger.info("Initializing database with default SQLite configuration")
        
        # Create database instance - this will automatically initialize tables
        db = JeopardyDatabase(db_url)
        
        logger.info("Database initialization completed successfully!")
        
        # Check if we should load sample data
        if len(sys.argv) > 1 and sys.argv[1] == '--load-sample':
            logger.info("Loading sample data...")
            sample_file = 'data/questions_sample.json'
            if os.path.exists(sample_file):
                count = db.load_questions_from_json(sample_file)
                logger.info(f"Loaded {count} questions from sample file")
            else:
                logger.warning(f"Sample file {sample_file} not found")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)