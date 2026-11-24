"""
CampusFind - Database Helper & Schema Definition
Handles SQLite database connection, initialization, and query execution.
"""

import sqlite3
import os
from flask import g, current_app

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'campusfind.db')

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- Users Table
CREATE TABLE IF NOT EXISTS User (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user', -- 'user' or 'admin'
    active INTEGER NOT NULL DEFAULT 1, -- 1 for active, 0 for deactivated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Items Table (Lost & Found posts)
CREATE TABLE IF NOT EXISTS Item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('lost', 'found')),
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('ID card', 'electronics', 'books', 'bottle', 'keys', 'clothing', 'other')),
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    date TEXT NOT NULL, -- Format: YYYY-MM-DD
    photo_path TEXT,
    status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'Matched', 'Claimed', 'Returned')),
    verification_question TEXT,
    verification_answer_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
);

-- Matches Table (Auto-matched pairs with score >= 60)
CREATE TABLE IF NOT EXISTS Match (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lost_item_id INTEGER NOT NULL,
    found_item_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(lost_item_id, found_item_id),
    FOREIGN KEY (lost_item_id) REFERENCES Item(id) ON DELETE CASCADE,
    FOREIGN KEY (found_item_id) REFERENCES Item(id) ON DELETE CASCADE
);

-- Claims Table (Verification attempts for found items)
CREATE TABLE IF NOT EXISTS Claim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    claimant_id INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    result TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES Item(id) ON DELETE CASCADE,
    FOREIGN KEY (claimant_id) REFERENCES User(id) ON DELETE CASCADE
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS Notification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
);

-- Indexes for lightning fast searching and filtering (< 2s requirement)
CREATE INDEX IF NOT EXISTS idx_item_type_status ON Item(type, status);
CREATE INDEX IF NOT EXISTS idx_item_category ON Item(category);
CREATE INDEX IF NOT EXISTS idx_item_date ON Item(date);
CREATE INDEX IF NOT EXISTS idx_match_lost ON Match(lost_item_id);
CREATE INDEX IF NOT EXISTS idx_match_found ON Match(found_item_id);
CREATE INDEX IF NOT EXISTS idx_notification_user ON Notification(user_id, is_read);
"""


def get_db_path():
    """Return database path from Flask config or default."""
    try:
        if current_app and current_app.config.get('DATABASE'):
            return current_app.config['DATABASE']
    except RuntimeError:
        pass
    return DEFAULT_DB_PATH


def get_db(db_path=None):
    """
    Get a database connection. If running within a Flask request context,
    reuse the connection stored on the 'g' object.
    """
    path = db_path or get_db_path()
    try:
        if 'db' not in g or g.get('db_path') != path:
            conn = sqlite3.connect(path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            g.db = conn
            g.db_path = path
        return g.db
    except RuntimeError:
        # Outside Flask context (e.g. standalone test or seed script)
        conn = sqlite3.connect(path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn


def close_db(e=None):
    """Close the database connection on app context teardown."""
    try:
        db = g.pop('db', None)
        if db is not None:
            db.close()
    except RuntimeError:
        pass


def init_db(db_path=None):
    """Initialize database tables and indexes."""
    conn = get_db(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def query_db(query, args=(), one=False, db=None):
    """Execute a read query and return list of rows or a single row."""
    conn = db or get_db()
    cur = conn.execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, args=(), commit=True, db=None):
    """Execute an INSERT, UPDATE, or DELETE query and return lastrowid."""
    conn = db or get_db()
    cur = conn.execute(query, args)
    if commit:
        conn.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
