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
GENERIC_BRAND_WORDS = {
    "by", "parfum", "parfums", "perfume", "perfumes", "fragrance", "fragrances",
    "parfumeur", "parfumerie", "parfumer", "createur", "prive", "prives",
}


def norm(text: str) -> str:
    text = unquote((text or "").strip())
    text = text.replace("&", " and ").replace("’", "'").replace("®", "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("'", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def code_suffix(code: str) -> str:
    code = (code or "").strip().upper()
    return code.rsplit("-", 1)[-1] if "-" in code else ""


def brand_core(text: str) -> str:
    return " ".join(t for t in norm(text).split() if t not in GENERIC_BRAND_WORDS)


def qualifier_tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in norm(text).split() if t in QUALIFIERS)


def parse_url(url: str):
    m = re.match(r"^https?://(?:www\.)?fragrantica\.com/perfume/([^/]+)/(.+)-(\d+)\.html$", url.strip(), re.I)
    if not m:
        return None
    bslug, pslug, fid = m.groups()
    brand = unquote(bslug).replace("-", " ").strip()
    perfume = unquote(pslug).replace("-", " ").strip()
    return {"brand": brand, "perfume": perfume, "brand_norm": norm(brand), "brand_core": brand_core(brand), "perfume_norm": norm(perfume), "id": fid, "url": url.strip()}


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def unique_record(records: list[dict]):
    vals = list({(r["brand_norm"], r["perfume_norm"], r["id"]): r for r in records}.values())
    return vals[0] if len(vals) == 1 else None


def name_variants(name: str, brand: str = "") -> list[str]:
    n = norm(name)
    vals = {n} if n else set()
    if not n or not brand:
        return sorted(vals, key=len)
    forms = {norm(brand), brand_core(brand)} - {""}
    for form in sorted(forms, key=len, reverse=True):
        if n.endswith(" " + form): vals.add(n[:-(len(form)+1)].strip())
        if n.startswith(form + " "): vals.add(n[len(form)+1:].strip())
    return sorted((x for x in vals if x), key=len)


