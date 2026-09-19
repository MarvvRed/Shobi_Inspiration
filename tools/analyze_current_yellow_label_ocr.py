#!/usr/bin/env python3
"""Non-destructive V2 OCR analysis restricted to current yellow strict-reading rows.

This intentionally writes to a separate report so the historical V2 evidence used by
already-certified green rows is never overwritten.
"""
from __future__ import annotations

import json
import os
from collections import Counter

from analyze_label_ocr_pilot import ROOT, DB, OUT, LEXICON, code, inspect

SITE = ROOT / "database/catalog/catalog_site.json"
REPORT = ROOT / "database/audits/current-yellow-label-ocr-v2.json"


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    site_rows = json.loads(SITE.read_text(encoding="utf-8-sig"))
    audit = json.loads(OUT.read_text(encoding="utf-8"))

    db_by = {code(r.get("code")): r for r in rows}
    site_by = {code(r.get("code")): r for r in site_rows}
    audit_by = {code(r.get("code")): r for r in audit.get("rows", [])}

    target_codes = [
        c for c, s in site_by.items()
        if s.get("validationStatus") == "yellow"
        and c in db_by
        and audit_by.get(c, {}).get("result") == "READING_NOT_STRICT_ENOUGH"
    ]
    target_codes.sort()

    limit = int(os.environ.get("CURRENT_YELLOW_OCR_LIMIT", "0"))
    if limit > 0:
        target_codes = target_codes[:limit]

    lexicon = [x.strip() for x in LEXICON.read_text(encoding="utf-8").splitlines() if x.strip()]
    results = []
    for i, c in enumerate(target_codes, 1):
        result = inspect(db_by[c], lexicon)
        result["currentValidationStatus"] = site_by[c].get("validationStatus")
        result["sourceOrderedAuditResult"] = audit_by[c].get("result")
        results.append(result)
        if i % 20 == 0:
            print(f"processed {i}/{len(target_codes)}", flush=True)

    counts = Counter(r.get("result") for r in results)
    exact_codes = [r["code"] for r in results if r.get("result") == "EXACT_LABEL_SEQUENCE"]
    payload = {
        "mode": "NON_DESTRUCTIVE_CURRENT_YELLOW_PER_LABEL_MULTI_OCR_V2",
        "scope": "catalog_site validationStatus=yellow AND ordered audit=READING_NOT_STRICT_ENOUGH",
        "targets": len(target_codes),
        "counts": dict(sorted(counts.items())),
        "exactCandidateCount": len(exact_codes),
        "exactCandidateCodes": exact_codes,
        "rows": results,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "targets": len(target_codes),
        "counts": payload["counts"],
        "exactCandidateCount": len(exact_codes),
        "output": str(REPORT),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
