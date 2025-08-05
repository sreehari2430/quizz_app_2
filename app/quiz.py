import random
import json
import fitz 
import sqlite3
from flask import session
from .config import DB_PATH, PDF_PATH
from .llm import generate_questions, generate_questions_for
from .db import save_questions

# --- Helpers ---


def parse_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def get_user_id():
    return session.get("user_id")

def adjust_difficulty_pro():
      if len(session["answer_track"]) < 6:
            return "easy"
      levels = ['easy', 'medium', 'hard']
      idx = session["level_index"]
      last_three = session["answer_track"][-3:]
      
      if all(last_three) and idx < len(levels) - 1:
            idx += 1
            
      elif not any(last_three) and idx > 0:
            idx -= 1
                  
      session["level_index"] = idx
      return levels[idx]

def choose_next_category(weights_dict):
    print("choose_next_category")
    """Choose next category using weighted random selection."""
    if not weights_dict:
        print("not weights_dict")  
        return None

    categories = list(weights_dict.keys())
    weights = list(weights_dict.values())
    return random.choices(categories, weights=weights, k=1)[0]

# Helper to check if a quiz is in progress
def is_quiz_in_progress():
    return session.get("index", 0) > 0

def evaluate_answer_from_db(prompt, correct_answer, user_answer, explanation):
    is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
    return {
        "correct": is_correct,
        "explanation": explanation
    }
def get_qn_from_db(difficulty, category):
      query = "SELECT * FROM questions WHERE difficulty_level = ?"
      params = [difficulty]
      if category is not None:
            query += " AND category = ?"
            params.append(category)
            print(f"Querying for category: {category} with difficulty: {difficulty}")    
      used_ids = session.get("used_ids", [])
      if used_ids:
            placeholder = ",".join(["?"] * len(used_ids))
            query += f" AND id NOT IN ({placeholder})"
            params.extend(used_ids)

      query += " ORDER BY RANDOM() LIMIT 1"
      with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()

def update_used_ids(question_id):
      if "used_ids" not in session:
            session["used_ids"] = []
      if question_id not in session["used_ids"]:
            session["used_ids"].append(question_id)

def build_question_dict(row): 
      update_used_ids(row[0])            
      return {
            "id": row[0],
            "answer": row[1],
            "prompt": row[2],
            "question_type": row[3],
            "hint": row[4],
            "explanation": row[5],
            "choices": json.loads(row[6]) if row[6] else [],
            "difficulty_level": row[7],
            "category": row[8]
            }
          
def get_random_unseen_question():
      MAX_RETRIES = 1
      user_id = get_user_id()
      if not user_id:
            raise Exception("User not logged in")  
      difficulty = session.get("difficulty")
      if difficulty == "Progressive":
            difficulty = adjust_difficulty_pro()
      category = choose_next_category(session["weights"])
      for retry in range(MAX_RETRIES + 1):                            
            row = get_qn_from_db(difficulty, category)          
            if row:
                  return build_question_dict(row)
            print("❌ No unique questions found. Generating more...")
            text = parse_pdf(PDF_PATH)
            questions = generate_questions_for(text, difficulty, category)
            save_questions(questions)
      category = None
      row = get_qn_from_db(difficulty, category)
      return build_question_dict(row)
      
  
  