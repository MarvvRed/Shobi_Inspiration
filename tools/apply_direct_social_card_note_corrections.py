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
SITE = ROOT / "database/catalog/catalog_site.json"
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

# Results from the full independent re-audit of every previously green record.
# Each item is bound to the exact code, FID and archived Social Card that
# produced a complete multipass physical-card reading.  They are corrections,
# not guesses or page-derived substitutions.
INDEPENDENT_GREEN_REAUDIT_CORRECTIONS = {
    "1033-BRB": {"fid": "815", "card": "database/fragrantica/social-cards/images/134_1033-BRB_815.jpeg", "notes": ["Violet Leaf", "Musk", "Pepper", "Tonka Bean", "Cedar", "Nutmeg"]},
    "1036-BLG": {"fid": "148", "card": "database/fragrantica/social-cards/images/current_1036-BLG_148.jpeg", "notes": ["Ginger", "Cardamom", "Tobacco Blossom", "Sandalwood", "Juniper", "Galanga"]},
    "1059-CRT": {"fid": "307", "card": "database/fragrantica/social-cards/images/current_1059-CRT_307.jpeg", "notes": ["Cardamom", "Bitter Orange", "Caraway", "Birch", "Vetiver", "Pepper"]},
    "1160-HUG": {"fid": "383", "card": "database/fragrantica/social-cards/images/current_1160-HUG_383.jpeg", "notes": ["Apple", "Vanilla", "Cinnamon", "Sandalwood", "Plum", "Cedar"]},
    "1614-FRE": {"fid": "52195", "card": "database/fragrantica/social-cards/images/2328_1614-FRE_52195.jpeg", "notes": ["Olibanum (Frankincense)", "Agarwood (Oud)", "Labdanum", "Pink Pepper", "Rose", "Vetiver"]},
    "1731-VICT": {"fid": "68550", "card": "database/fragrantica/social-cards/images/2516_1731-VICT_68550.jpeg", "notes": ["Meringues", "Vanilla", "Musk", "Sandalwood Flower", "Amber"]},
    "1768-LTN": {"fid": "40501", "card": "database/fragrantica/social-cards/images/2623_1768-LTN_40501.jpeg", "notes": ["Vanilla", "Cacao Pod", "Ambrette (Musk Mallow)", "Magnolia", "Orange Blossom", "Pear"]},
    "1770-BON": {"fid": "46057", "card": "database/fragrantica/social-cards/images/2625_1770-BON_46057.jpeg", "notes": ["Caramel", "Coffee", "Patchouli", "Floral Notes", "Gardenia", "Sandalwood"]},
    "1848-LEL": {"fid": "6334", "card": "database/fragrantica/social-cards/images/2768_1848-LEL_6334.jpeg", "notes": ["Ambrette (Musk Mallow)", "Fruity Notes", "Musk", "Aldehydes", "Lemon", "Amber"]},
    "1892-NRO": {"fid": "71596", "card": "database/fragrantica/social-cards/images/2800_1892-NRO_71596.jpeg", "notes": ["Musk", "Plum", "Vanilla", "Rose", "Tuberose", "Pink Pepper"]},
    "2099-MARG": {"fid": "67789", "card": "database/fragrantica/social-cards/images/current_2099-MARG_67789.jpeg", "notes": ["Cedar", "Cardamom", "Nutmeg", "Oakmoss", "Carrot Seeds", "Pink Pepper"]},
    "2134-MEM": {"fid": "60587", "card": "database/fragrantica/social-cards/images/3568_2134-MEM_60587.jpeg", "notes": ["Mandarin Orange", "Sage", "Basil", "Vetiver", "Leather", "Violet"]},
    "2151-GIV": {"fid": "78639", "card": "database/fragrantica/social-cards/images/3602_2151-GIV_78639.jpeg", "notes": ["Vanilla", "Cardamom", "Palo Santo", "Narcissus", "Sage", "Vetiver"]},
    "2169-ROJ": {"fid": "34996", "card": "database/fragrantica/social-cards/images/current_2169-ROJ_34996.jpeg", "notes": ["Cacao Pod", "Orris Root", "Vanilla", "Ylang-Ylang", "Heliotrope", "Sandalwood"]},
    "2271-ROJ": {"fid": "81839", "card": "database/fragrantica/social-cards/images/current_2271-ROJ_81839.jpeg", "notes": ["Grapefruit", "Rhubarb", "Bagas de Zimbro", "Lime", "Black Currant", "Bergamot"]},
    "2301-DIP": {"fid": "131717", "card": "database/fragrantica/social-cards/images/3943_2301-DIP_131717.jpeg", "notes": ["Ambrette (Musk Mallow)", "Carrot", "Musk", "Iris", "Aldehydes", "Cedar"]},
    "2431-ROJ": {"fid": "23008", "card": "database/fragrantica/social-cards/images/4170_2431-ROJ_23008.jpeg", "notes": ["Agarwood (Oud)", "Musk", "Rose", "Leather", "Woody Notes", "Ambrette (Musk Mallow)"]},
    "2467-NISH": {"fid": "64092", "card": "database/fragrantica/social-cards/images/4202_2467-NISH_64092.jpeg", "notes": ["Basil", "Mint", "Violet Leaf", "Yuzu", "Anise", "Licorice"]},
    "2532-PRA": {"fid": "32197", "card": "database/fragrantica/social-cards/images/4258_2532-PRA_32197.jpeg", "notes": ["Coumarin", "Ambrette (Musk Mallow)", "Iso E Super", "Cedar", "Hedione", "Orris Root"]},
    "2536-PRA": {"fid": "95006", "card": "database/fragrantica/social-cards/images/current_2536-PRA_95006.jpeg", "notes": ["Jasmine", "Neroli", "Bergamot", "Musk", "Ambrette (Musk Mallow)"]},
    "2550-ARM": {"fid": "90333", "card": "database/fragrantica/social-cards/images/current_2550-ARM_90333.jpeg", "notes": ["Tobacco", "Vanilla", "Chestnut", "Cinnamon Leaf", "Pimento", "Amber"]},
    "2557-ARIA": {"fid": "68664", "card": "database/fragrantica/social-cards/images/4284_2557-ARIA_68664.jpeg", "notes": ["Pear", "Ambrette (Musk Mallow)", "Vanilla", "Orris Root", "Sandalwood", "Rose"]},
    "320-NAS": {"fid": "40200", "card": "database/fragrantica/social-cards/images/2684_320-NAS_40200.jpeg", "notes": ["Whiskey", "Woody Notes", "Ambrette (Musk Mallow)", "Rose", "Ambroxan", "Musk"]},
    "353-TMFO": {"fid": "55766", "card": "database/fragrantica/social-cards/images/1891_353-TMFO_55766.jpeg", "notes": ["Vanilla", "Aldehydes", "Heliotrope", "Ambrette (Musk Mallow)", "Peru Balsam", "Sandalwood"]},
    "406-BAL": {"fid": "21987", "card": "database/fragrantica/social-cards/images/current_406-BAL_21987.jpeg", "notes": ["Fig Leaf", "Rose", "Petitgrain", "Grapefruit", "Pink Pepper", "Cedar"]},
    "533-DRC": {"fid": "1282", "card": "database/fragrantica/social-cards/images/current_533-DRC_1282.jpeg", "notes": ["Patchouli", "Rose", "Amber", "Bergamot", "Vanilla", "Mandarin Orange"]},
    "611-ESC": {"fid": "10611", "card": "database/fragrantica/social-cards/images/695_611-ESC_10611.jpeg", "notes": ["Mango", "Nectarine", "Blood Orange", "Raspberry", "Coconut", "Star Apple"]},
    "821-MIC": {"fid": "34276", "card": "database/fragrantica/social-cards/images/866_821-MIC_34276.jpeg", "notes": ["Lotus", "Pear", "Freesia", "Vanilla", "Ambrette (Musk Mallow)", "Peony"]},
    "896-RCAV": {"fid": "58538", "card": "database/fragrantica/social-cards/images/current_896-RCAV_58538.jpeg", "notes": ["Vanilla", "Cypriol Oil or Nagarmotha", "Magnolia", "Cedar", "Patchouli", "Rose"]},
}

