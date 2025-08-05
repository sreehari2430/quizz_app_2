from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from .quiz import get_user_id, is_quiz_in_progress, evaluate_answer_from_db, get_random_unseen_question
import sqlite3
from .config import DB_PATH, NUM_QUESTIONS_PER_QUIZ
from .llm import get_llm_weights, generate_study_plan
from .db import get_user_stats, get_latest_study_plan, batch_update_user_stats, save_study_plan
from collections import defaultdict
from .logger import logger

def register_routes(app):
      # Add session timeout and cleanup
      @app.before_request
      def make_session_permanent():
            session.permanent = True
      
      @app.route("/")
      def home():
            if get_user_id():
                  return redirect(url_for("start"))  # Changed to redirect to start instead of profile
            return render_template("login.html")

      @app.route("/login", methods=["GET", "POST"])
      def login():
            if request.method == "POST":
                  username = request.form.get("username")
                  password = request.form.get("password")

                  conn = sqlite3.connect(DB_PATH)
                  cur = conn.cursor()
                  cur.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
                  user = cur.fetchone()
                  conn.close()

                  if user and check_password_hash(user[1], password):
                        session["user_id"] = user[0]
                        session["username"] = username  # Store username in session for easy access
                        return redirect(url_for("start"))
                  else:
                        flash("Invalid credentials", "error")  # Changed to redirect to start instead of profile
                        return redirect(url_for("login"))
            return render_template("login.html")

      @app.route("/register", methods=["GET", "POST"])
      def register():
            if request.method == "POST":
                  username = request.form.get("username")
                  password = request.form.get("password")
                  if not username or not password:
                        return "Missing credentials", 400

                  conn = sqlite3.connect(DB_PATH)
                  cur = conn.cursor()
                  try:
                        password_hash = generate_password_hash(password)
                        cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
                        conn.commit()
                        return redirect(url_for("login"))
                  except sqlite3.IntegrityError:
                        return "Username already exists", 400
                  finally:
                        conn.close()
            return render_template("register.html")
       
      @app.route("/start", methods=["GET", "POST"])
      def start():
            print("Enter start")
            logger.info("Enter start")
            user_id = get_user_id()
            if not user_id:
                  return redirect(url_for("login"))

            if is_quiz_in_progress():
                  return redirect(url_for("question"))
            
            logger.info("calling get_llm_weights")
            session["weights"] = get_llm_weights(get_user_id())
            
            logger.info("got response from get_llm_weights")

            session["difficulty"] = "Progressive"
            session["index"] = 0
            session["score"] = 0
            session["used_ids"] = []
            session["history"] = []
            session["answer_track"] = []
            session["answer_history"] = []  # Add this missing variable
            session["level_index"] = 0
            
            logger.info("Exit start")
            
            return redirect(url_for("question"))

      @app.route("/question")
      def question():
            logger.info("Enter question")
            if not get_user_id():
                  return redirect(url_for("login"))

            session["last_feedback"] = None
            try:
                  logger.info("get_random_unseen_question")                  
                  q = get_random_unseen_question()
                  logger.info("Question fetched:", q)
            except Exception as e:
                  logger.error("Error fetching question:", e)
                  return "Error occurred while loading question", 500

            session["current_question"] = q
            current_index = session.get("index", 0)
            return render_template("question.html", question=q, score=session.get("score", 0), current_index=current_index)

      @app.route("/question_deviate")
      def question_deviate():
            if not get_user_id():
                  return redirect(url_for("login"))
            
            if is_quiz_in_progress():
                  q = session["current_question"]
                  current_index = session.get("index", 0)
                  return render_template("question.html", question=q, score=session.get("score", 0), current_index=current_index)
            else:
                  # Handle the case when no quiz is in progress
                  return redirect(url_for("start"))

      @app.route("/answer", methods=["POST"])
      def answer():
            if not get_user_id():
                  return redirect(url_for("login"))

            user_answer = request.form.get("user_answer")
            q = session.get("current_question")
            result = evaluate_answer_from_db(q["prompt"], q["answer"], user_answer, q["explanation"])
            is_correct = result["correct"]
            session["answer_track"].append(is_correct)
            if is_correct:
                  session["score"] += 1
            # Keep recent 10
            if len(session['answer_history']) > 10:
                  session['answer_history'] = session['answer_history'][-10:]
            session["history"].append({
                  "question": q["prompt"],
                  "user_answer": user_answer,
                  "correct_answer": q["answer"],
                  "explanation": q["explanation"],
                  "correct": is_correct,
                  "category": q.get("category", "general"),
                  "difficulty_level": q.get("difficulty_level", "medium")
            })

            session["last_feedback"] = {
                  "user_answer": user_answer,
                  "correct_answer": q["answer"],
                  "correct": is_correct,
                  "explanation": q["explanation"]
            }
            session["index"] += 1

            if session["index"] >= NUM_QUESTIONS_PER_QUIZ:
                  return redirect(url_for("result"))
            return redirect(url_for("feedback"))

      @app.route("/logout")
      def logout():
            user_id = get_user_id()
            if user_id:
                  history = session.get("history", [])
            session.clear()
            return redirect(url_for("home"))

      @app.route("/profile")  # Unchanged, but stats now reflect batched updates
      def profile():
            if not get_user_id():
                  return redirect(url_for("login"))
            user_id = get_user_id()
            stats = get_user_stats(user_id)
            in_progress = is_quiz_in_progress()
            latest_plan = get_latest_study_plan(user_id) or "<ul><li>No study plan available yet. Complete a quiz to generate one.</li></ul>"
            return render_template(
                  "profile.html",
                  stats=stats,
                  username=session.get("username", "User"),
                  in_progress=in_progress,
                  latest_plan=latest_plan
            )

      @app.route("/set_difficulty", methods=["POST"])
      def set_difficulty():
            data = request.get_json()
            difficulty = data.get("difficulty")

            # Store in session or use directly
            session["difficulty"] = difficulty
            print(f"Difficulty updated to: {difficulty}")

            return jsonify({"status": "success", "difficulty": difficulty})

      @app.route("/feedback")
      def feedback():
            if not get_user_id():
                  return redirect(url_for("login"))

            q = session.get("current_question")
            result = session.get("last_feedback")
            return render_template("feedback.html", question=q, feedback=result, score=session["score"])

      @app.route("/result")
      def result():
            if not get_user_id():
                  return redirect(url_for("login"))

            history = session.get("history", [])
            user_id = get_user_id()

            if history:
                  # Batch update stats from session history
                  batch_update_user_stats(user_id, history)

            category_stats = defaultdict(lambda: {"correct": 0, "incorrect": 0})
            difficulty_stats = defaultdict(lambda: {"correct": 0, "incorrect": 0})

            for item in history:
                  cat = item.get("category", "general")
                  diff = item.get("difficulty_level", "medium")
                  correct = item.get("correct", False)
                  category_stats[cat]["correct" if correct else "incorrect"] += 1
                  difficulty_stats[diff]["correct" if correct else "incorrect"] += 1

            try:
                  score_percent = (session["score"] / len(history)) * 100
            except ZeroDivisionError:
                  score_percent = 0

            study_plan = generate_study_plan(category_stats, difficulty_stats, score_percent, len(history))
            save_study_plan(user_id, study_plan)

            return render_template(
                  "result.html",
                  score=session.get("score", 0),
                  history=history,
                  category_labels=list(category_stats.keys()),
                  category_correct=[category_stats[k]["correct"] for k in category_stats],
                  category_incorrect=[category_stats[k]["incorrect"] for k in category_stats],
                  difficulty_labels=list(difficulty_stats.keys()),
                  difficulty_correct=[difficulty_stats[k]["correct"] for k in difficulty_stats],
                  difficulty_incorrect=[difficulty_stats[k]["incorrect"] for k in difficulty_stats],
                  score_percent=score_percent,
                  study_plan=study_plan
            )
            
      @app.route("/ADD_NEW_QA")
      def ADD_NEW_QA():
            pass