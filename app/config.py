import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecret")
DB_PATH = os.path.join(PROJECT_ROOT, os.getenv("DB_PATH"))
PDF_PATH = os.path.join(PROJECT_ROOT, os.getenv("PDF_PATH"))
MODEL_NAME = os.getenv("MODEL_NAME")
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
NUM_QUESTIONS_PER_QUIZ = int(os.getenv("NUM_QUESTIONS_PER_QUIZ"))