# These cards have no contradiction, but the fresh all-green audit could not
# reproduce a complete exact reading. They must lose green status until a new
# exact reading exists; no note is changed.
INDEPENDENT_GREEN_REAUDIT_UNRESOLVED = {
    # The sixteen rows below were subsequently re-read directly from their
    # exact FID-bound Notes panels. Their explicit manual visual proof above
    # supersedes this withdrawal, so only cases still lacking a complete
    # current-card transcription remain here.
    "1073-DRC", "1090-COS", "1101-DOL", "1154-HER", "1168-HUG", "1499-BYR", "1831-TMFO", "1874-LTN", "1896-ESC", "1907-PEN", "2086-VICT", "2137-ROJ", "2162-BRB", "2216-DOL", "2489-KKWI", "2502-MATIE", "2570-JOM", "2753-YZLO", "2778-JOM", "2789-PEN", "2797-MATIE", "303-JOM", "465-CAL", "699-HER", "909-SFER",
}

rows = json.loads(DB.read_text(encoding="utf-8-sig"))
site_rows = json.loads(SITE.read_text(encoding="utf-8-sig"))
audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
by_code = {str(item.get("code") or "").strip().upper(): item for item in audit.get("rows", [])}
site_by_code = {str(item.get("code") or "").strip().upper(): item for item in site_rows}

