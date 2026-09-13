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
VALIDATED_NOTES = ROOT / "social-card-main-notes-validated.json"
PERFUME_IMAGE_MAP = ROOT / "perfume-images" / "map.js"

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
validated_notes = {str(item.get("code") or "").strip().upper(): item for item in json.loads(VALIDATED_NOTES.read_text(encoding="utf-8"))}
image_prefix = "window.PERFUME_IMAGE_MAP="
image_text = PERFUME_IMAGE_MAP.read_text(encoding="utf-8").strip()
if not image_text.startswith(image_prefix): raise SystemExit("Invalid perfume image map")
perfume_images = json.loads(image_text[len(image_prefix):].rstrip(";"))
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


def exact_social_card(row, fid, notes):
    source = validated_notes.get(str(row.get("code") or "").strip().upper())
    card = str(source.get("card") or "") if source else ""
    suffix = "_" + str(row.get("code")) + "_" + fid + ".jpeg"
    return bool(source and source.get("validated") is True and str(source.get("fragranticaId") or "") == fid and card.endswith(suffix) and (ROOT / card).is_file() and source.get("mainNotes") == notes)


def exact_perfume_image(row, fid):
    path = perfume_images.get(str(row.get("code") or "").strip().upper(), "")
    return path == "perfume-images/" + fid + ".avif" and (ROOT / path).is_file()


def matched_notes_count(row, fid, notes):
    source = validated_notes.get(str(row.get("code") or "").strip().upper())
    if not source or str(source.get("fragranticaId") or "") != fid: return 0
    return sum(actual == expected for actual, expected in zip(notes, source.get("mainNotes") or []))


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
    matching_notes = matched_notes_count(row, fid, notes)
    matching_icons = sum(note_key(note) in local_note_icons for note in notes)

    checks = {
        "shobiProduct": bool(row.get("prestashopProductId")) and bool(row.get("shobiUrl")) and str(row.get("code") or "").lower() in str(row.get("shobiUrl") or "").lower(),
        "shobiIdentity": bool(row.get("brand")) and bool(row.get("inspiredBy")) and row.get("catalogSource") == "shobi-perfumes-live-unique.csv",
        "identity": yes(row.get("identityStatus")) and bool(row.get("fragranticaVerificationSource")),
        "fid": bool(fid),
        "url": bool(furl) and bool(fid) and parsed_fid == fid,
        "socialCard": exact_social_card(row, fid, notes),
        "image": exact_perfume_image(row, fid),
        "notes": bool(notes) and exact_social_card(row, fid, notes),
        "icons": bool(notes) and matching_icons == len(notes),
        "gender": bool(row.get("gender") or row.get("genderAffinity")) and yes(row.get("genderStatus")),
        "season": bool(seasons) and has_verified_social_season(row, fid, seasons),
    }

    issues = []
    if not checks["shobiProduct"]: issues.append("Shobi product page not fully verified")
    if not checks["shobiIdentity"]: issues.append("Shobi original name/brand not fully verified")
    if not checks["identity"]: issues.append("Fragrantica identity not fully verified")
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

    hard_error = (bool(fid and furl) and parsed_fid != fid) or str(row.get("identityStatus") or "").upper() in {"ERROR", "WRONG", "MISMATCH"}
    status = "red" if hard_error else ("green" if all(checks.values()) else "yellow")
    counts[status] += 1

    audit = {"status": status, "checks": checks, "issues": issues, "notesCount": len(notes), "matchedNotesCount": matching_notes, "iconsCount": matching_icons}
    row["validationAudit"] = audit
    site["validationStatus"] = status
    site["validationIssues"] = issues
    site["validationChecks"] = checks
    site["validationNotesCount"] = len(notes)
    site["validationMatchedNotesCount"] = matching_notes
    site["validationIconsCount"] = matching_icons

DB.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
SITE.write_text(json.dumps(site_rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print("validation", counts)
if counts["green"] and any(not all(r.get("validationAudit", {}).get("checks", {}).values()) for r in rows if r.get("validationAudit", {}).get("status") == "green"):
    raise SystemExit("Invalid green validation state")
