import sqlite3
from collections import defaultdict
from .config import DB_PATH, NUM_QUESTIONS_PER_QUIZ

import json
def get_all_categories():
    query = "SELECT DISTINCT(category) from questions"
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(query)
        return [row[0] for row in cur.fetchall()]
    
def get_llm_input(user_id=1):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
                    SELECT category, correct, total, last_study_plan 
                    FROM user_category_stats 
                    WHERE user_id = ?
                    ''', (user_id,))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            print("No category data available for user_id:", user_id)
            return {"stats": [], "last_study_plan": ""}

        last_study_plan = rows[0][3] or ""  # Handle possible None
        stats = []

        for cat, correct, total, _ in rows:
            stats.append({
                "category": cat,
                "correct": correct,
                "total": total
            })
        existing_categories = [i["category"] for i in stats]
        all_categories = get_all_categories()
        
        for cat in all_categories:
            if cat not in existing_categories:
                stats.append({
                "category": cat,
                "correct": 0,
                "total": 0
            })
                
        return {
            "stats": stats,
            "last_study_plan": last_study_plan
        }
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return {"stats": [], "last_study_plan": ""}
  

  
  
def get_latest_study_plan(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT last_study_plan FROM user_category_stats WHERE user_id = ? LIMIT 1", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def save_questions(questions):
    if not questions:
        print("No questions to store.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    values = []
    for qa in questions:
        values.append((
            qa['answer'],
            qa['prompt'],
            qa['question_type'],
            qa['hint'],
            qa['explanation'],
            json.dumps(qa.get('choices', [])),
            qa.get('difficulty_level', 'medium'),
            qa.get('category', 'general')
        ))

    cur.executemany('''
        INSERT INTO questions (
            answer, prompt, question_type, hint, explanation, choices,
            difficulty_level, category
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', values)
    conn.commit()
    conn.close()
    
def update_user_stats(user_id, category, correct):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO user_category_stats (user_id, category, correct, total)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id, category) DO UPDATE SET
            correct = correct + ?,
            total = total + 1
    ''', (user_id, category, 1 if correct else 0, 1 if correct else 0))
    conn.commit()
    conn.close()

def save_study_plan(user_id, plan):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE user_category_stats SET last_study_plan = ? WHERE user_id = ?", (plan, user_id))
    conn.commit()
    conn.close()
    
def get_username(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else "User"

def batch_update_user_stats(user_id, history):
    """Batch update stats from session history."""
    if not history:
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Aggregate counts from history
    category_counts = defaultdict(lambda: {"correct": 0, "total": 0})
    for item in history:
        cat = item.get("category", "general")
        correct = 1 if item.get("correct", False) else 0
        category_counts[cat]["correct"] += correct
        category_counts[cat]["total"] += 1

    # Update DB for each category
    for cat, counts in category_counts.items():
        cur.execute('''
            INSERT INTO user_category_stats (user_id, category, correct, total)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, category) DO UPDATE SET
                correct = correct + ?,
                total = total + ?
        ''', (user_id, cat, counts["correct"], counts["total"], counts["correct"], counts["total"]))

    conn.commit()
    conn.close()
    
def get_user_stats(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT category, correct, total FROM user_category_stats WHERE user_id = ?", (user_id,))
    stats = {row[0]: {"correct": row[1], "total": row[2], "accuracy": (row[1] / row[2] * 100) if row[2] > 0 else 0} for row in cur.fetchall()}
    overall_correct = sum(s["correct"] for s in stats.values())
    overall_total = sum(s["total"] for s in stats.values())
    overall_accuracy = (overall_correct / overall_total * 100) if overall_total > 0 else 0
    conn.close()
    return {"categories": stats, "overall_accuracy": overall_accuracy, "total_quizzes": overall_total // NUM_QUESTIONS_PER_QUIZ}
