"""
JobAgent AI — Database Manager
Handles SQLite storage and deduplication of job listings.
"""

import sqlite3
import hashlib
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            job_hash    TEXT UNIQUE NOT NULL,
            title       TEXT NOT NULL,
            company     TEXT,
            location    TEXT,
            url         TEXT,
            description TEXT,
            source      TEXT,
            score       REAL DEFAULT NULL,
            applied     INTEGER DEFAULT 0,
            fetched_at  TEXT NOT NULL,
            scored_at   TEXT DEFAULT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS digests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sent_at     TEXT NOT NULL,
            job_ids     TEXT NOT NULL,
            email_status TEXT
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialised at %s", DB_PATH)


def make_hash(title: str, company: str, url: str) -> str:
    """Stable fingerprint so we never store the same job twice."""
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{url.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def insert_job(job: dict) -> bool:
    """
    Insert a job dict. Returns True if inserted, False if duplicate.
    Expected keys: title, company, location, url, description, source
    """
    job_hash = make_hash(job["title"], job.get("company", ""), job.get("url", ""))
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO jobs (job_hash, title, company, location, url, description, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_hash,
                job["title"],
                job.get("company", "Unknown"),
                job.get("location", ""),
                job.get("url", ""),
                job.get("description", ""),
                job.get("source", ""),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # duplicate
    finally:
        conn.close()


def bulk_insert_jobs(jobs: list[dict]) -> tuple[int, int]:
    """Insert a list of jobs. Returns (inserted, duplicates)."""
    inserted, dupes = 0, 0
    for job in jobs:
        if insert_job(job):
            inserted += 1
        else:
            dupes += 1
    logger.info("Bulk insert: %d new, %d duplicates", inserted, dupes)
    return inserted, dupes


def get_unscored_jobs(limit: int = 200) -> list[dict]:
    """Fetch jobs that haven't been scored by Claude yet."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE score IS NULL ORDER BY fetched_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_score(job_id: int, score: float):
    conn = get_connection()
    conn.execute(
        "UPDATE jobs SET score=?, scored_at=? WHERE id=?",
        (score, datetime.utcnow().isoformat(), job_id)
    )
    conn.commit()
    conn.close()


def get_top_jobs(threshold: float = 7.0, limit: int = 5) -> list[dict]:
    """Fetch highest-scored jobs that haven't been sent in a digest yet.
    Ties on score break in favor of the most recently fetched (i.e. newest) job."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM jobs
        WHERE score >= ? AND applied = 0
        ORDER BY score DESC, fetched_at DESC
        LIMIT ?
        """,
        (threshold, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_applied(job_id: int):
    conn = get_connection()
    conn.execute("UPDATE jobs SET applied=1 WHERE id=?", (job_id,))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    total   = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    scored  = conn.execute("SELECT COUNT(*) FROM jobs WHERE score IS NOT NULL").fetchone()[0]
    top     = conn.execute("SELECT COUNT(*) FROM jobs WHERE score >= 7").fetchone()[0]
    applied = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied=1").fetchone()[0]
    conn.close()
    return {"total": total, "scored": scored, "top_matches": top, "applied": applied}