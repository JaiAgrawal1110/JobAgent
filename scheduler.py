"""
JobAgent AI — Scheduler (Week 4)
Runs the full pipeline daily at the configured time.
Usage: python scheduler.py
"""

import schedule
import time
import logging
from config import DAILY_RUN_TIME

logger = logging.getLogger(__name__)


def run_full_pipeline():
    """The complete daily pipeline — called by the scheduler."""
    logger.info("⏰ Scheduler triggered — starting full pipeline")

    from run import run_scraper_pipeline
    from database import get_unscored_jobs, update_score, get_top_jobs
    from scorer import score_job, filter_top_jobs
    from tailor import prepare_application
    from pdf_generator import generate_resume_pdf
    from emailer import send_digest
    from config import SCORE_THRESHOLD, TOP_JOBS_PER_DAY

    # Step 1: Scrape
    run_scraper_pipeline()

    # Step 2: Score unscored jobs
    unscored = get_unscored_jobs(limit=100)
    logger.info("Scoring %d unscored jobs with Claude...", len(unscored))
    for job in unscored:
        score, reason = score_job(job)
        update_score(job["id"], score)
        job["score"] = score
        job["score_reason"] = reason

    # Step 3: Get top jobs
    top_jobs = get_top_jobs(threshold=SCORE_THRESHOLD, limit=TOP_JOBS_PER_DAY)
    if not top_jobs:
        logger.info("No jobs scored above threshold today. Skipping email.")
        return

    logger.info("Top %d jobs selected. Tailoring applications...", len(top_jobs))

    # Step 4: Tailor resume + cover letter for each
    applications = []
    pdf_paths = []
    for job in top_jobs:
        app = prepare_application(job)
        applications.append(app)

        # Step 5: Generate PDF
        from pdf_generator import generate_resume_pdf
        pdf_path = generate_resume_pdf(
            app["tailored_resume"], job, app["cover_letter"]
        )
        pdf_paths.append(pdf_path)

    # Step 6: Send email digest
    send_digest(applications, pdf_paths)

    logger.info("✅ Full pipeline complete for today!")


def start_scheduler():
    logger.info("JobAgent scheduler starting — will run daily at %s", DAILY_RUN_TIME)
    schedule.every().day.at(DAILY_RUN_TIME).do(run_full_pipeline)

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    import os, sys
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.FileHandler("logs/jobagent.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    start_scheduler()
