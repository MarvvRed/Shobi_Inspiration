#!/usr/bin/env python3
"""Fast search-only Fragrantica candidate collector via public search indexes.

No Firefox, no Fragrantica page requests, no identity mapping writes.
Queries Bing RSS for indexed Fragrantica perfume URLs and stores candidates in
a separate CSV. Intended as the fast first-pass before any slower browser work.
"""
from __future__ import annotations

import csv
import html
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "shobi-master-v1.csv"
OUTPUT = ROOT / "data" / "fragrantica-indexed-search-candidates.csv"
DEFAULT_LIMIT = 10
DELAY = 1.2
TIMEOUT = 15
MAX_CANDIDATES = 5
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
PERFUME_RE = re.compile(r"https?://(?:www\.)?fragrantica\.com/perfume/[^\s\"'<>]+?-(\d+)\.html", re.I)
BROKEN_INSPIRED = {"", "the fragrance notes", "the fragrance notes of", "fragrance notes"}
STOP = {"for", "the", "and", "of", "by", "pour", "eau", "de", "parfum", "perfume", "fragrance", "edp", "edt"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return " ".join(s.split())


def toks(s: str) -> set[str]:
    return {t for t in norm(s).split() if len(t) > 1 and t not in STOP}


def query_for(row: dict[str, str]) -> str:
    inspired = (row.get("inspired_by") or "").strip()
    if norm(inspired) not in BROKEN_INSPIRED:
        return inspired
    return (row.get("shobi_name") or "").strip()


def fetch_bing_rss(term: str) -> str:
    q = f'site:fragrantica.com/perfume "{term}"'
    url = "https://www.bing.com/search?format=rss&q=" + quote_plus(q)
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml,text/xml,*/*"})
    with urlopen(req, timeout=TIMEOUT) as r:
        return r.read(1_500_000).decode("utf-8", errors="replace")


def extract(page: str) -> list[str]:
    page = html.unescape(page).replace("&amp;", "&")
    raw: list[str] = []
    raw.extend(re.findall(r"<link>(.*?)</link>", page, flags=re.I | re.S))
    raw.extend(re.findall(r"https?://(?:www\.)?fragrantica\.com/perfume/[^\s\"'<>]+", page, flags=re.I))
    out: list[str] = []
    for item in raw:
        item = unquote(re.sub(r"<[^>]+>", "", item).strip()).replace("\\/", "/")
        m = PERFUME_RE.search(item)
        if not m:
            continue
        url = m.group(0).split("?", 1)[0].split("#", 1)[0]
        if url not in out:
            out.append(url)
    return out


def label(url: str) -> str:
    p = urlparse(url)
    parts = [unquote(x) for x in p.path.split("/") if x]
    if len(parts) < 3:
        return ""
    perfume = re.sub(r"-\d+\.html$", "", parts[-1], flags=re.I)
    return norm(parts[-2].replace("-", " ") + " " + perfume.replace("-", " "))


def score(query: str, url: str) -> tuple[float, float, float]:
    q = toks(query)
    l = toks(label(url))
    coverage = len(q & l) / max(1, len(q))
    seq = SequenceMatcher(None, norm(query), label(url)).ratio()
    total = coverage * 0.78 + seq * 0.22
    return total, coverage, seq


def done_ids() -> set[str]:
    if not OUTPUT.exists():
        return set()
    with OUTPUT.open("r", encoding="utf-8-sig", newline="") as f:
        return {r.get("prestashop_product_id", "") for r in csv.DictReader(f)}


def append(rows: list[dict[str, str]]) -> None:
    fields = ["prestashop_product_id", "shobi_code", "shobi_name", "inspired_by", "search_query", "search_status", "candidate_rank", "candidate_score", "candidate_coverage", "fragrantica_id", "candidate_url"]
    new = not OUTPUT.exists()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerows(rows)
        f.flush(); os.fsync(f.fileno())


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LIMIT
    done = done_ids()
    with MASTER.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("prestashop_product_id", "") not in done][:limit]
    print(f"Mode: fast indexed search (Bing RSS only)")
    print(f"Rows to search: {len(rows)}")
    print(f"Output: {OUTPUT}")
    started = time.time()
    found_count = 0
    for i, row in enumerate(rows, 1):
        pid = row.get("prestashop_product_id", "")
        q = query_for(row)
        print(f"\n[{i}/{len(rows)}] {pid} | {row.get('shobi_code','')} | {q}")
        base = {"prestashop_product_id": pid, "shobi_code": row.get("shobi_code", ""), "shobi_name": row.get("shobi_name", ""), "inspired_by": row.get("inspired_by", ""), "search_query": q}
        try:
            page = fetch_bing_rss(q)
            links = extract(page)
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
            append([{**base, "search_status": "ERROR", "candidate_rank": "", "candidate_score": "", "candidate_coverage": "", "fragrantica_id": "", "candidate_url": ""}])
            time.sleep(DELAY)
            continue
        ranked = sorted(((score(q, u), u) for u in links), key=lambda x: x[0][0], reverse=True)[:MAX_CANDIDATES]
        if not ranked:
            print("NO_RESULTS")
            append([{**base, "search_status": "NO_RESULTS", "candidate_rank": "", "candidate_score": "", "candidate_coverage": "", "fragrantica_id": "", "candidate_url": ""}])
        else:
            found_count += 1
            out = []
            for rank, ((sc, cov, seq), url) in enumerate(ranked, 1):
                fid = PERFUME_RE.search(url).group(1)
                print(f" {rank}. score={sc:.3f} cov={cov:.3f} id={fid} | {url}")
                out.append({**base, "search_status": "FOUND", "candidate_rank": str(rank), "candidate_score": f"{sc:.4f}", "candidate_coverage": f"{cov:.4f}", "fragrantica_id": fid, "candidate_url": url})
            append(out)
        if i < len(rows):
            time.sleep(DELAY)
    elapsed = time.time() - started
    print(f"\nRESULT: BATCH_COMPLETE | found={found_count}/{len(rows)} | elapsed={elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
