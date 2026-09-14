#!/usr/bin/env python3
"""Apply only Social Card note sequences proven by the strict image audit."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database_complete.json"
SITE = ROOT / "catalog_site.json"
VALIDATED = ROOT / "social-card-main-notes-validated.json"
AUDIT = ROOT / "social-card-ordered-image-audit.json"
REPORT = ROOT / "strict-ordered-card-corrections.json"


def code(value):
    return str(value or "").strip().upper()


rows = json.loads(DB.read_text(encoding="utf-8-sig"))
site_rows = json.loads(SITE.read_text(encoding="utf-8"))
audit = json.loads(AUDIT.read_text(encoding="utf-8"))
validated = json.loads(VALIDATED.read_text(encoding="utf-8"))
if audit.get("catalogRows") != len(rows) or len(rows) != len(site_rows):
    raise SystemExit("Audit/database/site row count mismatch")

db_by_code = {}
site_by_code = {}
for db, site in zip(rows, site_rows):
    c = code(db.get("code"))
    if not c:
        raise SystemExit("Missing catalog code")
    # The current source contains four exact duplicate product rows.  They are
    # identical in identity/FID/notes, so using either as the note target is
    # safe; non-identical duplicates remain a hard stop.
    signature = (db.get("brand"), db.get("inspiredBy"), db.get("fragranticaId"), db.get("fragranticaSocialCardNotes"))
    if c in db_by_code:
        previous = db_by_code[c]
        previous_sig = (previous.get("brand"), previous.get("inspiredBy"), previous.get("fragranticaId"), previous.get("fragranticaSocialCardNotes"))
        if previous_sig != signature:
            raise SystemExit(f"Ambiguous duplicate catalog code: {c}")
    else:
        db_by_code[c] = db
        site_by_code[c] = site
valid_by_code = {code(row.get("code")): row for row in validated}

changes = []
for item in audit.get("rows") or []:
    if item.get("result") != "ORDERED_MISMATCH":
        continue
    c = code(item.get("code"))
    observed = list(item.get("observedNotes") or [])
    db = db_by_code.get(c)
    site = site_by_code.get(c)
    if not db or not site or not observed:
        raise SystemExit(f"Missing strict mismatch target: {c}")
    fid = str(db.get("fragranticaId") or "")
    if fid != str(item.get("fragranticaId") or ""):
        raise SystemExit(f"Fragrantica ID changed after audit: {c}")
    card = str(item.get("card") or "")
    if not card or not (ROOT / card).is_file():
        raise SystemExit(f"Exact card missing after audit: {c}")
    old = list(db.get("fragranticaSocialCardNotes") or [])
    db["fragranticaSocialCardNotes"] = observed
    db["fragranticaSocialCardStatus"] = "VALIDATED_IMAGE_ORDER_STRICT_V2"
    db["fragranticaSocialCardVerificationSource"] = card
    db["fragranticaSocialCardVerificationFragranticaId"] = fid
    site["fragranticaSocialCardNotes"] = observed
    source = valid_by_code.get(c)
    if source is None:
        source = {"code": c}
        validated.append(source)
        valid_by_code[c] = source
    source.update({
        "code": c,
        "fragranticaId": int(fid) if fid.isdigit() else fid,
        "card": card,
        "validated": True,
        "mainNotes": observed,
        "validationMethod": "INDEPENDENT_IMAGE_ORDER_OCR_STRICT_V2",
        "auditEvidence": {
            "rule": "Two independent OCR reads plus visible note-icon count; exact ordered sequence.",
            "iconCounts": item.get("iconCounts"),
            "labelCounts": item.get("labelCounts"),
        },
    })
    changes.append({"code": c, "fragranticaId": fid, "card": card, "oldNotes": old, "orderedCardNotes": observed})

DB.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
SITE.write_text(json.dumps(site_rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
VALIDATED.write_text(json.dumps(validated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
REPORT.write_text(json.dumps({"rule": "Only ORDERED_MISMATCH rows proven by the strict exact-card image audit are corrected.", "changed": len(changes), "rows": changes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"changed": len(changes), "report": str(REPORT)}, indent=2))
