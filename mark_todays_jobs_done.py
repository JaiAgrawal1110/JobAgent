"""
One-off helper: marks the current top-5 scored jobs as 'applied'
so they don't repeat in tomorrow's digest, since you already
received them in today's test emails.

Run this once: python mark_todays_jobs_done.py
"""

from database import get_top_jobs, mark_applied
from config import SCORE_THRESHOLD, TOP_JOBS_PER_DAY

top_jobs = get_top_jobs(threshold=SCORE_THRESHOLD, limit=TOP_JOBS_PER_DAY)

if not top_jobs:
    print("No top jobs found to mark.")
else:
    for job in top_jobs:
        mark_applied(job["id"])
        print(f"Marked as applied: {job['title']} @ {job['company']}")
    print(f"\nDone — {len(top_jobs)} jobs marked. They won't appear in future digests.")
