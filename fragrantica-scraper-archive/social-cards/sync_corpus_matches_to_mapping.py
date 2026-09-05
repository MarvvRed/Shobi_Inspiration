#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAPPING = ROOT / "data" / "shobi-fragrantica-mapping.csv"
CORPUS_MATCH = ROOT / "fragrantica-scraper-archive" / "corpus-match" / "shobi-fragrantica-corpus-match.csv"


def clean(value: str | None) -> str:
    return (value or "").strip()


def main() -> int:
    with MAPPING.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        mapping = list(reader)

    with CORPUS_MATCH.open("r", encoding="utf-8-sig", newline="") as f:
        corpus = list(csv.DictReader(f))

    by_pid: dict[str, dict[str, str]] = {}
    by_code: dict[str, dict[str, str]] = {}
    found = 0
    for row in corpus:
        if clean(row.get("status")).upper() != "FOUND":
            continue
        fid = clean(row.get("fragrantica_id"))
        if not fid.isdigit():
            continue
        found += 1
        pid = clean(row.get("prestashop_product_id"))
        code = clean(row.get("shobi_code"))
        if pid:
            by_pid[pid] = row
        if code:
            by_code[code] = row

    updated = 0
    already_current = 0
    missing = 0
    for row in mapping:
        pid = clean(row.get("prestashop_product_id"))
        code = clean(row.get("shobi_code"))
        match = by_pid.get(pid) if pid else None
        if match is None and code:
            match = by_code.get(code)
        if match is None:
            missing += 1
            continue

        fid = clean(match.get("fragrantica_id"))
        url = clean(match.get("fragrantica_url")) or f"https://www.fragrantica.com/p/{fid}"
        brand = clean(match.get("fragrantica_brand"))
        perfume = clean(match.get("fragrantica_perfume"))

        changed = False
        desired = {
            "identity_status": "CONFIRMED",
            "fragrantica_status": "FOUND",
            "fragrantica_id": fid,
            "fragrantica_url": url,
        }
        if brand:
            desired["original_brand"] = brand
        if perfume:
            desired["original_perfume"] = perfume

        for key, value in desired.items():
            if clean(row.get(key)) != value:
                row[key] = value
                changed = True

        if changed:
            updated += 1
        else:
            already_current += 1

    with MAPPING.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(mapping)

    print("CORPUS -> SOCIAL CARD MAPPING SYNC")
    print(f"corpus_found_with_id={found}")
    print(f"mapping_rows={len(mapping)}")
    print(f"updated={updated}")
    print(f"already_current={already_current}")
    print(f"mapping_rows_without_found_corpus_match={missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
