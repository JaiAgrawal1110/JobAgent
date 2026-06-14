# ============================================================
# JobAgent AI — Config
# Edit this file to match your profile and preferences
# ============================================================

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
SCORE_THRESHOLD = 7        # Only keep jobs with Claude score >= this
TOP_JOBS_PER_DAY = 5       # Max jobs to include in daily digest

# --- Scheduler ---
DAILY_RUN_TIME = "07:00"   # 24h format, local time

# --- Email (fill in Week 3) ---
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_RECEIVER = "your_email@gmail.com"
EMAIL_APP_PASSWORD = "your_gmail_app_password"  # Gmail App Password, not your real password

# --- Paths ---
DB_PATH = "data/jobagent.db"
LOG_PATH = "logs/jobagent.log"
RESUME_PATH = "resume/base_resume.json"
PDF_OUTPUT_DIR = "data/pdfs/"
