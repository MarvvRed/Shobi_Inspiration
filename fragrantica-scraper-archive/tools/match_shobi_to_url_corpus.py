from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "perfume-database/catalog/shobi-master-v1.csv"
CONFIRMED = ROOT / "perfume-database/confirmed/shobi-fragrantica-mapping.csv"
URLS = ROOT / "fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt"
OUTDIR = ROOT / "fragrantica-scraper-archive/corpus-match"
REPORT = OUTDIR / "shobi-fragrantica-corpus-match.csv"
AMBIGUOUS = OUTDIR / "ambiguous.csv"
UNMATCHED = OUTDIR / "unmatched.csv"
SUMMARY = OUTDIR / "summary.md"
SUMMARY_JSON = OUTDIR / "summary.json"

QUALIFIERS = {
    "absolu", "absolute", "absolue", "elixir", "essence", "extreme", "extrait",
    "intense", "intensely", "intensivo", "intenso", "noir", "parfum", "perfume",
    "rouge", "sport", "edp", "edt", "edc", "limited", "edition", "collector",
}


def norm(text: str) -> str:
    text = unquote((text or "").strip())
    text = text.replace("&", " and ").replace("’", "'")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("'", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def qualifier_tokens(text: str) -> frozenset[str]:
    return frozenset(tok for tok in norm(text).split() if tok in QUALIFIERS)


def code_suffix(code: str) -> str:
    code = (code or "").strip().upper()
    return code.rsplit("-", 1)[-1] if "-" in code else ""


def parse_fragrantica_url(url: str):
    url = url.strip()
    m = re.match(r"^https?://(?:www\.)?fragrantica\.com/perfume/([^/]+)/(.+)-(\d+)\.html$", url, re.I)
    if not m:
        return None
    brand_slug, perfume_slug, fid = m.groups()
    brand = unquote(brand_slug).replace("-", " ").strip()
    perfume = unquote(perfume_slug).replace("-", " ").strip()
    return {
        "brand": brand,
        "perfume": perfume,
        "brand_norm": norm(brand),
        "perfume_norm": norm(perfume),
        "id": fid,
        "url": url,
    }


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def choose_unique(records: list[dict]):
    unique = {}
    for r in records:
        unique[(r["brand_norm"], r["perfume_norm"], r["id"])] = r
    vals = list(unique.values())
    if len(vals) == 1:
        return vals[0]
    return None


def main():
    catalog = read_csv(CATALOG)
    confirmed_rows = read_csv(CONFIRMED) if CONFIRMED.exists() else []

    parsed = []
    invalid_lines = []
    total_lines = 0
    blank_lines = 0
    with URLS.open("r", encoding="utf-8-sig", errors="replace") as fh:
        for lineno, raw in enumerate(fh, 1):
            total_lines += 1
            url = raw.strip()
            if not url:
                blank_lines += 1
                continue
            item = parse_fragrantica_url(url)
            if item:
                item["line"] = lineno
                parsed.append(item)
            else:
                invalid_lines.append((lineno, url))

    by_id = defaultdict(list)
    by_name = defaultdict(list)
    by_brand_name = defaultdict(list)
    by_brand = defaultdict(list)
    for r in parsed:
        by_id[r["id"]].append(r)
        by_name[r["perfume_norm"]].append(r)
        by_brand_name[(r["brand_norm"], r["perfume_norm"])].append(r)
        by_brand[r["brand_norm"]].append(r)

    # Existing confirmed mapping is authoritative for identity and also teaches us
    # the Shobi code-suffix -> original brand relationship. Only unanimous suffixes
    # are used for brand inference.
    confirmed_by_code = {}
    suffix_brands = defaultdict(set)
    suffix_brand_display = defaultdict(Counter)
    for row in confirmed_rows:
        code = (row.get("shobi_code") or "").strip()
        if code:
            confirmed_by_code[code] = row
        suffix = code_suffix(code)
        brand = (row.get("original_brand") or "").strip()
        if suffix and brand:
            nb = norm(brand)
            suffix_brands[suffix].add(nb)
            suffix_brand_display[(suffix, nb)][brand] += 1

    suffix_to_brand = {}
    suffix_to_brand_display = {}
    for suffix, brands in suffix_brands.items():
        if len(brands) == 1:
            nb = next(iter(brands))
            suffix_to_brand[suffix] = nb
            suffix_to_brand_display[suffix] = suffix_brand_display[(suffix, nb)].most_common(1)[0][0]

    results = []
    status_counts = Counter()

    for row in catalog:
        code = (row.get("shobi_code") or "").strip()
        inspired = (row.get("inspired_by") or "").strip()
        nname = norm(inspired)
        suffix = code_suffix(code)
        inferred_brand_norm = suffix_to_brand.get(suffix, "")
        inferred_brand = suffix_to_brand_display.get(suffix, "")

        status = "NOT_FOUND"
        match_type = ""
        score = ""
        candidate_count = 0
        matched = None
        note = ""

        existing = confirmed_by_code.get(code)
        if existing:
            existing_id = (existing.get("fragrantica_id") or "").strip()
            existing_brand = (existing.get("original_brand") or "").strip()
            existing_perfume = (existing.get("original_perfume") or inspired).strip()
            if existing_id and existing_id in by_id:
                choices = by_id[existing_id]
                candidate_count = len(choices)
                matched = choices[0]
                status = "FOUND"
                match_type = "CONFIRMED_ID_IN_CORPUS"
                score = "1.0000"
                note = "Existing confirmed Fragrantica ID occurs in URL corpus"
            else:
                key = (norm(existing_brand), norm(existing_perfume))
                choices = by_brand_name.get(key, [])
                candidate_count = len(choices)
                selected = choose_unique(choices)
                if selected:
                    matched = selected
                    status = "FOUND"
                    match_type = "CONFIRMED_NAME_IN_CORPUS"
                    score = "1.0000"
                    note = "Existing confirmed brand+perfume found in URL corpus"
                elif choices:
                    status = "AMBIGUOUS"
                    match_type = "CONFIRMED_NAME_MULTIPLE_IDS"
                    note = "Confirmed identity maps to multiple Fragrantica IDs in corpus"
                else:
                    status = "MAPPED_NOT_IN_CORPUS"
                    match_type = "CONFIRMED_MAPPING_ONLY"
                    note = "Existing confirmed mapping exists but its ID/name was not found in this URL corpus"
        else:
            # First choice: exact name inside a safely inferred brand.
            if inferred_brand_norm and nname:
                choices = by_brand_name.get((inferred_brand_norm, nname), [])
                candidate_count = len(choices)
                selected = choose_unique(choices)
                if selected:
                    matched = selected
                    status = "FOUND"
                    match_type = "EXACT_BRAND_NAME"
                    score = "1.0000"
                    note = "Brand inferred from an unanimous Shobi code suffix"
                elif choices:
                    status = "AMBIGUOUS"
                    match_type = "EXACT_BRAND_NAME_MULTIPLE_IDS"
                    note = "Exact brand+name exists with multiple Fragrantica IDs"

            # Second choice: exact normalized perfume name globally, only if it points
            # to one single brand/name/id record. This avoids guessing common names.
            if status == "NOT_FOUND" and nname:
                choices = by_name.get(nname, [])
                candidate_count = len(choices)
                selected = choose_unique(choices)
                if selected:
                    matched = selected
                    status = "FOUND"
                    match_type = "EXACT_UNIQUE_NAME"
                    score = "1.0000"
                    note = "Perfume name is unique across the entire URL corpus"
                elif choices:
                    distinct = {(x["brand_norm"], x["id"]) for x in choices}
                    if len(distinct) > 1:
                        status = "AMBIGUOUS"
                        match_type = "EXACT_NAME_MULTIPLE_CANDIDATES"
                        note = "Same perfume name exists under multiple candidates"

            # Conservative fuzzy matching is allowed only inside a safely inferred
            # brand and only when meaningful qualifier tokens agree exactly.
            if status == "NOT_FOUND" and inferred_brand_norm and nname:
                pool = by_brand.get(inferred_brand_norm, [])
                scored = []
                q = qualifier_tokens(inspired)
                for candidate in pool:
                    if qualifier_tokens(candidate["perfume"]) != q:
                        continue
                    ratio = SequenceMatcher(None, nname, candidate["perfume_norm"]).ratio()
                    if ratio >= 0.96:
                        scored.append((ratio, candidate))
                scored.sort(key=lambda x: x[0], reverse=True)
                if scored:
                    best_score, best = scored[0]
                    runner = scored[1][0] if len(scored) > 1 else 0.0
                    near_best = [x for x in scored if best_score - x[0] < 0.03]
                    if best_score >= 0.96 and best_score - runner >= 0.03 and len(near_best) == 1:
                        matched = best
                        status = "FOUND"
                        match_type = "SAFE_FUZZY_SAME_BRAND"
                        score = f"{best_score:.4f}"
                        candidate_count = len(scored)
                        note = "High-similarity name within inferred brand; qualifier tokens preserved"
                    else:
                        status = "AMBIGUOUS"
                        match_type = "FUZZY_MULTIPLE_CANDIDATES"
                        score = f"{best_score:.4f}"
                        candidate_count = len(scored)
                        note = "Fuzzy candidates too close to choose safely"

        out = {
            "prestashop_product_id": row.get("prestashop_product_id", ""),
            "shobi_code": code,
            "inspired_by": inspired,
            "code_suffix": suffix,
            "inferred_brand": inferred_brand,
            "status": status,
            "match_type": match_type,
            "score": score,
            "candidate_count": candidate_count,
            "fragrantica_brand": matched["brand"] if matched else "",
            "fragrantica_perfume": matched["perfume"] if matched else "",
            "fragrantica_id": matched["id"] if matched else "",
            "fragrantica_url": matched["url"] if matched else "",
            "note": note,
        }
        results.append(out)
        status_counts[status] += 1

    fields = [
        "prestashop_product_id", "shobi_code", "inspired_by", "code_suffix",
        "inferred_brand", "status", "match_type", "score", "candidate_count",
        "fragrantica_brand", "fragrantica_perfume", "fragrantica_id",
        "fragrantica_url", "note",
    ]
    write_csv(REPORT, results, fields)
    write_csv(AMBIGUOUS, [r for r in results if r["status"] == "AMBIGUOUS"], fields)
    write_csv(UNMATCHED, [r for r in results if r["status"] in {"NOT_FOUND", "MAPPED_NOT_IN_CORPUS"}], fields)

    unique_urls = len({r["url"] for r in parsed})
    unique_ids = len(by_id)
    duplicate_url_count = len(parsed) - unique_urls
    duplicate_id_extra = len(parsed) - unique_ids
    inferred_suffix_count = len(suffix_to_brand)
    catalog_with_inferred_brand = sum(1 for r in catalog if code_suffix(r.get("shobi_code", "")) in suffix_to_brand)

    summary = {
        "catalog_rows": len(catalog),
        "fragrantica_lines_total": total_lines,
        "fragrantica_blank_lines": blank_lines,
        "fragrantica_valid_url_rows": len(parsed),
        "fragrantica_invalid_url_rows": len(invalid_lines),
        "fragrantica_unique_urls": unique_urls,
        "fragrantica_duplicate_url_rows": duplicate_url_count,
        "fragrantica_unique_ids": unique_ids,
        "fragrantica_extra_rows_sharing_an_id": duplicate_id_extra,
        "confirmed_mapping_rows": len(confirmed_rows),
        "unanimous_code_suffix_brand_mappings": inferred_suffix_count,
        "catalog_rows_with_inferred_brand": catalog_with_inferred_brand,
        "status_counts": dict(status_counts),
        "found_total": status_counts.get("FOUND", 0),
        "ambiguous_total": status_counts.get("AMBIGUOUS", 0),
        "not_found_total": status_counts.get("NOT_FOUND", 0),
        "mapped_not_in_corpus_total": status_counts.get("MAPPED_NOT_IN_CORPUS", 0),
        "invalid_url_examples": [
            {"line": line, "value": value} for line, value in invalid_lines[:20]
        ],
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Shobi ↔ Fragrantica URL corpus match",
        "",
        "This report compares the Shobi master catalog with the archived Fragrantica URL corpus.",
        "It favors precision: exact matches first; fuzzy matching is restricted to an inferred brand and preserves qualifier words such as Intense/Extrait/Parfum.",
        "",
        "## Corpus",
        f"- Shobi catalog rows: **{len(catalog)}**",
        f"- Fragrantica file lines: **{total_lines}**",
        f"- Valid Fragrantica URL rows: **{len(parsed)}**",
        f"- Invalid URL rows: **{len(invalid_lines)}**",
        f"- Unique Fragrantica URLs: **{unique_urls}**",
        f"- Unique Fragrantica IDs: **{unique_ids}**",
        "",
        "## Matching result",
        f"- FOUND: **{status_counts.get('FOUND', 0)}**",
        f"- AMBIGUOUS: **{status_counts.get('AMBIGUOUS', 0)}**",
        f"- NOT_FOUND: **{status_counts.get('NOT_FOUND', 0)}**",
        f"- MAPPED_NOT_IN_CORPUS: **{status_counts.get('MAPPED_NOT_IN_CORPUS', 0)}**",
        "",
        "## Brand inference",
        f"- Existing confirmed mappings: **{len(confirmed_rows)}**",
        f"- Unanimous code-suffix → brand mappings learned: **{inferred_suffix_count}**",
        f"- Shobi catalog rows covered by those brand mappings: **{catalog_with_inferred_brand}**",
        "",
        "## Outputs",
        "- `shobi-fragrantica-corpus-match.csv`: all Shobi rows",
        "- `ambiguous.csv`: rows needing review",
        "- `unmatched.csv`: rows not found in the corpus",
        "- `summary.json`: machine-readable totals",
    ]
    if invalid_lines:
        lines += ["", "## Invalid URL examples"]
        for line, value in invalid_lines[:10]:
            lines.append(f"- line {line}: `{value}`")
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
