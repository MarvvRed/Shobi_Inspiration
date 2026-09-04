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
TIMEOUT = float(os.environ.get("SHOBI_HTTP_TIMEOUT", "7"))
DELAY = float(os.environ.get("FRAGRANTICA_ID_DELAY", "0.15"))
MAX_ROWS = int(os.environ.get("FRAGRANTICA_ID_MAX", "250"))
CHECKPOINT_EVERY = max(1, int(os.environ.get("FRAGRANTICA_ID_CHECKPOINT_EVERY", "10")))
RETRY_UNRESOLVED = os.environ.get("FRAGRANTICA_RETRY_UNRESOLVED", "1").strip().lower() not in {"0", "false", "no"}
STOP = {
    "for", "the", "and", "of", "by", "pour", "eau", "de", "parfum", "perfume",
    "perfumes", "fragrance", "fragrances", "edp", "edt", "men", "women", "unisex",
    "type", "spray", "edition", "intense", "extract", "extrait"
}
REPORT_FIELDS = [
    "prestashop_product_id", "shobi_code", "original_brand", "original_perfume",
    "old_fragrantica_id", "new_fragrantica_id", "fragrantica_url", "result", "providers", "note"
]

# Search providers can become slow or rate-limited mid-run. After repeated failures we stop
# using the sick provider instead of burning ~20 seconds on every remaining perfume.
PROVIDER_FAILURES: dict[str, int] = {}
DISABLED_PROVIDERS: set[str] = set()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def clean_perfume_name(perfume: str, brand: str = "") -> str:
    """Remove catalogue noise while keeping the distinctive perfume name."""
    s = unicodedata.normalize("NFKC", perfume or "")
    s = re.sub(r"\([^)]*\b(?:19|20)\d{2}\b[^)]*\)", " ", s, flags=re.I)
    s = re.sub(r"\b(?:eau\s+de\s+parfum|eau\s+de\s+toilette|eau\s+de\s+cologne|parfum|perfume|fragrance|edp|edt)\b", " ", s, flags=re.I)
    s = re.sub(r"\b(?:for\s+(?:men|women)|pour\s+homme|pour\s+femme|type)\b", " ", s, flags=re.I)
    s = re.sub(r"\b(?:19|20)\d{2}\b", " ", s)
    s = re.sub(r"[-_/|]+", " ", s)
    s = " ".join(s.split()).strip(" -–—,.;:")

    # Some source names redundantly append the brand: "Khamrah Qahwa Lattafa Perfumes".
    nb = norm(brand)
    ns = norm(s)
    if nb and ns:
        brand_words = nb.split()
        words = ns.split()
        if len(words) > len(brand_words) and words[-len(brand_words):] == brand_words:
            words = words[:-len(brand_words)]
            s = " ".join(words)
        elif len(brand_words) == 1 and len(words) > 1 and words[-1] == brand_words[0]:
            s = " ".join(words[:-1])
    return s.strip() or perfume.strip()


def toks(s: str) -> set[str]:
    return {t for t in norm(s).split() if len(t) >= 2 and t not in STOP}


def fetch_text(url: str) -> str:
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
    })
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


def query_variants(brand: str, perfume: str) -> list[str]:
    clean = clean_perfume_name(perfume, brand)
    variants = [
        f'site:fragrantica.com/perfume "{brand}" "{clean}"',
        f'site:fragrantica.com/perfume {brand} {clean}',
    ]
    # If cleaning materially changed the source name, keep one original-name query too.
    if norm(clean) != norm(perfume):
        variants.append(f'site:fragrantica.com/perfume "{brand}" "{perfume}"')
    # Short, distinctive token query helps with awkward punctuation/slugs.
    core = [t for t in norm(clean).split() if t not in STOP]
    if core:
        variants.append(f'site:fragrantica.com/perfume {brand} ' + " ".join(core[:6]))
    out: list[str] = []
    for q in variants:
        q = " ".join(q.split())
        if q not in out:
            out.append(q)
    return out[:4]


def provider_urls(query: str) -> list[tuple[str, str]]:
    return [
        ("bing-rss", "https://www.bing.com/search?format=rss&q=" + quote_plus(query)),
        ("ddg-html", "https://html.duckduckgo.com/html/?q=" + quote_plus(query)),
        ("bing", "https://www.bing.com/search?q=" + quote_plus(query)),
    ]


def search_links(brand: str, perfume: str) -> tuple[list[str], str]:
    links: list[str] = []
    used: list[str] = []
    queries = query_variants(brand, perfume)

    for qi, q in enumerate(queries, start=1):
        for name, url in provider_urls(q):
            if name in DISABLED_PROVIDERS:
                continue
            try:
                started = time.monotonic()
                found = extract(fetch_text(url))
                elapsed = time.monotonic() - started
                used.append(f"q{qi}:{name}:{len(found)}:{elapsed:.1f}s")
                PROVIDER_FAILURES[name] = 0
                for u in found:
                    if u not in links:
                        links.append(u)
                # Enough candidates to score; avoid needless requests.
                if len(links) >= 6:
                    return links[:16], "|".join(used)
            except Exception as e:
                PROVIDER_FAILURES[name] = PROVIDER_FAILURES.get(name, 0) + 1
                used.append(f"q{qi}:{name}:ERR:{type(e).__name__}")
                if PROVIDER_FAILURES[name] >= 3:
                    DISABLED_PROVIDERS.add(name)
                    used.append(f"{name}:DISABLED")
            time.sleep(DELAY)

        if links and qi >= 2:
            break

    return links[:16], "|".join(used)


