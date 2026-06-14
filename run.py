"""
JobAgent AI — Full Pipeline Runner
Runs all 4 weeks in sequence: Scrape → Score → Tailor → PDF → Email.
For one-off runs. For daily automation use: python scheduler.py
"""

import logging
import os
import sys
from datetime import datetime

os.makedirs("logs", exist_ok=True)
os.makedirs("data/pdfs", exist_ok=True)
os.makedirs("resume", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("logs/jobagent.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("JobAgent")

from database import init_db, bulk_insert_jobs, get_unscored_jobs, update_score, get_top_jobs, get_stats
from scrapers import scrape_indeed, scrape_internshala, scrape_wellfound
from config import SCORE_THRESHOLD, TOP_JOBS_PER_DAY


def run_scraper_pipeline():
    logger.info("=" * 60)
    logger.info("WEEK 1 — Scraper Pipeline")
    logger.info("=" * 60)
    init_db()
    all_jobs = []
    for name, fn in [("Indeed", scrape_indeed), ("Internshala", scrape_internshala), ("Wellfound", scrape_wellfound)]:
        logger.info("Scraping %s...", name)
        try:
            jobs = fn()
            all_jobs.extend(jobs)
            logger.info("%s: %d jobs fetched", name, len(jobs))
        except Exception as e:
            logger.error("%s scraper failed: %s", name, e)
    inserted, dupes = bulk_insert_jobs(all_jobs)
    logger.info("Stored: %d new, %d duplicates skipped", inserted, dupes)
    return inserted


def run_scorer_and_tailor():
    from scorer import score_job
    from tailor import prepare_application
    logger.info("=" * 60)
    logger.info("WEEK 2 — Claude Scorer + Resume Tailor")
    logger.info("=" * 60)
    unscored = get_unscored_jobs(limit=100)
    logger.info("Scoring %d unscored jobs...", len(unscored))
    for job in unscored:
        score, reason = score_job(job)
        update_score(job["id"], score)
        job["score"] = score
        job["score_reason"] = reason
    top_jobs = get_top_jobs(threshold=SCORE_THRESHOLD, limit=TOP_JOBS_PER_DAY)
    if not top_jobs:
        logger.info("No jobs above threshold %.1f today.", SCORE_THRESHOLD)
        return []
    logger.info("%d top jobs. Tailoring resumes + cover letters...", len(top_jobs))
    return [prepare_application(job) for job in top_jobs]


def run_pdf_and_email(applications):
    from pdf_generator import generate_resume_pdf
    from emailer import send_digest
    logger.info("=" * 60)
    logger.info("WEEK 3 — PDF Generator + Email Digest")
    logger.info("=" * 60)
    pdf_paths = []
    for app in applications:
        try:
            path = generate_resume_pdf(app["tailored_resume"], app["job"], app["cover_letter"])
            pdf_paths.append(path)
        except Exception as e:
            logger.error("PDF generation failed: %s", e)
    send_digest(applications, pdf_paths)
    return pdf_paths


def run_full_pipeline():
    logger.info("JobAgent AI — Full Pipeline starting")
    logger.info("Run time: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    run_scraper_pipeline()
    applications = run_scorer_and_tailor()
    if applications:
        run_pdf_and_email(applications)
    stats = get_stats()
    logger.info("Pipeline complete! DB stats: %s", stats)


if __name__ == "__main__":
    run_full_pipeline()
