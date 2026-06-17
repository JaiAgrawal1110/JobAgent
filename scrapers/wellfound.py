"""
JobAgent AI — Wellfound Scraper
Scrapes startup job listings from Wellfound (formerly AngelList Talent).

Note: Wellfound is JS-heavy. This scraper targets their public role pages
and the lightweight search endpoint that returns JSON.
"""

import requests
from bs4 import BeautifulSoup
import logging
import time
from config import SEARCH_KEYWORDS

logger = logging.getLogger(__name__)

BASE_URL = "https://wellfound.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Role slug mappings for Wellfound URL patterns
ROLE_SLUGS = {
    "ML engineer intern":        "machine-learning",
    "AI engineer intern":        "artificial-intelligence",
    "Python developer intern":   "python",
    "backend developer intern":  "backend",
    "machine learning intern":   "machine-learning",
}


def scrape_role_page(role_slug: str) -> list[dict]:
    """Scrape a Wellfound role listing page, sorted newest-first."""
    url = f"{BASE_URL}/role/{role_slug}?location_type=remote&location_type=in-office&sort=recency"
    jobs = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning("Wellfound returned %d for %s", resp.status_code, url)
            return jobs

        soup = BeautifulSoup(resp.text, "lxml")

        # Wellfound job cards — selectors may need updating if they change their HTML
        cards = (
            soup.select("div[class*='JobListing']") or
            soup.select(".styles_component__UCLp1") or
            soup.select("a[href*='/jobs/']")
        )

        logger.info("Wellfound [%s]: %d raw elements", role_slug, len(cards))

        seen = set()
        for card in cards:
            try:
                # If it's an <a> tag itself, handle differently
                if card.name == "a":
                    link = BASE_URL + card["href"] if card["href"].startswith("/") else card["href"]
                    title = card.get_text(strip=True)
                    company = ""
                else:
                    link_el = card.select_one("a[href*='/jobs/']") or card.select_one("a")
                    link = ""
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        link = (BASE_URL + href) if href.startswith("/") else href

                    title_el = (
                        card.select_one("h2") or
                        card.select_one("h3") or
                        card.select_one("[class*='title']")
                    )
                    title = title_el.get_text(strip=True) if title_el else ""

                    company_el = (
                        card.select_one("[class*='company']") or
                        card.select_one("[class*='startup']")
                    )
                    company = company_el.get_text(strip=True) if company_el else "Unknown"

                if not title or link in seen:
                    continue
                seen.add(link)

                location_el = card.select_one("[class*='location']")
                location = location_el.get_text(strip=True) if location_el else "Remote / India"

                jobs.append({
                    "title":       title,
                    "company":     company,
                    "location":    location,
                    "url":         link,
                    "description": f"Role: {role_slug} | Source: Wellfound",
                    "source":      "Wellfound",
                })
            except Exception as e:
                logger.debug("Wellfound card error: %s", e)
                continue

    except requests.RequestException as e:
        logger.error("Request error for Wellfound %s: %s", url, e)

    return jobs


def scrape_wellfound() -> list[dict]:
    """Scrape Wellfound across all relevant role slugs."""
    all_jobs = []
    seen_urls = set()
    visited_slugs = set()

    for keyword in SEARCH_KEYWORDS:
        slug = ROLE_SLUGS.get(keyword)
        if not slug or slug in visited_slugs:
            continue
        visited_slugs.add(slug)
        jobs = scrape_role_page(slug)
        for job in jobs:
            if job["url"] and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
        time.sleep(2)

    logger.info("Wellfound total raw jobs: %d", len(all_jobs))
    return all_jobs