def score_candidate(brand: str, perfume: str, c: dict) -> tuple[float, float, float, float]:
    clean = clean_perfume_name(perfume, brand)
    bt, pt = toks(brand), toks(clean)
    cb, cp = toks(c["brand_slug"]), toks(c["perfume_slug"])
    brand_cov = len(bt & cb) / max(1, len(bt))
    perfume_cov = len(pt & cp) / max(1, len(pt))
    seq = SequenceMatcher(None, norm(clean), norm(c["perfume_slug"])).ratio()
    reverse_cov = len(pt & cp) / max(1, len(cp))
    score = 0.34 * brand_cov + 0.43 * perfume_cov + 0.18 * seq + 0.05 * reverse_cov
    return score, brand_cov, perfume_cov, seq


def resolve(brand: str, perfume: str):
    links, providers = search_links(brand, perfume)
    candidates = []
    for u in links:
        c = parse_url(u)
        if not c:
            continue
        score, bc, pc, seq = score_candidate(brand, perfume, c)
        c.update(score=score, brand_cov=bc, perfume_cov=pc, seq=seq)
        candidates.append(c)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    if not candidates:
        return None, providers, "no candidates"

    best = candidates[0]
    second = candidates[1]["score"] if len(candidates) > 1 else 0.0
    margin = best["score"] - second
    clean = clean_perfume_name(perfume, brand)
    exact_name = norm(clean) == norm(best["perfume_slug"])

    # Keep acceptance conservative, but tolerate catalogue suffixes and Fragrantica slug differences.
    ok = (
        best["brand_cov"] >= 0.66
        and best["perfume_cov"] >= 0.60
        and best["score"] >= 0.70
        and (exact_name or second < 0.68 or margin >= 0.055 or best["score"] >= 0.86)
    )
    if not ok:
        return None, providers, (
            f"weak best={best['score']:.3f} brand={best['brand_cov']:.3f} "
            f"perfume={best['perfume_cov']:.3f} seq={best['seq']:.3f} second={second:.3f}"
        )
    return best, providers, f"accepted score={best['score']:.3f} margin={margin:.3f} clean={clean!r}"


def row_key(row: dict) -> str:
    product_id = (row.get("prestashop_product_id") or "").strip()
    if product_id:
        return f"id:{product_id}"
    code = norm(row.get("shobi_code") or "")
    brand = norm(row.get("original_brand") or "")
    perfume = norm(row.get("original_perfume") or "")
    return f"fallback:{code}|{brand}|{perfume}"


def load_report() -> list[dict]:
    if not REPORT.exists():
        return []
    try:
        with REPORT.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"WARNING: could not load existing report: {type(e).__name__}: {e}")
        return []


def save_checkpoint(rows: list[dict], fieldnames: list[str], report: list[dict]) -> None:
    tmp = MAPPING.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(MAPPING)

    report_tmp = REPORT.with_suffix(".csv.tmp")
    with report_tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(report)
    report_tmp.replace(REPORT)


def main() -> int:
    with MAPPING.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    for needed in ("fragrantica_id", "fragrantica_url", "fragrantica_status"):
        if needed not in fieldnames:
            fieldnames.append(needed)

    report = load_report()
    found_keys = {
        row_key(r) for r in report
        if (r.get("result") or "").strip().upper() == "FOUND"
    }
    unresolved_keys = {
        row_key(r) for r in report
        if (r.get("result") or "").strip().upper() == "UNRESOLVED"
    }
    attempted_keys = set(found_keys)
    if not RETRY_UNRESOLVED:
        attempted_keys.update(unresolved_keys)

    attempted = accepted = skipped_previous = 0

    for row in rows:
        identity = (row.get("identity_status") or "").strip().upper()
        existing = (row.get("fragrantica_id") or "").strip()
        brand = (row.get("original_brand") or "").strip()
        perfume = (row.get("original_perfume") or "").strip()

        if identity != "CONFIRMED" or existing.isdigit() or not brand or not perfume:
            continue

        key = row_key(row)
        if key in attempted_keys:
            skipped_previous += 1
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
            row["fragrantica_status"] = "UNRESOLVED"
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
        attempted_keys.add(key)
        print(
            f"[{attempted}] {row.get('shobi_code','')} | {brand} | {perfume} -> {result} {new_id} | {note}",
            flush=True,
        )

        if attempted % CHECKPOINT_EVERY == 0:
            save_checkpoint(rows, fieldnames, report)
            print(f"CHECKPOINT attempted={attempted} accepted={accepted} report_rows={len(report)}", flush=True)

    save_checkpoint(rows, fieldnames, report)

    remaining = 0
    for row in rows:
        identity = (row.get("identity_status") or "").strip().upper()
        existing = (row.get("fragrantica_id") or "").strip()
        brand = (row.get("original_brand") or "").strip()
        perfume = (row.get("original_perfume") or "").strip()
        if identity == "CONFIRMED" and not existing.isdigit() and brand and perfume and row_key(row) not in attempted_keys:
            remaining += 1

    print("SUMMARY")
    print(f"attempted={attempted}")
    print(f"accepted={accepted}")
    print(f"unresolved={attempted-accepted}")
    print(f"skipped_previous={skipped_previous}")
    print(f"remaining_unattempted={remaining}")
    print(f"disabled_providers={','.join(sorted(DISABLED_PROVIDERS)) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
