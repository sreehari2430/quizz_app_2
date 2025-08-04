from pydantic import BaseModel, Field
import sqlite3
from .config import DB_PATH

class Question(BaseModel):
    answer: str
    prompt: str
    question_type: str
    hint: str
    explanation: str
    choices: list[str] = Field(default_factory=list)
    difficulty_level: str  # 'easy', 'medium', 'hard'
    category: str

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_category_stats (
            user_id INTEGER,
            category TEXT,
            correct INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            last_study_plan TEXT,
            PRIMARY KEY (user_id, category),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer TEXT,
            prompt TEXT,
            question_type TEXT,
            hint TEXT,
            explanation TEXT,
            choices TEXT,
            difficulty_level TEXT,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()
