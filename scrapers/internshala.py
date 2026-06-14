"""
JobAgent AI — Internshala Scraper
Scrapes internship listings from Internshala's search pages.
"""

import requests
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
    Internshala URL pattern:
    /internships/keywords-<kw>/location-<loc>
    """
    kw  = keyword.lower().replace(" ", "-")
    loc = location.lower().replace(" ", "-")
    return f"{BASE_URL}/internships/keywords-{kw}/location-{loc}"


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
                # Title
                title_el = card.select_one(".job-internship-name") or card.select_one("h3")
                title = title_el.get_text(strip=True) if title_el else ""

                # Company
                company_el = card.select_one(".company-name") or card.select_one(".institute_name")
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                # Location
                location_el = card.select_one(".location_link") or card.select_one(".locations_info")
                location = location_el.get_text(strip=True) if location_el else ""

                # Link
                link_el = card.select_one("a.view_detail_button") or card.select_one("a[href*='/internship/detail']")
                link = (BASE_URL + link_el["href"]) if link_el and link_el.get("href") else url

                # Stipend / meta as description
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
                    "title":       title,
                    "company":     company,
                    "location":    location,
                    "url":         link,
                    "description": description,
                    "source":      "Internshala",
                })
            except Exception as e:
                logger.debug("Card parse error: %s", e)
                continue

    except requests.RequestException as e:
        logger.error("Request error for Internshala %s: %s", url, e)

    return jobs


def scrape_internshala() -> list[dict]:
    """Scrape Internshala for all keyword × location combos."""
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

    logger.info("Internshala total raw jobs: %d", len(all_jobs))
    return all_jobs
