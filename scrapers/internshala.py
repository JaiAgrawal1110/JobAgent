"""
JobAgent AI — Internshala Scraper
Scrapes internship listings from Internshala's search pages, sorted newest-first.
"""

import requests
import re
from bs4 import BeautifulSoup
import logging
import time
from config import SEARCH_KEYWORDS, LOCATIONS

logger = logging.getLogger(__name__)

BASE_URL = "https://internshala.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def build_search_url(keyword: str, location: str) -> str:
    """
    Internshala URL pattern, sorted by most recent first:
    /internships/keywords-<kw>/location-<loc>/sort-by-date-desc
    """
    kw  = keyword.lower().replace(" ", "-")
    loc = location.lower().replace(" ", "-")
    return f"{BASE_URL}/internships/keywords-{kw}/location-{loc}/sort-by-date-desc"


def _parse_posted_recency(card) -> int:
    """
    Extract how many days ago a listing was posted, for in-Python sorting
    as a fallback/double-check on top of the site's own sort order.
    Returns a small int (0 = today) — higher = older. Defaults to a large
    number if we can't parse anything (pushes unknowns to the back).
    """
    text_blob = card.get_text(" ", strip=True).lower()

    if "few hours ago" in text_blob or "just now" in text_blob or "today" in text_blob:
        return 0
    if "1 day ago" in text_blob or "yesterday" in text_blob:
        return 1

    match = re.search(r"(\d+)\s+day[s]?\s+ago", text_blob)
    if match:
        return int(match.group(1))

    match = re.search(r"(\d+)\s+week[s]?\s+ago", text_blob)
    if match:
        return int(match.group(1)) * 7

    match = re.search(r"(\d+)\s+month[s]?\s+ago", text_blob)
    if match:
        return int(match.group(1)) * 30

    return 999  # unknown recency — sort to the back


def scrape_listing_page(url: str) -> list[dict]:
    jobs = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning("Internshala returned %d for %s", resp.status_code, url)
            return jobs

        soup = BeautifulSoup(resp.text, "lxml")

        # Each internship card has class "individual_internship"
        cards = soup.select(".individual_internship")
        logger.info("Internshala [%s]: found %d cards", url, len(cards))

        for card in cards:
            try:
                title_el = card.select_one(".job-internship-name") or card.select_one("h3")
                title = title_el.get_text(strip=True) if title_el else ""

                company_el = card.select_one(".company-name") or card.select_one(".institute_name")
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                location_el = card.select_one(".location_link") or card.select_one(".locations_info")
                location = location_el.get_text(strip=True) if location_el else ""

                link_el = card.select_one("a.view_detail_button") or card.select_one("a[href*='/internship/detail']")
                link = (BASE_URL + link_el["href"]) if link_el and link_el.get("href") else url

                stipend_el = card.select_one(".stipend")
                duration_el = card.select_one(".internship_other_details_container")
                desc_parts = []
                if stipend_el:
                    desc_parts.append("Stipend: " + stipend_el.get_text(strip=True))
                if duration_el:
                    desc_parts.append(duration_el.get_text(" | ", strip=True))
                description = " | ".join(desc_parts)

                if not title:
                    continue

                jobs.append({
                    "title":          title,
                    "company":        company,
                    "location":       location,
                    "url":            link,
                    "description":    description,
                    "source":         "Internshala",
                    "_recency_days":  _parse_posted_recency(card),  # internal sort key, stripped before DB insert
                })
            except Exception as e:
                logger.debug("Card parse error: %s", e)
                continue

    except requests.RequestException as e:
        logger.error("Request error for Internshala %s: %s", url, e)

    return jobs


def scrape_internshala() -> list[dict]:
    """Scrape Internshala for all keyword × location combos, newest-first."""
    all_jobs = []
    seen_urls = set()

    for keyword in SEARCH_KEYWORDS:
        for location in LOCATIONS:
            url = build_search_url(keyword, location)
            jobs = scrape_listing_page(url)
            for job in jobs:
                if job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    all_jobs.append(job)
            time.sleep(2)   # polite crawl delay

    # Sort newest-first across the combined pool (site sort + our own check)
    all_jobs.sort(key=lambda j: j.get("_recency_days", 999))

    # Strip internal sort key before returning — not part of the DB schema
    for job in all_jobs:
        job.pop("_recency_days", None)

    logger.info("Internshala total raw jobs: %d (sorted newest-first)", len(all_jobs))
    return all_jobs