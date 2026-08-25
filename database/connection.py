import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(
    os.environ.get("FAT_BENDER_DB", Path(__file__).resolve().parent.parent / "fat_bender.db")
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    age INTEGER,
    gender TEXT,
    height_cm REAL,
    current_weight_kg REAL,
    target_weight_kg REAL,
    activity_description TEXT,
    goal_mode TEXT CHECK (goal_mode IN ('cut', 'bulk')),
    tdee_baseline REAL,
    target_calories REAL,
    protein_target_g REAL,
    carbs_target_g REAL,
    fat_target_g REAL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

CREATE TABLE IF NOT EXISTS meal_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    meal_name TEXT NOT NULL,
    items_json TEXT NOT NULL DEFAULT '[]',
    total_calories REAL NOT NULL DEFAULT 0,
    protein_g REAL NOT NULL DEFAULT 0,
    carbs_g REAL NOT NULL DEFAULT 0,
    fat_g REAL NOT NULL DEFAULT 0,
    logged_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_meal_logs_date ON meal_logs (date);

CREATE TABLE IF NOT EXISTS weight_logs (
    date TEXT PRIMARY KEY,
    weight_kg REAL NOT NULL,
    rolling_avg_7d REAL,
    logged_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);
"""

_initialized = False


@contextmanager
def get_connection():
    global _initialized
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if not _initialized:
            conn.executescript(SCHEMA_SQL)
            _initialized = True
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    with get_connection():
        pass
