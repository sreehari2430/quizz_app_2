from flask import Flask
from flask_cors import CORS
import os
from google import genai
import logging

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)

    # Load config
    from .config import FLASK_SECRET_KEY
    app.secret_key = FLASK_SECRET_KEY

    # Initialize DB
    from .models import init_db
    init_db()

    # Register routes
    from .routes import register_routes
    register_routes(app)

    # Session config
    from datetime import timedelta
    app.permanent_session_lifetime = timedelta(hours=2)

    return app
