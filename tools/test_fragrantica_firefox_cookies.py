#!/usr/bin/env python3
"""Local-only test: reuse Firefox cookies for a normal HTTP Fragrantica search.

Reads Fragrantica cookies from the user's local Firefox profile, performs one
search request, then ranks perfume URLs by relevance to the query. Cookie names
and values are never printed or written to disk.
"""
from __future__ import annotations

import re
import sys
from difflib import SequenceMatcher
from urllib.parse import quote_plus, unquote

TERM = " ".join(sys.argv[1:]).strip() or "Cheirosa 39 Sol de Janeiro"
STOP = {"de", "del", "della", "di", "da", "do", "dos", "the", "of", "for", "and", "e", "le", "la", "les"}


def norm(s: str) -> str:
    s = unquote(s).lower().replace("-", " ").replace("_", " ")
    s = re.sub(r"[^a-z0-9à-ÿ]+", " ", s)
    return " ".join(s.split())


def tokens(s: str) -> list[str]:
    return [t for t in norm(s).split() if t not in STOP and len(t) > 1]


def label_from_url(url: str) -> str:
    m = re.search(r"/perfume/([^/]+)/([^/]+?)-\d+\.html", url, flags=re.I)
    if not m:
        return ""
    return norm(m.group(1) + " " + m.group(2))


def score_url(url: str, query: str) -> tuple[float, int, float]:
    label = label_from_url(url)
    q_tokens = tokens(query)
    l_tokens = set(tokens(label))
    overlap = sum(1 for t in q_tokens if t in l_tokens)
    coverage = overlap / max(1, len(q_tokens))
    seq = SequenceMatcher(None, norm(query), label).ratio()
    score = coverage * 100 + seq * 25
    return score, overlap, seq


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
    if any(marker in lowered for marker in ("verify you are human", "checking your browser", "access denied", "ci siamo quasi", "captcha")):
        print("RESULT: CHALLENGE_DETECTED")
        return 7

    links: list[str] = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', text, flags=re.I):
        if re.search(r"/perfume/[^/]+/[^/]+-\d+\.html", href, flags=re.I):
            if href.startswith("/"):
                href = "https://www.fragrantica.com" + href
            href = href.split("#", 1)[0].split("?", 1)[0]
            if href not in links:
                links.append(href)

    print(f"All perfume links in HTML: {len(links)}")
    ranked = sorted(((score_url(link, TERM), link) for link in links), reverse=True)

    print("Top ranked candidates:")
    for i, ((score, overlap, seq), link) in enumerate(ranked[:10], 1):
        print(f"{i:2}. score={score:6.2f} overlap={overlap} seq={seq:.3f}  {link}")

    if not ranked:
        print("RESULT: PAGE_OPENED_BUT_NO_PERFUME_LINKS")
        return 8

    top_score, top_link = ranked[0][0][0], ranked[0][1]
    second_score = ranked[1][0][0] if len(ranked) > 1 else 0.0
    gap = top_score - second_score
    print(f"TOP_CANDIDATE: {top_link}")
    print(f"TOP_SCORE: {top_score:.2f}")
    print(f"GAP_TO_SECOND: {gap:.2f}")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
