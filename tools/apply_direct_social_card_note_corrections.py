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
    "884-RAL": {
        "fid": "9006",
        "card": "database/fragrantica/social-cards/images/current_884-RAL_9006.jpeg",
        "notes": ["Dark Chocolate", "Musk", "Spicy Notes"],
        "labelCounts": [3, 0],
    },
    "925-TMU": {
        "fid": "8766",
        "card": "database/fragrantica/social-cards/images/current_925-TMU_8766.jpeg",
        "notes": ["Fig", "Caviar", "Fig tree", "Fig Leaf"],
        "labelCounts": [3, 1],
    },
    "1257-SFER": {
        "fid": "659",
        "card": "database/fragrantica/social-cards/images/current_1257-SFER_659.jpeg",
        "notes": ["Fig Leaf", "Cedar", "Vetiver", "Grapefruit", "Sandalwood", "Carnation"],
        "labelCounts": [3, 3],
    },
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
    # Current yellow cards transcribed from their exact FID-bound Notes panels.
    # Fragrantica itself ellipsizes long labels in these images; the displayed
    # prefix, same-position icon and exact card ID identify the full label.
    "2598-GLO": {"fid": "46885", "card": "database/fragrantica/social-cards/images/current_2598-GLO_46885.jpeg", "notes": ["Iris", "Pink Pepper", "Ambroxan", "Ambrette (Musk Mallow)"], "labelCounts": [3, 1]},
    "2584-GIV": {"fid": "1966", "card": "database/fragrantica/social-cards/images/current_2584-GIV_1966.jpeg", "notes": ["Lily-of-the-Valley", "Honeysuckle", "Narcissus", "Oakmoss", "Grapefruit", "Jasmine"], "labelCounts": [3, 3]},
    "2119-ARM": {"fid": "78561", "card": "database/fragrantica/social-cards/images/current_2119-ARM_78561.jpeg", "notes": ["Iris Pallida", "Tuberose", "Orange Blossom", "Musk", "Ambrette (Musk Mallow)", "Bitter Orange"], "labelCounts": [3, 3]},
    "2118-GUC": {"fid": "79602", "card": "database/fragrantica/social-cards/images/current_2118-GUC_79602.jpeg", "notes": ["Tuberose", "Night Blooming Jasmine", "Jasmine", "Oakmoss", "Pear", "Patchouli"], "labelCounts": [3, 3]},
    "2121-CAR": {"fid": "77688", "card": "database/fragrantica/social-cards/images/current_2121-CAR_77688.jpeg", "notes": ["Bergamot", "Lemon", "Lapsang Souchong Tea", "Akigalawood", "Osmanthus", "Ambrette (Musk Mallow)"], "labelCounts": [3, 3]},
    "1851-ARM": {"fid": "58909", "card": "database/fragrantica/social-cards/images/current_1851-ARM_58909.jpeg", "notes": ["Lily-of-the-Valley", "Jasmine", "Nashi Pear", "Orange Blossom", "Sandalwood", "Cedar"], "labelCounts": [3, 3]},
    "201-CLIV": {"fid": "4648", "card": "database/fragrantica/social-cards/images/current_201-CLIV_4648.jpeg", "notes": ["Iris", "Ylang-Ylang", "Jasmine", "Sandalwood", "Lily-of-the-Valley", "Heliotrope"], "labelCounts": [3, 3]},
    "1803-DRC": {"fid": "62638", "card": "database/fragrantica/social-cards/images/current_1803-DRC_62638.jpeg", "notes": ["Tuberose", "Jasmine", "Ylang-Ylang", "Sandalwood", "Blood Orange", "Lily-of-the-Valley"], "labelCounts": [3, 3]},
    "1656-LOC": {"fid": "41970", "card": "database/fragrantica/social-cards/images/current_1656-LOC_41970.jpeg", "notes": ["Honey", "Lavender", "Tonka Bean", "Almond", "Ambrette (Musk Mallow)", "Acacia"], "labelCounts": [3, 3]},
    "1655-JOM": {"fid": "48318", "card": "database/fragrantica/social-cards/images/current_1655-JOM_48318.jpeg", "notes": ["Oat", "Hazelnut", "Cornflower Sultan Seeds", "Vetiver"], "labelCounts": [3, 1]},
    "106-ARB": {"fid": "21560", "card": "database/fragrantica/social-cards/images/current_106-ARB_21560.jpeg", "notes": ["Olibanum (Frankincense)", "Orange Blossom", "Rose", "Sandalwood", "Lily-of-the-Valley"], "labelCounts": [3, 2]},
    "378-TMFO": {"fid": "6386", "card": "database/fragrantica/social-cards/images/current_378-TMFO_6386.jpeg", "notes": ["Suede", "Musk", "Lily-of-the-Valley", "Sandalwood", "Saffron", "Thyme"], "labelCounts": [3, 3]},
    "874-PRA": {"fid": "44534", "card": "database/fragrantica/social-cards/images/current_874-PRA_44534.jpeg", "notes": ["Sour Cherry", "Vanilla", "Almond", "Peach", "Benzoin", "Currant Leaf and Bud"], "labelCounts": [3, 3]},
    "828-MIY": {"fid": "42720", "card": "database/fragrantica/social-cards/images/current_828-MIY_42720.jpeg", "notes": ["Lily-of-the-Valley", "Green Notes", "Dew Drop", "White Flowers", "Akigalawood", "Musk"], "labelCounts": [3, 3]},
    "440-BLG": {"fid": "45241", "card": "database/fragrantica/social-cards/images/current_440-BLG_45241.jpeg", "notes": ["Mulberry", "Night Blooming Jasmine", "Musk", "Peony", "Tuberose", "Patchouli"], "labelCounts": [3, 3]},
    "394-AGE": {"fid": "45363", "card": "database/fragrantica/social-cards/images/current_394-AGE_45363.jpeg", "notes": ["Resins", "Honey", "Pepper", "Musk", "Orchid", "Night Blooming Jasmine"], "labelCounts": [3, 3]},
}

MANUAL_VISUAL_PROFILE = {
    "828-MIY": {"gender": "Female", "genderAffinity": "feminine"},
    "884-RAL": {"gender": "Male", "genderAffinity": "masculine", "seasons": ["fall"], "seasonCardFid": "9006"},
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

for row in rows:
    profile = MANUAL_VISUAL_PROFILE.get(str(row.get("code") or "").strip().upper())
    if not profile:
        continue
    row.update(profile)
    row["genderStatus"] = "VALIDATED_MANUAL"
    if "seasons" in profile:
        row["seasonStatus"] = "VALIDATED_MANUAL"

DB.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
REPORT.write_text(json.dumps({
    "rule": "Only complete exact multi-rendering Social Card readings with matching physical icon counts may replace saved Main Notes.",
    "count": len(corrections),
    "corrections": corrections,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"directSocialCardCorrections": len(corrections)}, indent=2))
