"""
Database layer for Jayopardy.

Backed by Postgres (Replit's managed PostgreSQL) so the app can run on
Autoscale deployments where the local filesystem isn't durable. The
public API mirrors what the rest of the app expects from a sqlite3-style
connection:

  - get_db_connection() returns a connection with a cursor() method
  - cursor.execute(sql, params) accepts '?' placeholders (translated to
    '%s') and 'INSERT OR IGNORE' (translated to ON CONFLICT DO NOTHING)
  - cursor.fetchone() / fetchall() return rows that support both index
    access (row[0]) and key access (row['col']), and dict(row) works
  - cursor.lastrowid is populated for INSERTs
  - cursor.rowcount is populated for UPDATE/DELETE
"""
import os
import re
import psycopg2
import psycopg2.extras


DATABASE_URL = os.environ.get("DATABASE_URL")

# Cache of which tables have an 'id' column. Populated lazily on first INSERT
# to a given table so we only auto-append 'RETURNING id' when the table
# supports it — avoiding exception-driven control flow on hot paths.
_table_has_id_cache: dict[str, bool] = {}
_TABLE_NAME_RE = re.compile(
    r"^\s*INSERT\s+(?:OR\s+IGNORE\s+)?INTO\s+([\"\w\.]+)", re.IGNORECASE
)


class _Row(dict):
    """Row that supports both row[0] and row['col'] access, and dict(row)."""

    def __init__(self, mapping, columns):
        super().__init__(mapping)
        self._columns = columns

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(self._columns[key])
        return super().__getitem__(key)


class _Cursor:
    """Thin wrapper around a psycopg2 cursor that emulates sqlite3 semantics."""

    _INSERT_RE = re.compile(r"^\s*INSERT\s+(OR\s+IGNORE\s+)?INTO\s", re.IGNORECASE)
    _HAS_RETURNING_RE = re.compile(r"\bRETURNING\b", re.IGNORECASE)
    _INSERT_OR_IGNORE_RE = re.compile(r"^(\s*)INSERT\s+OR\s+IGNORE\s+INTO\s", re.IGNORECASE)

    def __init__(self, conn):
        self._conn = conn
        self._cur = conn._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.lastrowid = None
        self.rowcount = 0

    def _table_has_id_column(self, table: str) -> bool:
        """Return True if `table` has an 'id' column. Cached per process."""
        key = table.strip().strip('"').lower()
        cached = _table_has_id_cache.get(key)
        if cached is not None:
            return cached
        try:
            self._cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = 'id' LIMIT 1",
                (key.split(".")[-1],),
            )
            has_id = self._cur.fetchone() is not None
        except Exception:
            has_id = False
        _table_has_id_cache[key] = has_id
        return has_id

    @staticmethod
    def _translate(sql: str) -> tuple[str, bool]:
        """Translate sqlite-flavored SQL into psycopg2-compatible SQL.

        Returns (translated_sql, is_insert_needing_returning).
        """
        translated = sql

        # INSERT OR IGNORE -> append ON CONFLICT DO NOTHING and strip OR IGNORE.
        is_or_ignore = bool(_Cursor._INSERT_OR_IGNORE_RE.match(translated))
        if is_or_ignore:
            translated = _Cursor._INSERT_OR_IGNORE_RE.sub(r"\1INSERT INTO ", translated)
            if "ON CONFLICT" not in translated.upper():
                translated = translated.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

        # '?' placeholders -> '%s'. SQL strings in this codebase don't contain
        # literal '?' characters so a simple replace is safe.
        translated = translated.replace("?", "%s")

        # For INSERTs without a RETURNING clause, append RETURNING id so we
        # can populate cursor.lastrowid the way sqlite3 does.
        needs_returning = False
        if _Cursor._INSERT_RE.match(sql) and not _Cursor._HAS_RETURNING_RE.search(translated):
            translated = translated.rstrip().rstrip(";") + " RETURNING id"
            needs_returning = True

        return translated, needs_returning

    def execute(self, sql: str, params=None):
        translated, needs_returning = self._translate(sql)
        self.lastrowid = None
        # Suppress RETURNING id for tables that don't have an id column
        # (e.g. user_stats, premium_status). This avoids the savepoint /
        # exception path on every insert to those tables.
        if needs_returning:
            m = _TABLE_NAME_RE.match(sql)
            if m and not self._table_has_id_column(m.group(1)):
                translated = translated[: -len(" RETURNING id")]
                needs_returning = False
        if needs_returning:
            # Use a savepoint so a failure (e.g. INSERT into a table without an
            # 'id' column) can be recovered without rolling back the whole
            # surrounding transaction. Read RETURNING id BEFORE releasing the
            # savepoint — issuing another statement clears the cursor result.
            try:
                self._cur.execute("SAVEPOINT _shim_returning")
                self._cur.execute(translated, params or ())
                try:
                    row = self._cur.fetchone()
                    if row:
                        self.lastrowid = row.get("id") if isinstance(row, dict) else row[0]
                except psycopg2.ProgrammingError:
                    pass
                rowcount = self._cur.rowcount
                self._cur.execute("RELEASE SAVEPOINT _shim_returning")
                self.rowcount = rowcount
                return self
            except psycopg2.errors.UndefinedColumn:
                self._cur.execute("ROLLBACK TO SAVEPOINT _shim_returning")
                self._cur.execute("RELEASE SAVEPOINT _shim_returning")
                translated = translated[: -len(" RETURNING id")]

        self._cur.execute(translated, params or ())
        self.rowcount = self._cur.rowcount
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._cur.description]
        return _Row(row, cols)

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._cur.description]
        return [_Row(r, cols) for r in rows]

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass


class _Connection:
    """sqlite3-style connection wrapper around a psycopg2 connection."""

    def __init__(self, raw):
        self._raw = raw

    def cursor(self):
        return _Cursor(self)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        try:
            self._raw.close()
        except Exception:
            pass


def get_db_connection() -> _Connection:
    """Open a new Postgres connection wrapped in the sqlite3-compatible shim."""
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Provision a Postgres database for this project."
        )
    raw = psycopg2.connect(DATABASE_URL)
    return _Connection(raw)


def initialize_database():
    """Create tables if they don't exist. Idempotent."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur._cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )
    cur._cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            games_played INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0
        )
        """
    )
    cur._cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bookmarks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            category TEXT NOT NULL,
            clue TEXT NOT NULL,
            correct_response TEXT NOT NULL,
            bookmarked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, category, clue, correct_response)
        )
        """
    )
    cur._cur.execute(
        """
        CREATE TABLE IF NOT EXISTS premium_status (
            user_email TEXT PRIMARY KEY,
            is_premium INTEGER DEFAULT 0,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            plan_interval TEXT,
            subscription_end BIGINT,
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur._cur.execute(
        """
        CREATE TABLE IF NOT EXISTS challenges (
            id SERIAL PRIMARY KEY,
            challenger_id INTEGER NOT NULL REFERENCES users(id),
            opponent_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'pending',
            num_questions INTEGER DEFAULT 10,
            categories TEXT,
            challenger_score INTEGER DEFAULT 0,
            opponent_score INTEGER DEFAULT 0,
            challenger_completed INTEGER DEFAULT 0,
            opponent_completed INTEGER DEFAULT 0,
            winner_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
