#!/usr/bin/env python3
"""Local Firefox verification test for Shobi Master product 4651.

Uses the same temporary-copy Firefox profile approach as test_fragrantica_firefox.py.
It does not write mapping/state files and does not commit or push anything.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import time
from pathlib import Path
from urllib.parse import quote_plus

from test_fragrantica_firefox import find_firefox_profile

TERM = "Cheirosa 39 Sol de Janeiro"
EXPECTED_BRAND = "Sol-de-Janeiro"
EXPECTED_NAME_TOKENS = {"cheirosa", "39"}


def main() -> int:
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
    except ImportError:
        print("SELENIUM_MISSING: python -m pip install selenium")
        return 2

    source = find_firefox_profile()
    print(f"Testing Shobi 4651: {TERM}")
    print(f"Firefox profile found: {source}")

    with tempfile.TemporaryDirectory(prefix="shobi_4651_firefox_") as td:
        profile_copy = Path(td) / "profile"
        shutil.copytree(
            source,
            profile_copy,
            ignore=shutil.ignore_patterns("parent.lock", "lock", ".parentlock", "cache2", "startupCache"),
        )

        options = Options()
        options.profile = str(profile_copy)
        options.add_argument("-foreground")
        driver = webdriver.Firefox(options=options)
        try:
            search_url = "https://www.fragrantica.com/search/?query=" + quote_plus(TERM)
            print(f"Opening search: {search_url}")
            driver.get(search_url)
            time.sleep(7)

            html = driver.page_source
            links = []
            for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I):
                if re.search(r"/perfume/[^/]+/[^/]+-\d+\.html", href, flags=re.I):
                    if href.startswith("/"):
                        href = "https://www.fragrantica.com" + href
                    if href not in links:
                        links.append(href)

            print(f"Candidates found: {len(links)}")
            for i, link in enumerate(links[:10], 1):
                print(f"{i}. {link}")

            matches = []
            for link in links:
                low = link.lower()
                if EXPECTED_BRAND.lower() not in low:
                    continue
                slug = low.rsplit("/", 1)[-1]
                if all(tok in slug for tok in EXPECTED_NAME_TOKENS):
                    matches.append(link)

            if len(matches) != 1:
                print(f"RESULT: NOT_UNIQUE ({len(matches)} exact-looking matches)")
                return 4

            candidate = matches[0]
            print(f"Exact candidate: {candidate}")
            driver.get(candidate)
            time.sleep(6)
            page_title = driver.title
            page_url = driver.current_url
            page_html = driver.page_source
            print(f"Candidate title: {page_title}")
            print(f"Candidate URL: {page_url}")

            lowered = (page_title + "\n" + page_html[:30000]).lower()
            if "403 forbidden" in lowered or "access denied" in lowered:
                print("RESULT: BLOCKED_ON_CANDIDATE")
                return 5

            m = re.search(r"-(\d+)\.html(?:$|[?#])", page_url)
            if not m:
                m = re.search(r"-(\d+)\.html", candidate)
            if not m:
                print("RESULT: PAGE_OPENED_BUT_ID_NOT_PARSED")
                return 6

            fragrantica_id = m.group(1)
            if "cheirosa" not in page_title.lower() or "39" not in page_title.lower():
                print("RESULT: PAGE_TITLE_MISMATCH")
                return 7

            print(f"FRAGRANTICA_ID: {fragrantica_id}")
            print("RESULT: VERIFIED")
            return 0
        finally:
            print("Closing test Firefox...")
            driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
