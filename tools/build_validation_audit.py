#!/usr/bin/env python3
"""Build strict per-perfume QA status. Green is never inferred from mere field presence."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database_complete.json"
SITE = ROOT / "catalog_site.json"
NOTE_ICON_MAP = ROOT / "note-icons" / "map.js"
GENDER_SEASON = ROOT / "fragrantica-scraper-archive" / "social-cards" / "gender-season.csv"

rows = json.loads(DB.read_text(encoding="utf-8-sig"))
site_rows = json.loads(SITE.read_text(encoding="utf-8-sig"))
if len(rows) != len(site_rows):
    raise SystemExit("Complete/site catalog row count mismatch")


def url_id(url):
    """Extract the ID from canonical Fragrantica URLs and valid /p/ID short URLs."""
    text = str(url or "").strip()
    for pattern in (r"-(\d+)\.html(?:$|[?#])", r"/p/(\d+)(?:/?$|[?#])"):
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1)
    return ""


def yes(value):
    """Accept the explicit verification labels used by the import pipelines."""
    return str(value or "").strip().upper() in {
        "VERIFIED", "VALIDATED", "CONFIRMED", "OK", "MATCH_CORRETTO", "MATCH CORRETTO",
        "VALIDATED_OCR", "VALIDATED_MANUAL", "VALIDATED_SOCIAL_CARD",
    }


def note_key(note):
    return " ".join(str(note or "").strip().lower().split())


def load_local_note_icons():
    """Read the locally committed Fragrantica icon index without external URLs."""
    prefix = "window.FRAGRANTICA_NOTE_ICON_MAP="
    text = NOTE_ICON_MAP.read_text(encoding="utf-8").strip()
    if not text.startswith(prefix):
        raise SystemExit("Invalid local note icon map")
    return json.loads(text[len(prefix):].rstrip(";"))


local_note_icons = load_local_note_icons()
with GENDER_SEASON.open(encoding="utf-8-sig", newline="") as handle:
    social_seasons = {
        str(item.get("shobi_code") or "").strip().upper(): item
        for item in csv.DictReader(handle)
    }


def has_verified_social_season(row, fid, seasons):
    """The dominant season must come from the card of the exact Fragrantica ID."""
    source = social_seasons.get(str(row.get("code") or "").strip().upper())
    if not source or str(source.get("fragrantica_id") or "").strip() != fid:
        return False
    main_season = str(source.get("main_season") or "").strip().lower()
    return bool(main_season) and main_season in {str(value).strip().lower() for value in seasons}


counts = {"green": 0, "yellow": 0, "red": 0}
for row, site in zip(rows, site_rows):
    if (site.get("code"), site.get("brand"), site.get("inspiredBy")) != (row.get("code"), row.get("brand"), row.get("inspiredBy")):
        raise SystemExit(f"Complete/site catalog alignment mismatch at product {row.get('prestashopProductId')}")

    fid = str(row.get("fragranticaId") or "").strip()
    furl = str(row.get("fragranticaUrl") or "").strip()
    notes = row.get("fragranticaSocialCardNotes") or []
    seasons = row.get("seasons") or []
    image = str(row.get("shobiImageUrl") or row.get("image") or "").strip()
    parsed_fid = url_id(furl)

    checks = {
        "identity": yes(row.get("identityStatus")),
        "fid": bool(fid),
        "url": bool(furl) and bool(fid) and parsed_fid == fid,
        "socialCard": yes(row.get("fragranticaSocialCardStatus")),
        "image": bool(image),
        "notes": bool(notes) and yes(row.get("fragranticaSocialCardStatus")),
        "icons": bool(notes) and all(note_key(note) in local_note_icons for note in notes),
        "gender": bool(row.get("gender") or row.get("genderAffinity")) and yes(row.get("genderStatus")),
        "season": bool(seasons) and has_verified_social_season(row, fid, seasons),
    }

    issues = []
    if not checks["identity"]: issues.append("Identity not fully verified")
    if not checks["fid"]: issues.append("Missing Fragrantica ID")
    if fid and furl and parsed_fid != fid: issues.append("Fragrantica URL/ID mismatch")
    elif not furl: issues.append("Missing direct Fragrantica URL")
    if not checks["socialCard"]: issues.append("Social Card not fully verified")
    if not checks["image"]: issues.append("Missing perfume image")
    if not notes: issues.append("Missing Main Notes")
    elif not checks["notes"]: issues.append("Main Notes order not fully verified")
    if not checks["icons"]: issues.append("Note icons not fully verified")
    if not checks["gender"]: issues.append("Gender not fully verified")
    if not checks["season"]: issues.append("Season not fully verified")

    hard_error = (
        not checks["identity"]
        or not checks["fid"]
        or not checks["url"]
        or str(row.get("identityStatus") or "").upper() in {"ERROR", "WRONG", "MISMATCH", "AMBIGUOUS"}
    )
    status = "red" if hard_error else ("green" if all(checks.values()) else "yellow")
    counts[status] += 1

    audit = {"status": status, "checks": checks, "issues": issues, "notesCount": len(notes)}
    row["validationAudit"] = audit
    site["validationStatus"] = status
    site["validationIssues"] = issues
    site["validationChecks"] = checks
    site["validationNotesCount"] = len(notes)

DB.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
SITE.write_text(json.dumps(site_rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print("validation", counts)
if counts["green"] and any(not all(r.get("validationAudit", {}).get("checks", {}).values()) for r in rows if r.get("validationAudit", {}).get("status") == "green"):
    raise SystemExit("Invalid green validation state")