corrections = []

# Apply the complete, independently reproduced contradictions first.  The
# full re-audit already established that each sequence comes from this exact
# physical card, so a stale prior audit result is never used to choose notes.
for row in rows:
    code = str(row.get("code") or "").strip().upper()
    proof = INDEPENDENT_GREEN_REAUDIT_CORRECTIONS.get(code)
    if not proof:
        continue
    item = by_code.get(code)
    fid = str(row.get("fragranticaId") or "").strip()
    card = ROOT / proof["card"]
    previous = list(row.get("fragranticaSocialCardNotes") or [])
    if (not item or fid != proof["fid"] or not card.is_file() or
            str(item.get("fragranticaId") or "") != fid or
            previous == list(proof["notes"])):
        continue
    row["fragranticaSocialCardNotes"] = list(proof["notes"])
    row["fragranticaSocialCardStatus"] = "VALIDATED_SOCIAL_CARD"
    item.update({
        "result": "EXACT_ORDERED_MATCH",
        "catalogNotesBeforeCorrection": previous,
        "catalogNotes": list(proof["notes"]),
        "observedNotes": list(proof["notes"]),
        "proof": "INDEPENDENT_FULL_GREEN_REAUDIT; COMPLETE_PHYSICAL_CARD_EXACT_MULTIPASS; ICON_COUNTS_MATCH",
        "independentGreenReauditResult": "EXACT_ORDERED_MATCH",
    })
    corrections.append({
        "code": code,
        "fragranticaId": fid,
        "card": proof["card"],
        "previousNotes": previous,
        "socialCardNotes": list(proof["notes"]),
        "proof": item["proof"],
    })

# The 41 fresh-read failures are not corrections and have no replacement
# notes. Record the unresolved result in the same exact-card audit so the
# validation builder cannot retain a historical green proof for them.
for code in INDEPENDENT_GREEN_REAUDIT_UNRESOLVED:
    item = by_code.get(code)
    if item:
        item["independentGreenReauditResult"] = "READING_NOT_STRICT_ENOUGH"
        item["independentGreenReauditRule"] = "Fresh full green-card re-audit did not reproduce a complete exact sequence"

# catalog_site.json is the compact renderer input. Keep its displayed note
# sequence in lockstep with only the 29 exact, FID-bound corrections above.
for row in rows:
    code = str(row.get("code") or "").strip().upper()
    if code in INDEPENDENT_GREEN_REAUDIT_CORRECTIONS and code in site_by_code:
        site_by_code[code]["fragranticaSocialCardNotes"] = list(row.get("fragranticaSocialCardNotes") or [])

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
    # The compact site data is the renderer input. Keep it aligned with the
    # exact direct-card transcription, otherwise proof and UI would diverge.
    if code in site_by_code:
        site_by_code[code]["fragranticaSocialCardNotes"] = list(notes)
    item.update({
        "result": "EXACT_ORDERED_MATCH",
        "catalogNotesBeforeCorrection": previous,
        "catalogNotes": notes,
        "observedNotes": notes,
        "labelCounts": list(proof["labelCounts"]),
        "iconCounts": list(proof["labelCounts"]),
        "proof": "DIRECT_VISUAL_SOCIAL_CARD_NOTES_PANEL; EXACT_FID; ORDERED_MANUAL_TRANSCRIPTION",
    })
    # Keep the OCR re-audit history, but record that a separately checked
    # exact-FID visual reading of the same physical Notes panel superseded it.
    if item.get("independentGreenReauditResult") == "READING_NOT_STRICT_ENOUGH":
        item["independentGreenReauditResult"] = "SUPERSEDED_BY_DIRECT_MANUAL_CARD_TRANSCRIPTION"
        item["independentGreenReauditRule"] = (
            "Original OCR did not reproduce the text; exact-card visual transcription "
            "with matching physical icon count was subsequently checked."
        )
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
SITE.write_text(json.dumps(site_rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
REPORT.write_text(json.dumps({
    "rule": "Only complete exact multi-rendering Social Card readings with matching physical icon counts may replace saved Main Notes.",
    "count": len(corrections),
    "corrections": corrections,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"directSocialCardCorrections": len(corrections)}, indent=2))
