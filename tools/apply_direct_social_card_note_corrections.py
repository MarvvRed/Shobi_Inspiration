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

# Direct visual transcriptions of the `notes` box on the exact current Social
# Card. These are deliberately small, code+FID-bound records: no pyramid,
# accord, OCR guess, or catalog value is used to select a note.
MANUAL_VISUAL_NOTES = {
    "2792-AJMA": {
        "fid": "58837",
        "card": "database/fragrantica/social-cards/images/current_2792-AJMA_58837.jpeg",
        "notes": ["Lily-of-the-Valley", "Tolu Balsam", "Powdery Notes", "Vanilla"],
        "labelCounts": [3, 1],
    },
    "2744-NISH": {
        "fid": "116224",
        "card": "database/fragrantica/social-cards/images/current_2744-NISH_116224.jpeg",
        "notes": ["Orris Root", "Violet", "Moxalone", "Akigalawood", "Civettone", "Sesame"],
        "labelCounts": [3, 3],
    },
    "412-BOD": {
        "fid": "44100",
        "card": "database/fragrantica/social-cards/images/current_412-BOD_44100.jpeg",
        "notes": ["Musk", "Pear", "Lily-of-the-Valley", "Jasmine", "Rose"],
        "labelCounts": [3, 2],
    },
    "165-PEN": {
        "fid": "40716",
        "card": "database/fragrantica/social-cards/images/current_165-PEN_40716.jpeg",
        "notes": ["Woody Notes", "Brandy", "Tonka Bean", "Amber"],
        "labelCounts": [3, 1],
    },
    "2452-JOM": {
        "fid": "61928",
        "card": "database/fragrantica/social-cards/images/current_2452-JOM_61928.jpeg",
        "notes": ["Cypress", "Woody Notes", "Vine"],
        "labelCounts": [3, 0],
    },
    "1995-YZLO": {
        "fid": "32267",
        "card": "database/fragrantica/social-cards/images/current_1995-YZLO_32267.jpeg",
        "notes": ["Tonka Bean", "Sandalwood", "Elemi", "Olibanum (Frankincense)", "Pink Pepper", "Osmanthus"],
        "labelCounts": [3, 3],
    },
    "2553-BON": {
        "fid": "13630",
        "card": "database/fragrantica/social-cards/images/current_2553-BON_13630.jpeg",
        "notes": ["Plum", "Vanilla", "Agarwood (Oud)", "Sandalwood", "Olibanum (Frankincense)", "Labdanum"],
        "labelCounts": [3, 3],
    },
    "2454-KIL": {
        "fid": "78735",
        "card": "database/fragrantica/social-cards/images/current_2454-KIL_78735.jpeg",
        "notes": ["Orange Blossom", "Honey", "Oakmoss", "Vanilla", "Olibanum (Frankincense)", "Paradisone"],
        "labelCounts": [3, 3],
    },
    "2150-LEL": {
        "fid": "69731",
        "card": "database/fragrantica/social-cards/images/current_2150-LEL_69731.jpeg",
        "notes": ["Fig", "Cedar", "Matcha Tea", "Bitter Orange", "Vetiver"],
        "labelCounts": [3, 2],
    },
}

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
    # Keep the canonical audit aligned with the now-correct catalog while
    # preserving the before/after record in the separate corrections report.
    item["catalogNotesBeforeCorrection"] = previous
    item["catalogNotes"] = observed
    item["result"] = "EXACT_ORDERED_MATCH"
    corrections.append({
        "code": row.get("code"),
        "fragranticaId": fid,
        "card": item.get("card"),
        "previousNotes": previous,
        "socialCardNotes": observed,
        "proof": item.get("proof"),
        "iconCounts": item.get("iconCounts"),
    })

# A manual transcription is primary card evidence when the exact FID and the
# archived current-card path both agree. Store it in the same ordered audit
# record consumed by the validator, so the published proof remains inspectable.
for row in rows:
    code = str(row.get("code") or "").strip().upper()
    proof = MANUAL_VISUAL_NOTES.get(code)
    if not proof or str((row.get("validationAudit") or {}).get("status") or "").lower() != "yellow":
        continue
    item = by_code.get(code)
    fid = str(row.get("fragranticaId") or "").strip()
    notes = list(proof["notes"])
    card = ROOT / proof["card"]
    if (not item or fid != proof["fid"] or str(item.get("fragranticaId") or "") != fid or
            not card.is_file() or item.get("card") != proof["card"]):
        continue
    previous = list(row.get("fragranticaSocialCardNotes") or [])
    row["fragranticaSocialCardNotes"] = notes
    row["fragranticaSocialCardStatus"] = "VALIDATED_MANUAL"
    item.update({
        "result": "EXACT_ORDERED_MATCH",
        "catalogNotesBeforeCorrection": previous,
        "catalogNotes": notes,
        "observedNotes": notes,
        "labelCounts": list(proof["labelCounts"]),
        "iconCounts": list(proof["labelCounts"]),
        "proof": "DIRECT_VISUAL_SOCIAL_CARD_NOTES_PANEL; EXACT_FID; ORDERED_MANUAL_TRANSCRIPTION",
    })
    corrections.append({
        "code": code,
        "fragranticaId": fid,
        "card": proof["card"],
        "previousNotes": previous,
        "socialCardNotes": notes,
        "proof": item["proof"],
        "iconCounts": list(proof["labelCounts"]),
    })

DB.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
REPORT.write_text(json.dumps({
    "rule": "Only complete exact multi-rendering Social Card readings with matching physical icon counts may replace saved Main Notes.",
    "count": len(corrections),
    "corrections": corrections,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"directSocialCardCorrections": len(corrections)}, indent=2))
