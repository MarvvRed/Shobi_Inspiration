#!/usr/bin/env python3
"""Record direct gender evidence from the exact Fragrantica ID pages.

The identity and card FID are already exact. This task binds the displayed
Fragrantica gender classification to the same canonical URL; it never changes
an identity, FID or the Social Card note sequence.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
REPORT = ROOT / "database/audits/new-official-shobi-gender-evidence-2026-09-30.json"

EXPECTED = {
    "2850-ETLR": ("unisex", "83820"), "2851-LOUM": ("unisex", "83054"),
    "2852-MAN": ("unisex", "104247"), "2853-MEM": ("unisex", "79533"),
    "2855-AMG": ("feminine", "126673"), "2856-TMFO": ("unisex", "125742"),
    "2857-KAY": ("unisex", "118624"), "2858-CRIVEL": ("unisex", "131410"),
    "2859-DRC": ("unisex", "132884"), "2860-OBVI": ("unisex", "108057"),
    "2861-AKR": ("unisex", "51706"), "2862-GIA": ("unisex", "128151"),
    "2863-FRAG": ("unisex", "91981"), "2864-GISS": ("unisex", "127864"),
    "2865-IN": ("unisex", "129499"), "2866-KAY": ("feminine", "127456"),
    "2867-LAT": ("unisex", "84302"), "2868-LEL": ("unisex", "95922"),
    "2869-MARG": ("unisex", "129373"), "2870-MAN": ("unisex", "128865"),
    "2871-NARO": ("unisex", "103933"),
}


def main() -> None:
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    found = {}
    for row in rows:
        code = str(row.get("code") or "").strip().upper()
        if code not in EXPECTED:
            continue
        affinity, fid = EXPECTED[code]
        if str(row.get("fragranticaId") or "") != fid:
            raise SystemExit(f"FID regression for {code}")
        url = str(row.get("fragranticaUrl") or "")
        if not url.endswith(f"-{fid}.html"):
            raise SystemExit(f"URL/FID mismatch for {code}")
        row["genderAffinity"] = affinity
        row["gender"] = "Unisex" if affinity == "unisex" else "Women"
        row["genderStatus"] = "VALIDATED_MANUAL"
        row["genderSource"] = url
        found[code] = {"fragranticaId": fid, "gender": row["gender"], "source": url}
    if set(found) != set(EXPECTED):
        raise SystemExit(f"Missing new gender targets: {sorted(set(EXPECTED) - set(found))}")
    DB.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps({"rule": "Exact Fragrantica ID page title determines gender only after URL/FID identity validation.", "rows": found}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"gender evidence recorded for {len(found)} rows")


if __name__ == "__main__":
    main()
