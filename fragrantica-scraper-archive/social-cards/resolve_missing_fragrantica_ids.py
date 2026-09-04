#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import os
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
MAPPING = ROOT / "data" / "shobi-fragrantica-mapping.csv"
REPORT = ROOT / "fragrantica-scraper-archive" / "social-cards" / "id-resolution-report.csv"
UA = os.environ.get("SHOBI_USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36")
TIMEOUT = float(os.environ.get("SHOBI_HTTP_TIMEOUT", "20"))
DELAY = float(os.environ.get("FRAGRANTICA_ID_DELAY", "0.20"))
MAX_ROWS = int(os.environ.get("FRAGRANTICA_ID_MAX", "2500"))
STOP = {"for","the","and","of","by","pour","eau","de","parfum","perfume","fragrance","edp","edt","men","women","unisex"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def toks(s: str) -> set[str]:
    return {t for t in norm(s).split() if len(t) >= 2 and t not in STOP}


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    with urlopen(req, timeout=TIMEOUT) as r:
        return r.read(2_000_000).decode("utf-8", errors="replace")


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


def extract(page: str) -> list[str]:
    candidates: list[str] = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', page, re.I):
        candidates.append(m.group(1))
    for m in re.finditer(r'https?(?:%3A|:)(?:%2F|/){2}(?:www\.)?fragrantica\.com(?:%2F|/)[^"\'<>\s&]+', page, re.I):
        candidates.append(unquote(m.group(0)))
    out: list[str] = []
    for raw in candidates:
        u = unquote(unwrap(raw)).replace("\\/", "/")
        m = re.search(r'https?://(?:www\.)?fragrantica\.com/perfume/[^?#"\'<>\s]+', u, re.I)
        if not m:
            continue
        u = m.group(0).rstrip(".,);]")
        if u not in out:
            out.append(u)
    return out


def parse_url(url: str):
    p = urlparse(url)
    parts = [unquote(x) for x in p.path.split("/") if x]
    if len(parts) < 3 or parts[0].lower() != "perfume":
        return None
    m = re.match(r"(.+)-(\d+)\.html$", parts[-1], re.I)
    if not m:
        return None
    perfume_slug, fid = m.groups()
    return {
        "id": fid,
        "url": f"https://www.fragrantica.com{p.path}",
        "brand_slug": parts[1].replace("-", " "),
        "perfume_slug": perfume_slug.replace("-", " "),
    }


def search_links(brand: str, perfume: str) -> tuple[list[str], str]:
    q = f'site:fragrantica.com/perfume "{brand}" "{perfume}"'
    providers = [
        ("bing-rss", "https://www.bing.com/search?format=rss&q=" + quote_plus(q)),
        ("ddg-html", "https://html.duckduckgo.com/html/?q=" + quote_plus(q)),
        ("bing", "https://www.bing.com/search?q=" + quote_plus(q)),
    ]
    links: list[str] = []
    used: list[str] = []
    for name, url in providers:
        try:
            found = extract(fetch_text(url))
            used.append(f"{name}:{len(found)}")
            for u in found:
                if u not in links:
                    links.append(u)
            if len(links) >= 4:
                break
        except Exception as e:
            used.append(f"{name}:ERR:{type(e).__name__}")
        time.sleep(DELAY)
    return links[:12], "|".join(used)


def score_candidate(brand: str, perfume: str, c: dict) -> tuple[float, float, float]:
    bt, pt = toks(brand), toks(perfume)
    cb, cp = toks(c["brand_slug"]), toks(c["perfume_slug"])
    brand_cov = len(bt & cb) / max(1, len(bt))
    perfume_cov = len(pt & cp) / max(1, len(pt))
    seq = SequenceMatcher(None, norm(perfume), norm(c["perfume_slug"])).ratio()
    score = 0.35 * brand_cov + 0.45 * perfume_cov + 0.20 * seq
    return score, brand_cov, perfume_cov


def resolve(brand: str, perfume: str):
    links, providers = search_links(brand, perfume)
    candidates = []
    for u in links:
        c = parse_url(u)
        if not c:
            continue
        score, bc, pc = score_candidate(brand, perfume, c)
        c.update(score=score, brand_cov=bc, perfume_cov=pc)
        candidates.append(c)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    if not candidates:
        return None, providers, "no candidates"
    best = candidates[0]
    second = candidates[1]["score"] if len(candidates) > 1 else 0.0
    margin = best["score"] - second
    # Identity is already confirmed upstream. Here we only accept a very strong URL match.
    ok = best["brand_cov"] >= 0.75 and best["perfume_cov"] >= 0.75 and best["score"] >= 0.78 and (second < 0.72 or margin >= 0.08)
    if not ok:
        return None, providers, f"weak best={best['score']:.3f} brand={best['brand_cov']:.3f} perfume={best['perfume_cov']:.3f} second={second:.3f}"
    return best, providers, f"accepted score={best['score']:.3f} margin={margin:.3f}"


def main() -> int:
    with MAPPING.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    for needed in ("fragrantica_id", "fragrantica_url", "fragrantica_status"):
        if needed not in fieldnames:
            fieldnames.append(needed)

    report_fields = ["prestashop_product_id","shobi_code","original_brand","original_perfume","old_fragrantica_id","new_fragrantica_id","fragrantica_url","result","providers","note"]
    report = []
    attempted = accepted = 0

    for i, row in enumerate(rows, 1):
        identity = (row.get("identity_status") or "").strip().upper()
        existing = (row.get("fragrantica_id") or "").strip()
        brand = (row.get("original_brand") or "").strip()
        perfume = (row.get("original_perfume") or "").strip()
        if identity != "CONFIRMED" or existing.isdigit() or not brand or not perfume:
            continue
        if attempted >= MAX_ROWS:
            break
        attempted += 1
        try:
            best, providers, note = resolve(brand, perfume)
        except Exception as e:
            best, providers, note = None, "", f"{type(e).__name__}: {e}"
        if best:
            row["fragrantica_id"] = best["id"]
            row["fragrantica_url"] = best["url"]
            row["fragrantica_status"] = "FOUND"
            accepted += 1
            result = "FOUND"
            new_id = best["id"]
            url = best["url"]
        else:
            result = "UNRESOLVED"
            new_id = ""
            url = ""
        report.append({
            "prestashop_product_id": row.get("prestashop_product_id", ""),
            "shobi_code": row.get("shobi_code", ""),
            "original_brand": brand,
            "original_perfume": perfume,
            "old_fragrantica_id": existing,
            "new_fragrantica_id": new_id,
            "fragrantica_url": url,
            "result": result,
            "providers": providers,
            "note": note,
        })
        print(f"[{attempted}] {row.get('shobi_code','')} | {brand} | {perfume} -> {result} {new_id}")

    tmp = MAPPING.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(MAPPING)

    with REPORT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=report_fields)
        w.writeheader(); w.writerows(report)

    print("SUMMARY")
    print(f"attempted={attempted}")
    print(f"accepted={accepted}")
    print(f"unresolved={attempted-accepted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
