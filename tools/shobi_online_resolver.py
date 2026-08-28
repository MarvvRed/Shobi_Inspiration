#!/usr/bin/env python3
"""Conservative online resolver for one Shobi Master perfume row.

Input: one Master row as JSON on stdin.
Output: one mapping row as JSON on stdout.

The resolver searches the public web for Fragrantica candidates and only emits
CONFIRMED when the candidate matches the Shobi `inspired_by` text strongly.
Anything weaker is emitted as AMBIGUOUS rather than guessed.

No API key is required. Search providers are tried in order (DuckDuckGo HTML,
then Bing HTML). Fragrantica pages are fetched only for the best candidate and
only to strengthen verification; a blocked page does not crash the batch.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

UA = os.environ.get(
    "SHOBI_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36 ShobiIdentityResearch/1.0",
)
HTTP_TIMEOUT = float(os.environ.get("SHOBI_HTTP_TIMEOUT", "25"))
SEARCH_DELAY = float(os.environ.get("SHOBI_SEARCH_DELAY", "1.0"))

BAD_INSPIRED = {
    "", "the fragrance notes", "the fragrance notes of", "fragrance notes",
    "the notes", "notes",
}
STOPWORDS = {
    "for", "the", "and", "of", "by", "pour", "eau", "de", "parfum",
    "perfume", "fragrance", "edp", "edt", "intense", "men", "women",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def tokens(s: str):
    return {t for t in norm(s).split() if len(t) >= 2 and t not in STOPWORDS}


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urlopen(req, timeout=HTTP_TIMEOUT) as r:
        raw = r.read(2_000_000)
    return raw.decode("utf-8", errors="replace")


def unwrap_ddg(url: str) -> str:
    if "duckduckgo.com/l/?" in url:
        qs = parse_qs(urlparse(url).query)
        if qs.get("uddg"):
            return unquote(qs["uddg"][0])
    return url


def extract_links(page: str):
    out = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', page, re.I):
        u = html.unescape(m.group(1))
        u = unwrap_ddg(u)
        if u.startswith("//"):
            u = "https:" + u
        if "fragrantica.com/perfume/" in u:
            u = u.split("&")[0]
            if u not in out:
                out.append(u)
    return out


def search_web(query: str):
    errors = []
    providers = [
        ("duckduckgo", "https://html.duckduckgo.com/html/?q=" + quote_plus(query)),
        ("bing", "https://www.bing.com/search?q=" + quote_plus(query)),
    ]
    for name, url in providers:
        try:
            page = fetch(url)
            links = extract_links(page)
            if links:
                return links[:10], name, errors
            errors.append(f"{name}: no Fragrantica links")
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")
        time.sleep(SEARCH_DELAY)
    return [], "none", errors


def parse_fragrantica_url(url: str):
    # Typical: /perfume/Brand/Perfume-Name-12345.html
    p = urlparse(url)
    parts = [unquote(x) for x in p.path.split("/") if x]
    if len(parts) < 3 or parts[0].lower() != "perfume":
        return None
    brand_slug = parts[1]
    leaf = parts[-1]
    m = re.match(r"(.+)-(\d+)\.html$", leaf, re.I)
    if not m:
        return None
    perfume_slug, fid = m.groups()
    brand = brand_slug.replace("-", " ")
    perfume = perfume_slug.replace("-", " ")
    return {
        "url": f"https://www.fragrantica.com{p.path}",
        "id": fid,
        "brand_slug": brand,
        "perfume_slug": perfume,
    }


def candidate_score(inspired: str, cand) -> float:
    target = norm(inspired)
    candidate_text = norm(cand["brand_slug"] + " " + cand["perfume_slug"])
    seq = SequenceMatcher(None, target, candidate_text).ratio()
    a = tokens(target)
    b = tokens(candidate_text)
    overlap = len(a & b) / max(1, len(a))
    # Target containment is powerful for Shobi labels such as "X Brand".
    containment = 1.0 if target and target in candidate_text else 0.0
    return 0.45 * overlap + 0.35 * seq + 0.20 * containment


def page_title(page: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
    if not m:
        return ""
    return norm(html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))))


def verify_page(cand, inspired: str):
    try:
        page = fetch(cand["url"])
        title = page_title(page)
        wanted = tokens(inspired)
        title_tokens = tokens(title)
        coverage = len(wanted & title_tokens) / max(1, len(wanted))
        return coverage, title, None
    except Exception as e:
        return None, "", f"{type(e).__name__}: {e}"


def clean_name_from_slug(s: str) -> str:
    # Keep source spelling unavailable in URL; use readable title case conservatively.
    words = s.replace("-", " ").split()
    small = {"de", "du", "des", "di", "da", "of", "the", "and", "for", "by"}
    result = []
    for i, w in enumerate(words):
        if i and w.lower() in small:
            result.append(w.lower())
        elif w.isupper():
            result.append(w)
        else:
            result.append(w[:1].upper() + w[1:])
    return " ".join(result)


def ambiguous(row, note: str):
    return {
        "prestashop_product_id": str(row.get("prestashop_product_id", "")),
        "shobi_code": row.get("shobi_code", ""),
        "inspired_by": row.get("inspired_by", ""),
        "original_brand": "",
        "original_perfume": "",
        "identity_status": "AMBIGUOUS",
        "fragrantica_status": "NOT_FOUND",
        "fragrantica_id": "",
        "fragrantica_url": "",
        "evidence_note": note[:1800],
    }


def resolve(row):
    inspired = (row.get("inspired_by") or "").strip()
    if norm(inspired) in BAD_INSPIRED or len(tokens(inspired)) < 1:
        return ambiguous(row, "Shobi inspired_by is missing/broken; no identity forced")

    query = f'site:fragrantica.com/perfume "{inspired}" perfume'
    links, provider, search_errors = search_web(query)
    candidates = []
    for u in links:
        c = parse_fragrantica_url(u)
        if c:
            c["score"] = candidate_score(inspired, c)
            candidates.append(c)
    candidates.sort(key=lambda c: c["score"], reverse=True)

    if not candidates:
        return ambiguous(row, "No Fragrantica candidate found via public web search; " + "; ".join(search_errors))

    best = candidates[0]
    second = candidates[1]["score"] if len(candidates) > 1 else 0.0
    margin = best["score"] - second

    # Conservative gate before touching Fragrantica page.
    if best["score"] < 0.72 or (second >= 0.65 and margin < 0.12):
        return ambiguous(
            row,
            f"Public search candidate not unique/strong enough; provider={provider}; "
            f"best_score={best['score']:.3f}; second_score={second:.3f}",
        )

    coverage, title, page_error = verify_page(best, inspired)
    # A blocked Fragrantica page is not fatal if the search match is exceptionally strong.
    page_ok = coverage is not None and coverage >= 0.75
    exceptional_search = best["score"] >= 0.90 and (second < 0.70 or margin >= 0.18)
    if not page_ok and not exceptional_search:
        detail = f"page_coverage={coverage}" if coverage is not None else f"page_fetch_error={page_error}"
        return ambiguous(
            row,
            f"Candidate found but verification insufficient; provider={provider}; "
            f"score={best['score']:.3f}; {detail}",
        )

    brand = clean_name_from_slug(best["brand_slug"])
    perfume = clean_name_from_slug(best["perfume_slug"])
    evidence = (
        f"Verified from Shobi inspired_by + public search Fragrantica candidate; "
        f"provider={provider}; score={best['score']:.3f}; margin={margin:.3f}"
    )
    if coverage is not None:
        evidence += f"; Fragrantica title token coverage={coverage:.3f}"
    elif page_error:
        evidence += "; direct page unavailable, exceptional search match used"

    return {
        "prestashop_product_id": str(row.get("prestashop_product_id", "")),
        "shobi_code": row.get("shobi_code", ""),
        "inspired_by": inspired,
        "original_brand": brand,
        "original_perfume": perfume,
        "identity_status": "CONFIRMED",
        "fragrantica_status": "FOUND",
        "fragrantica_id": best["id"],
        "fragrantica_url": best["url"],
        "evidence_note": evidence,
    }


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("expected one Master JSON object on stdin")
    row = json.loads(raw)
    if not isinstance(row, dict):
        raise SystemExit("stdin JSON must be an object")
    result = resolve(row)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
