import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Union, Any
import logging
from urllib.parse import urlparse

# Try to import PostgreSQL adapter
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("psycopg2 not available, PostgreSQL support disabled")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JeopardyDatabase:
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database connection.
        If db_url is provided and starts with 'postgresql://', use PostgreSQL.
        Otherwise, use SQLite.
        """
        self.db_url = db_url or os.environ.get('DATABASE_URL', 'sqlite:///data/jeopardy.db')
        
        # Debug logging
        logger.info(f"DATABASE_URL from env: {os.environ.get('DATABASE_URL', 'NOT SET')[:50]}...")
        logger.info(f"Using db_url: {self.db_url[:50]}...")
        
        # Railway sometimes provides postgres:// instead of postgresql://
        if self.db_url.startswith('postgres://'):
            self.db_url = self.db_url.replace('postgres://', 'postgresql://', 1)
            logger.info("Converted postgres:// to postgresql://")
            
        self.db_type = 'postgresql' if self.db_url.startswith(('postgresql://', 'postgres://')) else 'sqlite'
        
        if self.db_type == 'postgresql' and not POSTGRESQL_AVAILABLE:
            raise RuntimeError("PostgreSQL URL provided but psycopg2 is not installed")
        
        # For SQLite, extract the path
        if self.db_type == 'sqlite':
            self.db_path = self.db_url.replace('sqlite:///', '')
            if self.db_path == self.db_url:  # No sqlite:/// prefix
                self.db_path = self.db_url
            # Handle empty path
            if not self.db_path or self.db_path == 'sqlite:':
                self.db_path = 'data/jeopardy.db'
        
        logger.info(f"Using {self.db_type} database")
        self.init_db()
    
    def get_connection(self) -> Union[sqlite3.Connection, Any]:
        """Get a database connection with appropriate row factory."""
        if self.db_type == 'postgresql':
            conn = psycopg2.connect(self.db_url)
            return conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
    
    def execute_query(self, conn, query: str, params: tuple = None):
        """Execute a query with database-specific handling."""
        if self.db_type == 'postgresql':
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                conn.commit()
                return cur
        else:
            if params:
                return conn.execute(query, params)
            else:
                return conn.execute(query)
    
    def _format_query(self, query: str) -> str:
        """Convert SQLite parameter style (?) to PostgreSQL style (%s) if needed."""
        if self.db_type == 'postgresql':
            return query.replace('?', '%s')
        return query
    
    def _execute_select(self, conn, query: str, params: tuple = None) -> List[Dict]:
        """Execute a SELECT query and return results as list of dicts."""
        query = self._format_query(query)
        
        if self.db_type == 'postgresql':
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results]
        else:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def _execute_insert(self, conn, query: str, params: tuple) -> Optional[int]:
        """Execute an INSERT query and return the last inserted ID."""
        query = self._format_query(query)
        
        if self.db_type == 'postgresql':
            cursor = conn.cursor()
            cursor.execute(query + ' RETURNING id', params)
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        else:
            cursor = conn.execute(query, params)
            return cursor.lastrowid
    
    def init_db(self):
        """Initialize database tables if they don't exist."""
        if self.db_type == 'sqlite':
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self.get_connection() as conn:
            if self.db_type == 'postgresql':
                # PostgreSQL version with SERIAL instead of AUTOINCREMENT
                queries = [
                    '''CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    )''',
                    
                    '''CREATE TABLE IF NOT EXISTS questions (
                        id SERIAL PRIMARY KEY,
                        category VARCHAR(255) NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        value INTEGER,
                        air_date VARCHAR(255),
                        round VARCHAR(255),
                        show_number INTEGER,
                        difficulty_rating REAL DEFAULT NULL,
                        times_asked INTEGER DEFAULT 0,
                        times_correct INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''',
                    
                    '''CREATE TABLE IF NOT EXISTS user_progress (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        session_id VARCHAR(255) NOT NULL,
                        question_id INTEGER NOT NULL,
                        user_answer TEXT,
                        is_correct BOOLEAN,
                        time_taken_seconds INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (question_id) REFERENCES questions (id),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )''',
                    
                    '''CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id VARCHAR(255) PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )''',
                    
                    '''CREATE TABLE IF NOT EXISTS performance_snapshots (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        session_id VARCHAR(255) NOT NULL,
                        snapshot_date DATE NOT NULL,
                        total_questions INTEGER,
                        correct_answers INTEGER,
                        accuracy REAL,
                        avg_time_seconds REAL,
                        categories_played TEXT,
                        FOREIGN KEY (session_id) REFERENCES user_sessions (session_id),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )''',
                    
                    '''CREATE INDEX IF NOT EXISTS idx_session_id ON user_progress(session_id)''',
                    '''CREATE INDEX IF NOT EXISTS idx_category ON questions(category)''',
                    '''CREATE INDEX IF NOT EXISTS idx_question_stats ON questions(times_asked, times_correct)''',
                    '''CREATE INDEX IF NOT EXISTS idx_progress_timestamp ON user_progress(timestamp)'''
                ]
                
                # Execute each query separately for PostgreSQL
                cursor = conn.cursor()
                for query in queries:
                    try:
                        cursor.execute(query)
                    except psycopg2.errors.DuplicateTable:
                        # Table already exists, that's fine
                        pass
                conn.commit()
                cursor.close()
                
            else:
                # SQLite version
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    );
                    
                    CREATE TABLE IF NOT EXISTS questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        value INTEGER,
                        air_date TEXT,
                        round TEXT,
                        show_number INTEGER,
                        difficulty_rating REAL DEFAULT NULL,
                        times_asked INTEGER DEFAULT 0,
                        times_correct INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS user_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_id TEXT NOT NULL,
                        question_id INTEGER NOT NULL,
                        user_answer TEXT,
                        is_correct BOOLEAN,
                        time_taken_seconds INTEGER,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (question_id) REFERENCES questions (id),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS performance_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_id TEXT NOT NULL,
                        snapshot_date DATE NOT NULL,
                        total_questions INTEGER,
                        correct_answers INTEGER,
                        accuracy REAL,
                        avg_time_seconds REAL,
                        categories_played TEXT,
                        FOREIGN KEY (session_id) REFERENCES user_sessions (session_id),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_session_id ON user_progress(session_id);
                    CREATE INDEX IF NOT EXISTS idx_category ON questions(category);
                    CREATE INDEX IF NOT EXISTS idx_question_stats ON questions(times_asked, times_correct);
                    CREATE INDEX IF NOT EXISTS idx_progress_timestamp ON user_progress(timestamp);
                ''')
                conn.commit()
                
            logger.info("Database initialized successfully")
    
    # Question Management
    
    def load_questions_from_json(self, json_file_path: str) -> int:
        """Load questions from a JSON file into the database."""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with self.get_connection() as conn:
                count = 0
                for item in data:
                    # Check if question already exists
                    if self.db_type == 'postgresql':
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        cursor.execute(
                            'SELECT id FROM questions WHERE question = %s AND answer = %s',
                            (item.get('question', ''), item.get('answer', ''))
                        )
                        existing = cursor.fetchone()
                        
                        if not existing:
                            cursor.execute('''
                                INSERT INTO questions (category, question, answer, value, 
                                                     air_date, round, show_number)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ''', (
                                item.get('category', '').upper(),
                                item.get('question', ''),
                                item.get('answer', ''),
                                item.get('value', 0),
                                item.get('air_date', ''),
                                item.get('round', ''),
                                item.get('show_number', 0)
                            ))
                            count += 1
                        cursor.close()
                    else:
                        existing = conn.execute(
                            'SELECT id FROM questions WHERE question = ? AND answer = ?',
                            (item.get('question', ''), item.get('answer', ''))
                        ).fetchone()
                        
                        if not existing:
                            conn.execute('''
                                INSERT INTO questions (category, question, answer, value, 
                                                     air_date, round, show_number)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                item.get('category', '').upper(),
                                item.get('question', ''),
                                item.get('answer', ''),
                                item.get('value', 0),
                                item.get('air_date', ''),
                                item.get('round', ''),
                                item.get('show_number', 0)
                            ))
                            count += 1
                
                conn.commit()
                logger.info(f"Loaded {count} new questions from {json_file_path}")
                return count
                
        except Exception as e:
            logger.error(f"Error loading questions: {e}")
            raise
    
    def get_questions(self, category: Optional[str] = None, 
                     difficulty: Optional[str] = None,
                     count: int = 10,
                     exclude_recent: Optional[str] = None) -> List[Dict]:
        """Get questions with optional filters."""
        with self.get_connection() as conn:
            query = 'SELECT * FROM questions WHERE 1=1'
            params = []
            
            if category:
                query += ' AND category = ?'
                params.append(category.upper())
            
            if difficulty:
                if difficulty == 'easy':
                    query += ' AND value <= 400'
                elif difficulty == 'medium':
                    query += ' AND value > 400 AND value <= 800'
                elif difficulty == 'hard':
                    query += ' AND value > 800'
            
            # Exclude recently asked questions for this session
            if exclude_recent:
                query += ''' AND id NOT IN (
                    SELECT question_id FROM user_progress 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 20
                )'''
                params.append(exclude_recent)
            
            # Prioritize questions that haven't been asked much
            # Note: PostgreSQL uses RANDOM(), SQLite uses RANDOM()
            query += ' ORDER BY times_asked ASC, RANDOM() LIMIT ?'
            params.append(count)
            
            # Use helper method for cross-database compatibility
            results = self._execute_select(conn, query, tuple(params))
            
            # Format results
            questions = []
            for row in results:
                questions.append({
                    'id': row['id'],
                    'category': row['category'],
                    'question': row['question'],
                    'answer': row['answer'],
                    'value': row['value'],
                    'air_date': row['air_date'],
                    'round': row['round'],
                    'difficulty_rating': row['difficulty_rating'],
                    'times_asked': row['times_asked'],
                    'times_correct': row['times_correct']
                })
            
            return questions
    
    def get_categories(self) -> List[Tuple[str, int]]:
        """Get all categories with question counts."""
        with self.get_connection() as conn:
            query = '''SELECT category, COUNT(*) as count 
                      FROM questions 
                      GROUP BY category 
                      ORDER BY count DESC'''
            results = self._execute_select(conn, query)
            return [(row['category'], row['count']) for row in results]
    
    # User Authentication Management
    
    def create_user(self, username: str, email: str, password_hash: str) -> Optional[int]:
        """Create a new user account."""
        try:
            with self.get_connection() as conn:
                query = '''INSERT INTO users (username, email, password_hash)
                          VALUES (?, ?, ?)'''
                user_id = self._execute_insert(conn, query, (username, email, password_hash))
                conn.commit()
                return user_id
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username."""
        with self.get_connection() as conn:
            query = 'SELECT * FROM users WHERE username = ?'
            results = self._execute_select(conn, query, (username,))
            return results[0] if results else None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        with self.get_connection() as conn:
            query = 'SELECT * FROM users WHERE email = ?'
            results = self._execute_select(conn, query, (email,))
            return results[0] if results else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        with self.get_connection() as conn:
            query = 'SELECT * FROM users WHERE id = ?'
            results = self._execute_select(conn, query, (user_id,))
            return results[0] if results else None
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp."""
        with self.get_connection() as conn:
            query = '''UPDATE users 
                      SET last_login = CURRENT_TIMESTAMP 
                      WHERE id = ?'''
            query = self._format_query(query)
            
            if self.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute(query, (user_id,))
                cursor.close()
            else:
                conn.execute(query, (user_id,))
            
            conn.commit()
    
    def verify_user_password(self, username: str, password_hash: str) -> Optional[Dict]:
        """Verify user credentials and return user data if valid."""
        user = self.get_user_by_username(username)
        if user and user['password_hash'] == password_hash:
            self.update_last_login(user['id'])
            return user
        return None
    
    # User Progress Management
    
    def create_session(self, session_id: str, user_id: int):
        """Create a new user session."""
        with self.get_connection() as conn:
            if self.db_type == 'postgresql':
                query = 'INSERT INTO user_sessions (session_id, user_id) VALUES (%s, %s) ON CONFLICT (session_id) DO NOTHING'
                cursor = conn.cursor()
                cursor.execute(query, (session_id, user_id))
                cursor.close()
            else:
                query = 'INSERT OR IGNORE INTO user_sessions (session_id, user_id) VALUES (?, ?)'
                conn.execute(query, (session_id, user_id))
            
            conn.commit()
    
    def save_answer(self, user_id: int, session_id: str, question_id: int, 
                   user_answer: str, is_correct: bool, 
                   time_taken: Optional[int] = None):
        """Save a user's answer to a question."""
        with self.get_connection() as conn:
            # Save the answer
            query1 = '''INSERT INTO user_progress 
                       (user_id, session_id, question_id, user_answer, is_correct, time_taken_seconds)
                       VALUES (?, ?, ?, ?, ?, ?)'''
            query1 = self._format_query(query1)
            
            # Update question statistics
            if is_correct:
                query2 = '''UPDATE questions 
                           SET times_asked = times_asked + 1,
                               times_correct = times_correct + 1
                           WHERE id = ?'''
            else:
                query2 = '''UPDATE questions 
                           SET times_asked = times_asked + 1
                           WHERE id = ?'''
            query2 = self._format_query(query2)
            
            # Update session last active time
            query3 = '''UPDATE user_sessions 
                       SET last_active = CURRENT_TIMESTAMP 
                       WHERE session_id = ?'''
            query3 = self._format_query(query3)
            
            if self.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute(query1, (user_id, session_id, question_id, user_answer, is_correct, time_taken))
                cursor.execute(query2, (question_id,))
                cursor.execute(query3, (session_id,))
                cursor.close()
            else:
                conn.execute(query1, (user_id, session_id, question_id, user_answer, is_correct, time_taken))
                conn.execute(query2, (question_id,))
                conn.execute(query3, (session_id,))
            
            conn.commit()
    
    # Performance Tracking
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get comprehensive statistics for a session."""
        with self.get_connection() as conn:
            # Overall stats
            query1 = '''SELECT 
                           COUNT(*) as total_questions,
                           SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                           AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END) * 100 as accuracy,
                           AVG(time_taken_seconds) as avg_time
                       FROM user_progress
                       WHERE session_id = ?'''
            overall_results = self._execute_select(conn, query1, (session_id,))
            overall = overall_results[0] if overall_results else {'total_questions': 0, 'correct_answers': 0, 'accuracy': 0, 'avg_time': 0}
            
            # Category breakdown
            query2 = '''SELECT 
                           q.category,
                           COUNT(*) as total,
                           SUM(CASE WHEN up.is_correct THEN 1 ELSE 0 END) as correct,
                           AVG(CASE WHEN up.is_correct THEN 1.0 ELSE 0.0 END) * 100 as accuracy,
                           AVG(up.time_taken_seconds) as avg_time
                       FROM user_progress up
                       JOIN questions q ON up.question_id = q.id
                       WHERE up.session_id = ?
                       GROUP BY q.category
                       ORDER BY accuracy DESC'''
            category_stats = self._execute_select(conn, query2, (session_id,))
            
            # Recent performance (last 20 questions)
            if self.db_type == 'postgresql':
                query3 = '''SELECT 
                               COUNT(*) as total,
                               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct,
                               AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END) * 100 as accuracy
                           FROM (
                               SELECT is_correct
                               FROM user_progress
                               WHERE session_id = %s
                               ORDER BY timestamp DESC
                               LIMIT 20
                           ) as recent_questions'''
            else:
                query3 = '''SELECT 
                               COUNT(*) as total,
                               SUM(is_correct) as correct,
                               AVG(is_correct) * 100 as accuracy
                           FROM (
                               SELECT is_correct
                               FROM user_progress
                               WHERE session_id = ?
                               ORDER BY timestamp DESC
                               LIMIT 20
                           )'''
            recent_results = self._execute_select(conn, query3, (session_id,))
            recent = recent_results[0] if recent_results else {'total': 0, 'correct': 0, 'accuracy': 0}
            
            # Difficulty breakdown
            query4 = '''SELECT 
                           CASE 
                               WHEN q.value <= 400 THEN 'Easy'
                               WHEN q.value <= 800 THEN 'Medium'
                               ELSE 'Hard'
                           END as difficulty,
                           COUNT(*) as total,
                           SUM(CASE WHEN up.is_correct THEN 1 ELSE 0 END) as correct,
                           AVG(CASE WHEN up.is_correct THEN 1.0 ELSE 0.0 END) * 100 as accuracy
                       FROM user_progress up
                       JOIN questions q ON up.question_id = q.id
                       WHERE up.session_id = ?
                       GROUP BY difficulty'''
            difficulty_stats = self._execute_select(conn, query4, (session_id,))
            
            return {
                'overall': {
                    'total_questions': overall['total_questions'] or 0,
                    'correct_answers': overall['correct_answers'] or 0,
                    'accuracy': round(overall['accuracy'] or 0, 1),
                    'avg_time': round(overall['avg_time'] or 0, 1)
                },
                'by_category': [
                    {
                        'category': row['category'],
                        'total': row['total'],
                        'correct': row['correct'] or 0,
                        'accuracy': round(row['accuracy'] or 0, 1),
                        'avg_time': round(row['avg_time'] or 0, 1)
                    } for row in category_stats
                ],
                'recent_performance': {
                    'total': recent['total'] or 0,
                    'correct': recent['correct'] or 0,
                    'accuracy': round(recent['accuracy'] or 0, 1)
                },
                'by_difficulty': [
                    {
                        'difficulty': row['difficulty'],
                        'total': row['total'],
                        'correct': row['correct'] or 0,
                        'accuracy': round(row['accuracy'] or 0, 1)
                    } for row in difficulty_stats
                ]
            }
    
    def get_progress_over_time(self, session_id: str, days: int = 30) -> List[Dict]:
        """Get daily progress for the last N days."""
        with self.get_connection() as conn:
            if self.db_type == 'postgresql':
                query = '''SELECT 
                              DATE(timestamp) as date,
                              COUNT(*) as questions_answered,
                              SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                              AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END) * 100 as accuracy
                          FROM user_progress
                          WHERE session_id = %s 
                              AND timestamp >= CURRENT_DATE - INTERVAL '%s days'
                          GROUP BY DATE(timestamp)
                          ORDER BY date ASC'''
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(query, (session_id, days))
                results = cursor.fetchall()
                cursor.close()
            else:
                query = '''SELECT 
                              DATE(timestamp) as date,
                              COUNT(*) as questions_answered,
                              SUM(is_correct) as correct_answers,
                              AVG(is_correct) * 100 as accuracy
                          FROM user_progress
                          WHERE session_id = ? 
                              AND timestamp >= DATE('now', '-' || ? || ' days')
                          GROUP BY DATE(timestamp)
                          ORDER BY date ASC'''
                cursor = conn.execute(query, (session_id, days))
                results = [dict(row) for row in cursor.fetchall()]
            
            return [
                {
                    'date': str(row['date']),
                    'questions_answered': row['questions_answered'],
                    'correct_answers': row['correct_answers'] or 0,
                    'accuracy': round(row['accuracy'] or 0, 1)
                } for row in results
            ]
    
    def save_performance_snapshot(self, session_id: str):
        """Save a daily performance snapshot for tracking long-term progress."""
        stats = self.get_session_stats(session_id)
        
        with self.get_connection() as conn:
            # Get categories played today
            if self.db_type == 'postgresql':
                query1 = '''SELECT DISTINCT q.category
                           FROM user_progress up
                           JOIN questions q ON up.question_id = q.id
                           WHERE up.session_id = %s AND DATE(up.timestamp) = CURRENT_DATE'''
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(query1, (session_id,))
                categories = cursor.fetchall()
                cursor.close()
                
                categories_str = ','.join([row['category'] for row in categories])
                
                # Get user_id for this session
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM user_sessions WHERE session_id = %s', (session_id,))
                user_result = cursor.fetchone()
                user_id = user_result[0] if user_result else None
                cursor.close()
                
                if user_id:
                    # Use INSERT ... ON CONFLICT for PostgreSQL
                    query2 = '''INSERT INTO performance_snapshots
                               (user_id, session_id, snapshot_date, total_questions, correct_answers, 
                                accuracy, avg_time_seconds, categories_played)
                               VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, %s, %s)
                               ON CONFLICT (user_id, session_id, snapshot_date) 
                               DO UPDATE SET
                                   total_questions = EXCLUDED.total_questions,
                                   correct_answers = EXCLUDED.correct_answers,
                                   accuracy = EXCLUDED.accuracy,
                                   avg_time_seconds = EXCLUDED.avg_time_seconds,
                                   categories_played = EXCLUDED.categories_played'''
                    cursor = conn.cursor()
                    cursor.execute(query2, (
                        user_id,
                        session_id,
                        stats['overall']['total_questions'],
                        stats['overall']['correct_answers'],
                        stats['overall']['accuracy'],
                        stats['overall']['avg_time'],
                        categories_str
                    ))
                    cursor.close()
            else:
                query1 = '''SELECT DISTINCT q.category
                           FROM user_progress up
                           JOIN questions q ON up.question_id = q.id
                           WHERE up.session_id = ? AND DATE(up.timestamp) = DATE('now')'''
                categories = conn.execute(query1, (session_id,)).fetchall()
                
                categories_str = ','.join([row['category'] for row in categories])
                
                # Get user_id for this session
                user_result = conn.execute('SELECT user_id FROM user_sessions WHERE session_id = ?', (session_id,)).fetchone()
                user_id = user_result['user_id'] if user_result else None
                
                if user_id:
                    query2 = '''INSERT OR REPLACE INTO performance_snapshots
                               (user_id, session_id, snapshot_date, total_questions, correct_answers, 
                                accuracy, avg_time_seconds, categories_played)
                               VALUES (?, ?, DATE('now'), ?, ?, ?, ?, ?)'''
                    conn.execute(query2, (
                        user_id,
                        session_id,
                        stats['overall']['total_questions'],
                        stats['overall']['correct_answers'],
                        stats['overall']['accuracy'],
                        stats['overall']['avg_time'],
                        categories_str
                    ))
            
            conn.commit()
    
    def get_hardest_questions(self, limit: int = 10) -> List[Dict]:
        """Get questions with the lowest success rate."""
        with self.get_connection() as conn:
            query = '''SELECT *, 
                          CASE WHEN times_asked > 0 
                              THEN CAST(times_correct AS FLOAT) / times_asked * 100 
                              ELSE NULL 
                          END as success_rate
                      FROM questions
                      WHERE times_asked >= 5
                      ORDER BY success_rate ASC
                      LIMIT ?'''
            results = self._execute_select(conn, query, (limit,))
            
            return [
                {
                    'id': row['id'],
                    'category': row['category'],
                    'question': row['question'],
                    'answer': row['answer'],
                    'value': row['value'],
                    'times_asked': row['times_asked'],
                    'times_correct': row['times_correct'],
                    'success_rate': round(row['success_rate'] or 0, 1) if row.get('success_rate') is not None else 0
                } for row in results
            ]
    
    def cleanup_old_sessions(self, days_inactive: int = 30):
        """Remove sessions that have been inactive for too long."""
        with self.get_connection() as conn:
            # Get sessions to delete
            if self.db_type == 'postgresql':
                query1 = '''SELECT session_id FROM user_sessions
                           WHERE last_active < CURRENT_TIMESTAMP - INTERVAL '%s days' '''
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(query1, (days_inactive,))
                old_sessions = cursor.fetchall()
                cursor.close()
                
                cursor = conn.cursor()
                for row in old_sessions:
                    session_id = row['session_id']
                    # Delete progress and snapshots
                    cursor.execute('DELETE FROM user_progress WHERE session_id = %s', (session_id,))
                    cursor.execute('DELETE FROM performance_snapshots WHERE session_id = %s', (session_id,))
                
                # Delete the sessions
                cursor.execute('''DELETE FROM user_sessions
                                 WHERE last_active < CURRENT_TIMESTAMP - INTERVAL '%s days' ''', (days_inactive,))
                cursor.close()
            else:
                query1 = '''SELECT session_id FROM user_sessions
                           WHERE last_active < DATE('now', '-' || ? || ' days')'''
                old_sessions = conn.execute(query1, (days_inactive,)).fetchall()
                
                for row in old_sessions:
                    session_id = row['session_id']
                    # Delete progress and snapshots
                    conn.execute('DELETE FROM user_progress WHERE session_id = ?', (session_id,))
                    conn.execute('DELETE FROM performance_snapshots WHERE session_id = ?', (session_id,))
                
                # Delete the sessions
                conn.execute('''DELETE FROM user_sessions
                               WHERE last_active < DATE('now', '-' || ? || ' days')''', (days_inactive,))
            
            conn.commit()
            logger.info(f"Cleaned up {len(old_sessions)} inactive sessions")