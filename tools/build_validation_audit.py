#!/usr/bin/env python3
"""Build strict per-perfume QA status. Green is never inferred from mere field presence."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database_complete.json"
SITE = ROOT / "catalog_site.json"

rows = json.loads(DB.read_text(encoding="utf-8-sig"))
site_rows = json.loads(SITE.read_text(encoding="utf-8-sig"))
site_by_code = {r["code"]: r for r in site_rows}


def url_id(url):
    m = re.search(r"-(\d+)\.html(?:$|[?#])", str(url or ""))
    return m.group(1) if m else ""


def yes(value):
    return str(value or "").strip().upper() in {"VERIFIED", "VALIDATED", "CONFIRMED", "OK", "MATCH_CORRETTO", "MATCH CORRETTO"}

counts = {"green": 0, "yellow": 0, "red": 0}
for row in rows:
    fid = str(row.get("fragranticaId") or "").strip()
    furl = str(row.get("fragranticaUrl") or "").strip()
    notes = row.get("fragranticaSocialCardNotes") or []
    seasons = row.get("seasons") or []
    image = str(row.get("shobiImageUrl") or row.get("image") or "").strip()

    checks = {
        "identity": yes(row.get("identityStatus")),
        "fid": bool(fid),
        "url": bool(furl) and bool(fid) and url_id(furl) == fid,
        "socialCard": yes(row.get("fragranticaSocialCardStatus")),
        "image": bool(image),
        "notes": bool(notes) and yes(row.get("fragranticaSocialCardStatus")),
        # Icon correctness/order require explicit audit evidence; presence alone must never create green.
        "icons": yes(row.get("noteIconsStatus")),
        "gender": bool(row.get("gender") or row.get("genderAffinity")) and yes(row.get("genderStatus")),
        "season": bool(seasons) and yes(row.get("seasonStatus")),
    }

    issues = []
    if not checks["identity"]: issues.append("Identity not fully verified")
    if not checks["fid"]: issues.append("Missing Fragrantica ID")
    if fid and furl and url_id(furl) != fid: issues.append("Fragrantica URL/ID mismatch")
    elif not furl: issues.append("Missing direct Fragrantica URL")
    if not checks["socialCard"]: issues.append("Social Card not fully verified")
    if not checks["image"]: issues.append("Missing perfume image")
    if not notes: issues.append("Missing Main Notes")
    elif not checks["notes"]: issues.append("Main Notes order not fully verified")
    if not checks["icons"]: issues.append("Note icons not fully verified")
    if not checks["gender"]: issues.append("Gender not fully verified")
    if not checks["season"]: issues.append("Season not fully verified")

    hard_error = (bool(fid and furl) and url_id(furl) != fid) or str(row.get("identityStatus") or "").upper() in {"ERROR", "WRONG", "MISMATCH"}
    status = "red" if hard_error else ("green" if all(checks.values()) else "yellow")
    counts[status] += 1

    audit = {
        "status": status,
        "checks": checks,
        "issues": issues,
        "notesCount": len(notes),
    }
    row["validationAudit"] = audit
    site = site_by_code.get(row["code"])
    if site is not None:
        site["validationStatus"] = status
        site["validationIssues"] = issues
        site["validationChecks"] = checks
        site["validationNotesCount"] = len(notes)

DB.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
SITE.write_text(json.dumps(site_rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print("validation", counts)
if counts["green"] and any(not all(r.get("validationAudit", {}).get("checks", {}).values()) for r in rows if r.get("validationAudit", {}).get("status") == "green"):
    raise SystemExit("Invalid green validation state")
