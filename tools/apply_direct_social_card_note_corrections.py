#!/usr/bin/env python3
"""Apply only complete, direct Social Card note corrections.

This never derives notes from a page, pyramid, candidate, or fuzzy match.  A
row changes only when the original image reader recorded a complete physical
card sequence with exact multi-rendering OCR, matching icon counts, same FID,
and a different visible sequence.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
REPORT = ROOT / "database/audits/direct-social-card-note-corrections.json"

rows = json.loads(DB.read_text(encoding="utf-8-sig"))
audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
by_code = {str(item.get("code") or "").strip().upper(): item for item in audit.get("rows", [])}

corrections = []
for row in rows:
    if str((row.get("validationAudit") or {}).get("status") or "").lower() != "yellow":
        continue
    item = by_code.get(str(row.get("code") or "").strip().upper())
    if not item or item.get("result") != "EXACT_ORDERED_CARD_NOTES_DIFFER":
        continue
    fid = str(row.get("fragranticaId") or "").strip()
    observed = list(item.get("observedNotes") or [])
    if (not fid or str(item.get("fragranticaId") or "") != fid or not item.get("card") or
            not observed or item.get("catalogNotes") != list(row.get("fragranticaSocialCardNotes") or []) or
            item.get("iconCounts") != item.get("labelCounts")):
        continue
    previous = list(row.get("fragranticaSocialCardNotes") or [])
    row["fragranticaSocialCardNotes"] = observed
    row["fragranticaSocialCardStatus"] = "VALIDATED_SOCIAL_CARD"
    corrections.append({
        "code": row.get("code"),
        "fragranticaId": fid,
        "card": item.get("card"),
        "previousNotes": previous,
        "socialCardNotes": observed,
        "proof": item.get("proof"),
        "iconCounts": item.get("iconCounts"),
    })

DB.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
REPORT.write_text(json.dumps({
    "rule": "Only complete exact multi-rendering Social Card readings with matching physical icon counts may replace saved Main Notes.",
    "count": len(corrections),
    "corrections": corrections,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"directSocialCardCorrections": len(corrections)}, indent=2))
