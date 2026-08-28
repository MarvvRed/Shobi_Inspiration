#!/usr/bin/env python3
"""Conservative online resolver for one Shobi Master perfume row.

Reads one Master row as JSON from stdin and prints one reviewed mapping row.
Search failures are treated as transient errors so the worker can retry them;
weak evidence is never promoted to CONFIRMED.
"""
from __future__ import annotations

import csv
import html
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

UA = os.environ.get(
    "SHOBI_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36",
)
HTTP_TIMEOUT = float(os.environ.get("SHOBI_HTTP_TIMEOUT", "25"))
SEARCH_DELAY = float(os.environ.get("SHOBI_SEARCH_DELAY", "0.8"))
MAPPING = Path("data/shobi-fragrantica-mapping.csv")

BAD_INSPIRED = {
    "", "the fragrance notes", "the fragrance notes of", "fragrance notes",
    "the notes", "notes",
}
STOPWORDS = {
    "for", "the", "and", "of", "by", "pour", "eau", "de", "parfum",
    "perfume", "fragrance", "edp", "edt", "men", "women", "unisex",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def toks(s: str):
    return {t for t in norm(s).split() if len(t) >= 2 and t not in STOPWORDS}


def fetch(url: str) -> str:
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    with urlopen(req, timeout=HTTP_TIMEOUT) as r:
        raw = r.read(2_500_000)
    return raw.decode("utf-8", errors="replace")


def unwrap(url: str) -> str:
    url = html.unescape(url)
    if url.startswith("//"):
        url = "https:" + url
    p = urlparse(url)
    qs = parse_qs(p.query)
    for key in ("uddg", "u", "url", "r"):
        if qs.get(key):
            v = unquote(qs[key][0])
            if "fragrantica.com/" in v:
                return v
    return url


def extract_fragrantica_links(page: str):
    out = []
    candidates = []

    for m in re.finditer(r'href=["\']([^"\']+)["\']', page, re.I):
        candidates.append(m.group(1))

    # Search providers sometimes expose the destination only as an encoded URL.
    for m in re.finditer(r'https?(?:%3A|:)(?:%2F|/){2}(?:www\.)?fragrantica\.com(?:%2F|/)[^"\'<>\s&]+', page, re.I):
        candidates.append(unquote(m.group(0)))

    # And sometimes as plain text inside JSON/script blocks.
    for m in re.finditer(r'https?://(?:www\.)?fragrantica\.com/perfume/[^"\'<>\s]+', page, re.I):
        candidates.append(m.group(0))

    for raw in candidates:
        u = unwrap(raw)
        u = unquote(u).replace("\\/", "/")
        m = re.search(r'https?://(?:www\.)?fragrantica\.com/perfume/[^?#"\'<>\s]+', u, re.I)
        if not m:
            continue
        u = m.group(0).rstrip(".,);]")
        if u not in out:
            out.append(u)
    return out


def search_web(query: str):
    providers = [
        ("ddg-html", "https://html.duckduckgo.com/html/?q=" + quote_plus(query)),
        ("ddg-lite", "https://lite.duckduckgo.com/lite/?q=" + quote_plus(query)),
        ("bing-rss", "https://www.bing.com/search?format=rss&q=" + quote_plus(query)),
        ("bing", "https://www.bing.com/search?q=" + quote_plus(query)),
        ("google", "https://www.google.com/search?num=10&q=" + quote_plus(query)),
    ]
    errors = []
    links = []
    used = []
    for name, url in providers:
        try:
            page = fetch(url)
            found = extract_fragrantica_links(page)
            used.append(f"{name}:{len(found)}")
            for item in found:
                if item not in links:
                    links.append(item)
            if len(links) >= 5:
                break
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")
        time.sleep(SEARCH_DELAY)
    return links[:15], ",".join(used) or "none", errors


def parse_fragrantica_url(url: str):
    p = urlparse(url)
    parts = [unquote(x) for x in p.path.split("/") if x]
    if len(parts) < 3 or parts[0].lower() != "perfume":
        return None
    leaf = parts[-1]
    m = re.match(r"(.+)-(\d+)\.html$", leaf, re.I)
    if not m:
        return None
    perfume_slug, fid = m.groups()
    return {
        "url": f"https://www.fragrantica.com{p.path}",
        "id": fid,
        "brand_slug": parts[1].replace("-", " "),
        "perfume_slug": perfume_slug.replace("-", " "),
    }


def prefix_brand_hint(row):
    code = (row.get("shobi_code") or "").strip()
    prefix = (row.get("reference_prefix") or "").strip()
    if not prefix and "-" in code:
        prefix = code.rsplit("-", 1)[-1]
    if not prefix or not MAPPING.exists():
        return ""

    brands = []
    with MAPPING.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if (r.get("identity_status") or "") != "CONFIRMED":
                continue
            rcode = (r.get("shobi_code") or "").strip()
            rprefix = rcode.rsplit("-", 1)[-1] if "-" in rcode else ""
            if rprefix == prefix and (r.get("original_brand") or "").strip():
                brands.append((r.get("original_brand") or "").strip())
    if not brands:
        return ""
    brand, count = Counter(brands).most_common(1)[0]
    return brand if count >= 1 else ""


def candidate_metrics(inspired: str, cand, brand_hint: str):
    target = toks(inspired)
    ctext = cand["brand_slug"] + " " + cand["perfume_slug"]
    ctoks = toks(ctext)
    coverage = len(target & ctoks) / max(1, len(target))
    seq = SequenceMatcher(None, norm(inspired), norm(ctext)).ratio()
    brand_cov = 0.0
    if brand_hint:
        bt = toks(brand_hint)
        brand_cov = len(bt & ctoks) / max(1, len(bt))
    score = 0.64 * coverage + 0.21 * seq + 0.15 * brand_cov
    return score, coverage, brand_cov


def page_title(page: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip()


def verify_page(cand, inspired: str):
    try:
        page = fetch(cand["url"])
        title = page_title(page)
        coverage = len(toks(inspired) & toks(title)) / max(1, len(toks(inspired)))
        return coverage, title, None
    except Exception as e:
        return None, "", f"{type(e).__name__}: {e}"


def clean_slug(s: str) -> str:
    words = s.replace("-", " ").split()
    small = {"de", "du", "des", "di", "da", "of", "the", "and", "for", "by"}
    out = []
    for i, w in enumerate(words):
        if i and w.lower() in small:
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


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
    if norm(inspired) in BAD_INSPIRED or not toks(inspired):
        return ambiguous(row, "broken Shobi inspired_by; profile alone insufficient")

    brand_hint = prefix_brand_hint(row)
    queries = [
        f'site:fragrantica.com/perfume "{inspired}"',
        f'Fragrantica "{inspired}"',
    ]
    all_links = []
    providers = []
    errors = []
    for q in queries:
        links, provider, errs = search_web(q)
        providers.append(provider)
        errors.extend(errs)
        for u in links:
            if u not in all_links:
                all_links.append(u)
        if len(all_links) >= 5:
            break

    candidates = []
    for u in all_links:
        c = parse_fragrantica_url(u)
        if not c:
            continue
        score, coverage, brand_cov = candidate_metrics(inspired, c, brand_hint)
        c.update(score=score, coverage=coverage, brand_cov=brand_cov)
        candidates.append(c)
    candidates.sort(key=lambda x: x["score"], reverse=True)

    if not candidates:
        # This is an infrastructure/search failure, not a perfume identity judgement.
        raise RuntimeError("no Fragrantica candidates returned by search providers; " + "; ".join(errors[-5:]))

    best = candidates[0]
    second = candidates[1]["score"] if len(candidates) > 1 else 0.0
    margin = best["score"] - second

    strong_search = (
        best["coverage"] >= 0.78
        and best["score"] >= 0.68
        and (second < 0.66 or margin >= 0.10)
    )
    if brand_hint:
        strong_search = strong_search and best["brand_cov"] >= 0.50

    if not strong_search:
        return ambiguous(
            row,
            f"online candidate not unique/strong enough; providers={'|'.join(providers)}; "
            f"brand_hint={brand_hint or 'none'}; score={best['score']:.3f}; "
            f"coverage={best['coverage']:.3f}; second={second:.3f}",
        )

    page_cov, title, page_error = verify_page(best, inspired)
    page_ok = page_cov is not None and page_cov >= 0.68
    exceptional = best["coverage"] >= 0.90 and best["score"] >= 0.75 and (second < 0.62 or margin >= 0.15)
    if not page_ok and not exceptional:
        detail = f"page_coverage={page_cov:.3f}" if page_cov is not None else f"page_error={page_error}"
        return ambiguous(row, f"candidate search strong but direct verification insufficient; {detail}")

    evidence = (
        f"Shobi inspired_by + public web Fragrantica candidate; providers={'|'.join(providers)}; "
        f"score={best['score']:.3f}; coverage={best['coverage']:.3f}; margin={margin:.3f}"
    )
    if brand_hint:
        evidence += f"; confirmed-prefix brand hint={brand_hint}"
    if page_cov is not None:
        evidence += f"; page title coverage={page_cov:.3f}"
    else:
        evidence += "; direct page unavailable; exceptional search agreement"

    return {
        "prestashop_product_id": str(row.get("prestashop_product_id", "")),
        "shobi_code": row.get("shobi_code", ""),
        "inspired_by": inspired,
        "original_brand": clean_slug(best["brand_slug"]),
        "original_perfume": clean_slug(best["perfume_slug"]),
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
    print(json.dumps(resolve(row), ensure_ascii=False))


if __name__ == "__main__":
    main()
