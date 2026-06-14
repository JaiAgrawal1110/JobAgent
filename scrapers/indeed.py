"""
JobAgent AI — Indeed Scraper
Uses Indeed's public RSS feeds (no login needed).
"""

import feedparser
import logging
import time
from urllib.parse import urlencode, quote_plus
from config import SEARCH_KEYWORDS, LOCATIONS

logger = logging.getLogger(__name__)

INDEED_RSS_BASE = "https://in.indeed.com/rss?"


def build_indeed_url(keyword: str, location: str) -> str:
    params = {
        "q": keyword,
        "l": location,
        "sort": "date",
        "fromage": "1",   # posted in last 1 day
        "limit": "25",
    }
    return INDEED_RSS_BASE + urlencode(params)


def parse_feed(url: str, source_label: str = "Indeed") -> list[dict]:
    jobs = []
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            logger.warning("Feed parse warning for %s: %s", url, feed.bozo_exception)

        for entry in feed.entries:
            title   = entry.get("title", "").strip()
            link    = entry.get("link", "").strip()
            summary = entry.get("summary", "").strip()
            company_tag = entry.get("source", {})
            company = company_tag.get("title", "") if isinstance(company_tag, dict) else ""

            # Indeed puts "company - location" in the title sometimes
            # e.g.  "ML Engineer - Bengaluru, Karnataka - TechCorp"
            location = ""
            if " - " in title:
                parts = title.split(" - ")
                if len(parts) >= 2:
                    location = parts[1]

            if not title or not link:
                continue

            jobs.append({
                "title":       title,
                "company":     company or "Unknown",
                "location":    location,
                "url":         link,
                "description": summary,
                "source":      source_label,
            })

        logger.info("Indeed [%s | %s]: %d jobs", url[:60], source_label, len(jobs))
    except Exception as e:
        logger.error("Error scraping Indeed feed %s: %s", url, e)

    return jobs


def scrape_indeed() -> list[dict]:
    """Scrape Indeed RSS for all keyword × location combos."""
    all_jobs = []
    for keyword in SEARCH_KEYWORDS:
        for location in LOCATIONS:
            url = build_indeed_url(keyword, location)
            jobs = parse_feed(url, source_label="Indeed")
            all_jobs.extend(jobs)
            time.sleep(1)   # be polite
    logger.info("Indeed total raw jobs: %d", len(all_jobs))
    return all_jobs