def main():
    catalog = read_csv(CATALOG)
    confirmed_rows = read_csv(CONFIRMED) if CONFIRMED.exists() else []
    parsed, invalid_lines = [], []
    total_lines = blank_lines = 0
    with URLS.open("r", encoding="utf-8-sig", errors="replace") as fh:
        for lineno, raw in enumerate(fh, 1):
            total_lines += 1
            url = raw.strip()
            if not url:
                blank_lines += 1; continue
            rec = parse_url(url)
            if rec:
                rec["line"] = lineno; parsed.append(rec)
            else:
                invalid_lines.append((lineno, url))

    by_id, by_name, by_brand, by_brand_name, by_combined = (defaultdict(list) for _ in range(5))
    for r in parsed:
        by_id[r["id"]].append(r); by_name[r["perfume_norm"]].append(r); by_brand[r["brand_norm"]].append(r)
        by_brand_name[(r["brand_norm"], r["perfume_norm"])].append(r)
        combos = {norm(r["perfume"]+" "+r["brand"]), norm(r["brand"]+" "+r["perfume"])}
        if r["brand_core"]:
            combos |= {norm(r["perfume"]+" "+r["brand_core"]), norm(r["brand_core"]+" "+r["perfume"])}
        for c in combos:
            if c: by_combined[c].append(r)

    confirmed_by_code = {}
    suffix_votes = defaultdict(Counter)
    brand_display = defaultdict(Counter)
    for row in confirmed_rows:
        code = (row.get("shobi_code") or "").strip(); brand = (row.get("original_brand") or "").strip()
        if code: confirmed_by_code[code] = row
        suffix = code_suffix(code)
        if suffix and brand:
            nb = norm(brand); suffix_votes[suffix][nb] += 1000; brand_display[nb][brand] += 1

    learned_exact_rows = 0
    for row in catalog:
        inspired = (row.get("inspired_by") or "").strip(); code = (row.get("shobi_code") or "").strip()
        selected = unique_record(by_combined.get(norm(inspired), []))
        if selected:
            suffix = code_suffix(code)
            if suffix:
                suffix_votes[suffix][selected["brand_norm"]] += 1
                brand_display[selected["brand_norm"]][selected["brand"]] += 1
                learned_exact_rows += 1

    suffix_to_brand, suffix_to_display = {}, {}
    for suffix, votes in suffix_votes.items():
        ranked = votes.most_common()
        if not ranked: continue
        top_brand, top_score = ranked[0]; second = ranked[1][1] if len(ranked) > 1 else 0
        if top_score >= 1000 or second == 0:
            suffix_to_brand[suffix] = top_brand
            suffix_to_display[suffix] = brand_display[top_brand].most_common(1)[0][0]

    results, status_counts, type_counts = [], Counter(), Counter()
    for row in catalog:
        code = (row.get("shobi_code") or "").strip(); inspired = (row.get("inspired_by") or "").strip(); nraw = norm(inspired)
        suffix = code_suffix(code); ib = suffix_to_brand.get(suffix, ""); ib_display = suffix_to_display.get(suffix, "")
        status, match_type, score, note = "NOT_FOUND", "", "", ""; candidate_count = 0; matched = None
        existing = confirmed_by_code.get(code)
        if existing:
            eid = (existing.get("fragrantica_id") or "").strip(); ebrand = (existing.get("original_brand") or "").strip(); ename = (existing.get("original_perfume") or inspired).strip()
            if eid and eid in by_id:
                choices = by_id[eid]; matched = choices[0]; candidate_count = len(choices); status, match_type, score = "FOUND", "CONFIRMED_ID_IN_CORPUS", "1.0000"
            else:
                choices = by_brand_name.get((norm(ebrand), norm(ename)), []); selected = unique_record(choices); candidate_count = len(choices)
                if selected: matched = selected; status, match_type, score = "FOUND", "CONFIRMED_NAME_IN_CORPUS", "1.0000"
                elif choices: status, match_type = "AMBIGUOUS", "CONFIRMED_NAME_MULTIPLE_IDS"
                else: status, match_type = "MAPPED_NOT_IN_CORPUS", "CONFIRMED_MAPPING_ONLY"
        else:
            choices = by_combined.get(nraw, []) if nraw else []; selected = unique_record(choices); candidate_count = len(choices)
            if selected:
                matched = selected; status, match_type, score = "FOUND", "EXACT_PERFUME_BRAND_TEXT", "1.0000"
            elif choices:
                status, match_type = "AMBIGUOUS", "EXACT_COMBINED_MULTIPLE_IDS"

            variants = name_variants(inspired, ib_display) if ib else ([nraw] if nraw else [])
            if status == "NOT_FOUND" and ib:
                choices = [x for v in variants for x in by_brand_name.get((ib, v), [])]; selected = unique_record(choices); candidate_count = len(choices)
                if selected:
                    matched = selected; status, match_type, score = "FOUND", "EXACT_BRAND_CLEAN_NAME", "1.0000"
                elif choices:
                    status, match_type = "AMBIGUOUS", "EXACT_BRAND_NAME_MULTIPLE_IDS"

            if status == "NOT_FOUND":
                choices = [x for v in variants for x in by_name.get(v, [])]; selected = unique_record(choices); candidate_count = len(choices)
                if selected:
                    matched = selected; status, match_type, score = "FOUND", "EXACT_UNIQUE_NAME", "1.0000"
                elif choices and len({(x["brand_norm"], x["id"]) for x in choices}) > 1:
                    status, match_type = "AMBIGUOUS", "EXACT_NAME_MULTIPLE_CANDIDATES"

            if status == "NOT_FOUND" and ib and variants:
                scored = []
                for cand in by_brand.get(ib, []):
                    best = 0.0
                    for v in variants:
                        if qualifier_tokens(v) != qualifier_tokens(cand["perfume_norm"]): continue
                        best = max(best, SequenceMatcher(None, v, cand["perfume_norm"]).ratio())
                    if best >= 0.92: scored.append((best, cand))
                scored.sort(key=lambda x:x[0], reverse=True)
                if scored:
                    best_score, best = scored[0]; runner = scored[1][0] if len(scored)>1 else 0.0; near = [x for x in scored if best_score-x[0] < 0.025]; candidate_count = len(scored)
                    if best_score-runner >= 0.025 and len(near) == 1:
                        matched = best; status, match_type, score = "FOUND", "SAFE_FUZZY_SAME_BRAND", f"{best_score:.4f}"
                    else:
                        status, match_type, score = "AMBIGUOUS", "FUZZY_MULTIPLE_CANDIDATES", f"{best_score:.4f}"

        out = {
            "prestashop_product_id": row.get("prestashop_product_id", ""), "shobi_code": code, "inspired_by": inspired,
            "code_suffix": suffix, "inferred_brand": ib_display, "status": status, "match_type": match_type, "score": score,
            "candidate_count": candidate_count, "fragrantica_brand": matched["brand"] if matched else "",
            "fragrantica_perfume": matched["perfume"] if matched else "", "fragrantica_id": matched["id"] if matched else "",
            "fragrantica_url": matched["url"] if matched else "", "note": note,
        }
        results.append(out); status_counts[status] += 1; type_counts[match_type or "NONE"] += 1

    fields = ["prestashop_product_id","shobi_code","inspired_by","code_suffix","inferred_brand","status","match_type","score","candidate_count","fragrantica_brand","fragrantica_perfume","fragrantica_id","fragrantica_url","note"]
    write_csv(REPORT, results, fields); write_csv(AMBIGUOUS, [r for r in results if r["status"]=="AMBIGUOUS"], fields); write_csv(UNMATCHED, [r for r in results if r["status"] in {"NOT_FOUND","MAPPED_NOT_IN_CORPUS"}], fields)

    unique_urls = len({r["url"] for r in parsed}); unique_ids = len(by_id)
    summary = {
        "catalog_rows": len(catalog), "fragrantica_lines_total": total_lines, "fragrantica_blank_lines": blank_lines,
        "fragrantica_valid_url_rows": len(parsed), "fragrantica_invalid_url_rows": len(invalid_lines), "fragrantica_unique_urls": unique_urls,
        "fragrantica_duplicate_url_rows": len(parsed)-unique_urls, "fragrantica_unique_ids": unique_ids, "fragrantica_extra_rows_sharing_an_id": len(parsed)-unique_ids,
        "confirmed_mapping_rows": len(confirmed_rows), "learned_exact_combined_rows": learned_exact_rows, "safe_code_suffix_brand_mappings": len(suffix_to_brand),
        "catalog_rows_with_inferred_brand": sum(1 for r in catalog if code_suffix(r.get("shobi_code", "")) in suffix_to_brand),
        "status_counts": dict(status_counts), "match_type_counts": dict(type_counts), "found_total": status_counts.get("FOUND",0),
        "ambiguous_total": status_counts.get("AMBIGUOUS",0), "not_found_total": status_counts.get("NOT_FOUND",0), "mapped_not_in_corpus_total": status_counts.get("MAPPED_NOT_IN_CORPUS",0),
        "invalid_url_examples": [{"line":n,"value":v} for n,v in invalid_lines[:20]],
    }
    OUTDIR.mkdir(parents=True, exist_ok=True); SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    SUMMARY.write_text("# Shobi ↔ Fragrantica URL corpus match\n\n" + f"FOUND: **{summary['found_total']}**\n\nAMBIGUOUS: **{summary['ambiguous_total']}**\n\nNOT_FOUND: **{summary['not_found_total']}**\n\nMAPPED_NOT_IN_CORPUS: **{summary['mapped_not_in_corpus_total']}**\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__": main()
