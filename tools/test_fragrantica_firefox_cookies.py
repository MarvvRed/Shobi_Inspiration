#!/usr/bin/env python3
"""Local-only test: reuse Firefox cookies for a normal HTTP Fragrantica search.

Safety properties:
- reads cookies only from the user's local Firefox profile;
- never prints cookie names or values;
- never writes cookies to disk or GitHub;
- performs one GET request to a Fragrantica search URL;
- stops if Fragrantica returns a block/challenge response.
"""
from __future__ import annotations

import re
import sys
from urllib.parse import quote_plus

TERM = " ".join(sys.argv[1:]).strip() or "Cheirosa 39 Sol de Janeiro"


def main() -> int:
    try:
        import browser_cookie3
        import requests
    except ImportError:
        print("MISSING_DEPENDENCIES")
        print("Run: python -m pip install browser-cookie3 requests")
        return 2

    try:
        jar = browser_cookie3.firefox(domain_name="fragrantica.com")
    except Exception as exc:
        print(f"COOKIE_LOAD_ERROR: {type(exc).__name__}: {exc}")
        return 3

    cookie_count = sum(1 for _ in jar)
    print(f"Loaded Fragrantica cookies from Firefox: {cookie_count}")
    if cookie_count == 0:
        print("RESULT: NO_FRAGRANTICA_COOKIES")
        return 4

    session = requests.Session()
    session.cookies.update(jar)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:154.0) Gecko/20100101 Firefox/154.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })

    url = "https://www.fragrantica.com/search/?query=" + quote_plus(TERM)
    print(f"Opening: {url}")
    try:
        response = session.get(url, timeout=25, allow_redirects=True)
    except requests.RequestException as exc:
        print(f"REQUEST_ERROR: {type(exc).__name__}: {exc}")
        return 5

    print(f"HTTP status: {response.status_code}")
    print(f"Final URL: {response.url}")
    text = response.text
    lowered = text[:50000].lower()

    if response.status_code in (401, 403, 429):
        print("RESULT: BLOCKED")
        return 6
    if any(marker in lowered for marker in ("verify you are human", "checking your browser", "access denied", "ci siamo quasi", "captcha")):
        print("RESULT: CHALLENGE_DETECTED")
        return 7

    links = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', text, flags=re.I):
        if re.search(r"/perfume/[^/]+/[^/]+-\d+\.html", href, flags=re.I):
            if href.startswith("/"):
                href = "https://www.fragrantica.com" + href
            if href not in links:
                links.append(href)

    print(f"Perfume links found: {len(links)}")
    for link in links[:10]:
        print(link)

    if links:
        print("RESULT: OK")
        return 0

    print("RESULT: PAGE_OPENED_BUT_NO_PERFUME_LINKS")
    return 8


if __name__ == "__main__":
    raise SystemExit(main())
