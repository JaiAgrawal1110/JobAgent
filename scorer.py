"""
JobAgent AI — Claude Job Scorer (Week 2)
Scores each job 1-10 against your profile using Claude API.
"""

import anthropic
import logging
import json
from config import PROFILE, SCORE_THRESHOLD

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()


SCORER_SYSTEM = """You are a job-match evaluator. Given a candidate profile and a job listing,
return a JSON object with exactly two keys:
  "score": integer 1-10 (10 = perfect match)
  "reason": one sentence explaining the score

Respond ONLY with raw JSON. No markdown, no explanation outside the JSON."""


def score_job(job: dict) -> tuple[float, str]:
    """
    Send a job to Claude and get back a score + reason.
    Returns (score, reason).
    """
    profile_text = (
        f"Roles seeking: {', '.join(PROFILE['roles'])}\n"
        f"Experience: {PROFILE['experience_years']} years\n"
        f"Job type: {PROFILE['job_type']}\n"
        f"Preferred locations: {', '.join(PROFILE['locations'])}\n"
        f"Skills: {', '.join(PROFILE['skills'])}"
    )

    job_text = (
        f"Title: {job.get('title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Location: {job.get('location', '')}\n"
        f"Description: {job.get('description', '')[:1500]}"  # truncate to save tokens
    )

    prompt = f"CANDIDATE PROFILE:\n{profile_text}\n\nJOB LISTING:\n{job_text}\n\nScore this match."

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            system=SCORER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        data = json.loads(raw)
        score = float(data.get("score", 0))
        reason = data.get("reason", "")
        logger.info("Scored '%s' @ %s → %.1f | %s", job.get("title"), job.get("company"), score, reason)
        return score, reason
    except Exception as e:
        logger.error("Scoring error for job %s: %s", job.get("id"), e)
        return 0.0, "Scoring failed"


def score_all_jobs(jobs: list[dict]) -> list[dict]:
    """Score a list of job dicts. Attaches score + reason to each."""
    results = []
    for job in jobs:
        score, reason = score_job(job)
        job["score"] = score
        job["score_reason"] = reason
        results.append(job)
    return results


def filter_top_jobs(jobs: list[dict], threshold: float = SCORE_THRESHOLD, top_n: int = 5) -> list[dict]:
    """Filter jobs above threshold and return top N by score."""
    passing = [j for j in jobs if j.get("score", 0) >= threshold]
    passing.sort(key=lambda x: x["score"], reverse=True)
    return passing[:top_n]
