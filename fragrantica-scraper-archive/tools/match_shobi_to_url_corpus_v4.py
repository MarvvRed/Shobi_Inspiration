from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import urlparse, unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CATALOG = ROOT / "perfume-database/catalog/shobi-master-v1.csv"
TMP = Path("/tmp/shobi-master-enhanced.csv")
RECOVERY = ROOT / "fragrantica-scraper-archive/corpus-match/source-recovery.csv"
V3 = HERE / "match_shobi_to_url_corpus_v3.py"

BAD_EXACT = {
    "", "the fragrance notes", "the fragrance notes of", "the notes", "the notes of",
    "fragrance notes", "fragrance notes of", "eau de", "no",
}
TRAIL_WORDS = {
    "clone", "clones", "inspired", "inspiration", "similar", "fragrance", "fragrances",
    "perfume", "perfumes", "type",
}


def clean_space(s: str) -> str:
    return " ".join((s or "").replace("\xa0", " ").split()).strip(" -|,.;:")


def looks_bad(s: str) -> bool:
    x = clean_space(s).lower()
    if x in BAD_EXACT:
        return True
    if len(x) < 3:
        return True
    if x in {"citrus fragrance for women and men", "fragrance for women and men"}:
        return True
    return False


def clean_candidate(s: str) -> str:
    s = clean_space(s)
    s = re.sub(r"^(?:the\s+)?(?:fragrance\s+)?notes\s+of\s+", "", s, flags=re.I)
    s = re.sub(r"^the\s+fragrance\s+", "", s, flags=re.I)
    s = re.sub(r"\s+(?:type\s+perfume|type\s+fragrance|woman'?s\s+perfume|women'?s\s+perfume|men'?s\s+perfume)\b.*$", "", s, flags=re.I)
    s = re.sub(r"\s+(?:fragrance\s+for\s+women\s+and\s+men)\b.*$", "", s, flags=re.I)
    return clean_space(s)


def from_description(desc: str) -> str:
    d = clean_space(desc)
    if not d:
        return ""
    patterns = [
        r"inspired\s+by\s+the\s+fragrance\s+notes\s+of\s+(.+?)(?=\.\s*Fragrance|\.\s*$|$)",
        r"inspired\s+by\s+the\s+notes\s+of\s+(.+?)(?=\.\s*Fragrance|\.\s*$|$)",
    ]
    for pat in patterns:
        m = re.search(pat, d, flags=re.I)
        if m:
            c = clean_candidate(m.group(1))
            if not looks_bad(c):
                return c
    # Many older rows are simply "PERFUME - BRAND.Fragrance ..."
    m = re.match(r"(.+?)(?=\.\s*Fragrance\b)", d, flags=re.I)
    if m:
        c = clean_candidate(re.sub(r"^\s*[A-Z0-9-]+\s+(?:W|M|N|EL|WP|AR)?\s*", "", m.group(1), flags=re.I))
        if not looks_bad(c) and not c.lower().startswith("fragrance "):
            return c
    return ""


def from_url(url: str) -> str:
    if not url:
        return ""
    slug = unquote(urlparse(url).path.rstrip("/").split("/")[-1]).replace("-", " ")
    slug = clean_space(slug)
    if not slug:
        return ""
    toks = slug.split()
    # Product pages often end in SEO words rather than perfume identity.
    while toks and toks[-1].lower() in TRAIL_WORDS:
        toks.pop()
    # remove pairs such as "inspired fragrance" / "similar fragrance"
    while len(toks) >= 2 and toks[-2].lower() in TRAIL_WORDS and toks[-1].lower() in TRAIL_WORDS:
        toks = toks[:-2]
    c = clean_candidate(" ".join(toks))
    # A slug that is only the Shobi code/category gives us no identity.
    if re.fullmatch(r"\d+\s+[a-z0-9]+(?:\s+[wmen]+)?", c, flags=re.I):
        return ""
    return "" if looks_bad(c) else c


def quality(s: str) -> int:
    s = clean_candidate(s)
    if looks_bad(s):
        return -100
    low = s.lower()
    score = min(len(s), 80)
    if "fragrance notes" in low: score -= 60
    if "fresh spicy" in low or "woody" in low or "floral" in low: score -= 30
    if len(s.split()) > 16: score -= 40
    return score


def derive(row: dict):
    original = clean_candidate(row.get("inspired_by", ""))
    desc = from_description(row.get("official_description", ""))
    url = from_url(row.get("url", ""))
    candidates = [(original, "catalog"), (desc, "description"), (url, "url_slug")]
    # Prefer explicit catalog text when it is meaningful; otherwise recover from description/URL.
    if not looks_bad(original) and quality(original) >= 0:
        # Still allow description to replace obvious generic/truncated catalogue phrases.
        if original.lower().startswith(("the notes of ", "the fragrance ")) and quality(desc) > quality(original):
            return desc, "description"
        return original, "catalog"
    best, src = max(candidates, key=lambda x: quality(x[0]))
    return (best, src) if quality(best) >= 0 else (original, "unrecovered")


def main():
    with CATALOG.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)

    recovered = []
    for row in rows:
        old = row.get("inspired_by", "") or ""
        new, src = derive(row)
        if new != clean_candidate(old):
            recovered.append({
                "prestashop_product_id": row.get("prestashop_product_id", ""),
                "shobi_code": row.get("shobi_code", ""),
                "old_inspired_by": old,
                "recovered_inspired_by": new,
                "source": src,
                "url": row.get("url", ""),
            })
        row["inspired_by"] = new

    with TMP.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    RECOVERY.parent.mkdir(parents=True, exist_ok=True)
    with RECOVERY.open("w", encoding="utf-8-sig", newline="") as f:
        fields2 = ["prestashop_product_id","shobi_code","old_inspired_by","recovered_inspired_by","source","url"]
        w = csv.DictWriter(f, fieldnames=fields2); w.writeheader(); w.writerows(recovered)

    code = V3.read_text(encoding="utf-8")
    code = code.replace(
        'CATALOG = ROOT / "perfume-database/catalog/shobi-master-v1.csv"',
        'CATALOG = Path("/tmp/shobi-master-enhanced.csv")'
    )
    ns = {"__name__": "__main__", "__file__": str(V3)}
    exec(compile(code, str(V3), "exec"), ns, ns)


if __name__ == "__main__":
    main()
