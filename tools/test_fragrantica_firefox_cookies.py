#!/usr/bin/env python3
"""Inspect Fragrantica search HTML using the user's local Firefox cookies.

Goal: identify the actual search-result block/order instead of ranking every
perfume link found anywhere in the page. Cookie names/values are never printed
or written to disk.
"""
from __future__ import annotations

import html
import re
import sys
from urllib.parse import quote_plus

TERM = " ".join(sys.argv[1:]).strip() or "Cheirosa 39 Sol de Janeiro"
TARGET_WORDS = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", TERM) if len(w) > 1]


def perfume_links(fragment: str) -> list[str]:
    out: list[str] = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', fragment, flags=re.I):
        href = html.unescape(href)
        if re.search(r"/perfume/[^/]+/[^/]+-\d+\.html", href, flags=re.I):
            if href.startswith("/"):
                href = "https://www.fragrantica.com" + href
            href = href.split("#", 1)[0].split("?", 1)[0]
            if href not in out:
                out.append(href)
    return out


def main() -> int:
    try:
        import browser_cookie3
        import requests
    except ImportError:
        print("MISSING_DEPENDENCIES")
        return 2

    try:
        jar = browser_cookie3.firefox(domain_name="fragrantica.com")
    except Exception as exc:
        print(f"COOKIE_LOAD_ERROR: {type(exc).__name__}: {exc}")
        return 3

    print(f"Loaded Fragrantica cookies from Firefox: {sum(1 for _ in jar)}")
    session = requests.Session()
    session.cookies.update(jar)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:154.0) Gecko/20100101 Firefox/154.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })

    url = "https://www.fragrantica.com/search/?query=" + quote_plus(TERM)
    print(f"Query: {TERM}")
    print(f"Opening: {url}")
    try:
        response = session.get(url, timeout=25, allow_redirects=True)
    except requests.RequestException as exc:
        print(f"REQUEST_ERROR: {type(exc).__name__}: {exc}")
        return 5

    print(f"HTTP status: {response.status_code}")
    text = response.text
    lowered = text[:50000].lower()
    if response.status_code in (401, 403, 429):
        print("RESULT: BLOCKED")
        return 6
    if any(x in lowered for x in ("verify you are human", "checking your browser", "access denied", "ci siamo quasi", "captcha")):
        print("RESULT: CHALLENGE_DETECTED")
        return 7

    all_links = perfume_links(text)
    print(f"All perfume links in HTML: {len(all_links)}")

    # Locate occurrences of query-specific terms and inspect their nearest HTML
    # containers. This lets us discover Fragrantica's actual result markup from
    # the returned page rather than guessing from global links.
    low = text.lower()
    anchors: list[int] = []
    for needle in (TERM.lower(), "cheirosa", "sol-de-janeiro", "56681"):
        start = 0
        while True:
            pos = low.find(needle, start)
            if pos < 0:
                break
            anchors.append(pos)
            start = pos + len(needle)
    anchors = sorted(set(anchors))
    print(f"Query-related HTML occurrences: {len(anchors)}")

    candidates: list[tuple[int, int, list[str]]] = []
    # Inspect windows of increasing size around each query occurrence. A real
    # search-results block should contain Cheirosa 39 and nearby related links,
    # while excluding the hundreds of global navigation/catalog links.
    for pos in anchors:
        for radius in (1500, 3000, 6000, 12000):
            frag = text[max(0, pos-radius): min(len(text), pos+radius)]
            links = perfume_links(frag)
            if not links:
                continue
            joined = " ".join(links).lower()
            relevance = sum(1 for w in TARGET_WORDS if w in joined)
            if "cheirosa-39-56681.html" in joined:
                relevance += 10
            candidates.append((relevance, len(links), links))

    # Prefer a compact fragment containing the known query result, not a huge
    # page-wide fragment. This is diagnostic only; no mapping is written.
    candidates.sort(key=lambda x: (-x[0], x[1]))
    seen: set[tuple[str, ...]] = set()
    shown = 0
    print("Candidate result fragments:")
    for relevance, count, links in candidates:
        key = tuple(links)
        if key in seen:
            continue
        seen.add(key)
        if not any("Cheirosa-39-56681.html" in x for x in links):
            continue
        shown += 1
        print(f"\nFRAGMENT {shown}: relevance={relevance} perfume_links={count}")
        for i, link in enumerate(links[:15], 1):
            print(f" {i:2}. {link}")
        if shown >= 5:
            break

    if shown == 0:
        print("RESULT: TARGET_NOT_FOUND_IN_HTTP_HTML")
        return 8

    print("RESULT: STRUCTURE_CAPTURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
