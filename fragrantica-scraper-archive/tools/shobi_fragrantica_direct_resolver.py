#!/usr/bin/env python3
"""Direct-Fragrantica wrapper for the conservative Shobi resolver.

Archived copy. Tries Fragrantica's own public search page first, then falls
back to the existing free HTML search providers.
"""
from __future__ import annotations

import json
import re
import sys
import time
from urllib.parse import quote_plus

import shobi_online_resolver as base

_original_search_web = base.search_web


def _extract_term(query: str) -> str:
    quoted = re.findall(r'"([^"]+)"', query or "")
    if quoted:
        return quoted[0].strip()
    q = re.sub(r"site:fragrantica\.com/perfume", " ", query or "", flags=re.I)
    q = re.sub(r"\bfragrantica\b", " ", q, flags=re.I)
    return " ".join(q.split()).strip()


def _direct_fragrantica(term: str):
    if not term:
        return [], "fragrantica-direct:no-term", []
    urls = [
        "https://www.fragrantica.com/search/?query=" + quote_plus(term),
        "https://www.fragrantica.com/search/?q=" + quote_plus(term),
        "https://www.fragrantica.com/search/?name=" + quote_plus(term),
    ]
    links, errors, counts = [], [], []
    for url in urls:
        try:
            page = base.fetch(url)
            found = base.extract_fragrantica_links(page)
            counts.append(str(len(found)))
            for item in found:
                if item not in links:
                    links.append(item)
            if links:
                break
        except Exception as e:
            errors.append(f"fragrantica-direct: {type(e).__name__}: {e}")
        time.sleep(0.5)
    return links[:20], "fragrantica-direct:" + "/".join(counts or ["0"]), errors


def search_web_direct_first(query: str):
    term = _extract_term(query)
    direct, direct_provider, direct_errors = _direct_fragrantica(term)
    if direct:
        return direct, direct_provider, direct_errors
    fallback, fallback_provider, fallback_errors = _original_search_web(query)
    return fallback, direct_provider + "," + fallback_provider, direct_errors + fallback_errors


base.search_web = search_web_direct_first


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("expected one Master JSON object on stdin")
    row = json.loads(raw)
    if not isinstance(row, dict):
        raise SystemExit("stdin JSON must be an object")
    print(json.dumps(base.resolve(row), ensure_ascii=False))


if __name__ == "__main__":
    main()
