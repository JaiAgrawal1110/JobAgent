# ============================================================
# JobAgent AI — Config
# Keys are loaded from .env — never hardcode them here
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

# --- Your Profile ---
PROFILE = {
    "roles": ["ML Engineer", "AI Engineer", "Python Developer", "Backend Developer", "Full Stack Developer"],
    "experience_years": 2,
    "job_type": "Internship",
    "locations": ["Bangalore", "Jaipur", "Remote"],
    "skills": [
        "Python", "Machine Learning", "Deep Learning", "FastAPI", "Django",
        "PostgreSQL", "SQLite", "REST APIs", "Claude API", "LLMs",
        "TensorFlow", "PyTorch", "scikit-learn", "Docker", "Git"
    ],
}

# --- Job Search Keywords ---
SEARCH_KEYWORDS = [
    "ML engineer intern",
    "AI engineer intern",
    "Python developer intern",
    "backend developer intern",
    "machine learning intern",
]

LOCATIONS = ["Bangalore", "Jaipur", "Remote India"]

# --- Scoring ---
SCORE_THRESHOLD = 7
TOP_JOBS_PER_DAY = 5

# --- Scheduler ---
DAILY_RUN_TIME = "07:00"

# --- Email ---
EMAIL_SENDER   = os.getenv("EMAIL_SENDER", "your_email@gmail.com")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "your_email@gmail.com")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")

# --- API ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Paths ---
DB_PATH        = "data/jobagent.db"
LOG_PATH       = "logs/jobagent.log"
RESUME_PATH    = "resume/base_resume.json"
PDF_OUTPUT_DIR = "data/pdfs/"