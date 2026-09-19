#!/usr/bin/env python3
"""Build strict per-perfume QA status. Green is never inferred from mere field presence."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
SITE = ROOT / "database/catalog/catalog_site.json"
NOTE_ICON_MAP = ROOT / "database" / "assets" / "note-icons" / "map.js"
GENDER_SEASON = ROOT / "database/fragrantica" / "social-cards" / "gender-season.csv"
VALIDATED_NOTES = ROOT / "database/fragrantica/social-cards/records/social-card-main-notes-validated.json"
RAW_NOTES = ROOT / "database/fragrantica/social-cards/records/social-card-main-notes.json"
ORDERED_CARD_AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
V2_LABEL_PILOT = ROOT / "database/audits/label-ocr-pilot.json"
V2_EXACT_VALIDATION = ROOT / "database/audits/v2-exact-validation.json"
CURRENT_YELLOW_V2_PILOT = ROOT / "database/audits/current-yellow-label-ocr-v2.json"
CURRENT_YELLOW_V2_VALIDATION = ROOT / "database/audits/current-yellow-v2-exact-validation.json"
NEAR_PASS_REFINEMENT = ROOT / "database/audits/current-yellow-near-pass-ocr-refinement.json"
PERFUME_IMAGE_MAP = ROOT / "database/assets/perfumes" / "map.js"

rows = json.loads(DB.read_text(encoding="utf-8-sig"))
site_rows = json.loads(SITE.read_text(encoding="utf-8-sig"))
if len(rows) != len(site_rows):
    raise SystemExit("Complete/site catalog row count mismatch")


def row_code(row):
    return str(row.get("code") or "").strip().upper()


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
validated_notes = {row_code(item): item for item in json.loads(VALIDATED_NOTES.read_text(encoding="utf-8"))}
raw_notes = {row_code(item): item for item in json.loads(RAW_NOTES.read_text(encoding="utf-8"))}
ordered_card_audit = {row_code(item): item for item in json.loads(ORDERED_CARD_AUDIT.read_text(encoding="utf-8")).get("rows", [])}

# V2 is an additional conservative proof path.  The report status is never
# trusted by itself: every relevant condition is recomputed against the live
# catalog below so stale pilot output cannot turn a product green.
v2_pilot_payload = json.loads(V2_LABEL_PILOT.read_text(encoding="utf-8")) if V2_LABEL_PILOT.is_file() else {}
v2_validation_payload = json.loads(V2_EXACT_VALIDATION.read_text(encoding="utf-8")) if V2_EXACT_VALIDATION.is_file() else {}
v2_pilot = {row_code(item): item for item in v2_pilot_payload.get("rows", [])}
v2_validation = {row_code(item): item for item in v2_validation_payload.get("rows", [])}
current_yellow_v2_pilot_payload = json.loads(CURRENT_YELLOW_V2_PILOT.read_text(encoding="utf-8")) if CURRENT_YELLOW_V2_PILOT.is_file() else {}
current_yellow_v2_validation_payload = json.loads(CURRENT_YELLOW_V2_VALIDATION.read_text(encoding="utf-8")) if CURRENT_YELLOW_V2_VALIDATION.is_file() else {}
near_pass_refinement_payload = json.loads(NEAR_PASS_REFINEMENT.read_text(encoding="utf-8")) if NEAR_PASS_REFINEMENT.is_file() else {}
current_yellow_v2_pilot = {row_code(item): item for item in current_yellow_v2_pilot_payload.get("rows", [])}
current_yellow_v2_validation = {row_code(item): item for item in current_yellow_v2_validation_payload.get("rows", [])}
near_pass_refinement = {row_code(item): item for item in near_pass_refinement_payload.get("rows", [])}

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
    source = social_seasons.get(row_code(row))
    if not source or str(source.get("fragrantica_id") or "").strip() != fid:
        return False
    main_season = str(source.get("main_season") or "").strip().lower()
    return bool(main_season) and main_season in {str(value).strip().lower() for value in seasons}


def v2_strong_ordered_evidence(row, fid, notes):
    """Revalidate strong V2 per-label OCR evidence against the current catalog.

    A stored STRONG_EXACT label is only a hint.  To pass now, the same exact-FID
    archived card must still exist, the pilot sequence must still equal the live
    catalog sequence, and every visible label must have at least two eligible
    exact reads (including a real crop read) with no competing eligible note.
    """
    c = row_code(row)
    proof = v2_validation.get(c)
    pilot = v2_pilot.get(c)
    current_audit = ordered_card_audit.get(c)
    if not proof or not pilot or not current_audit:
        return False
    if proof.get("status") != "STRONG_EXACT" or pilot.get("result") != "EXACT_LABEL_SEQUENCE":
        return False
    if str(proof.get("fid") or "") != fid or str(pilot.get("fid") or "") != fid:
        return False
    if str(current_audit.get("fragranticaId") or "") != fid:
        return False
    card = str(current_audit.get("card") or "")
    if not card or not (ROOT / card).is_file():
        return False
    if list(pilot.get("catalog") or []) != list(notes) or list(pilot.get("observed") or []) != list(notes):
        return False
    details = list(pilot.get("details") or [])
    if not notes or len(details) != len(notes):
        return False
    for expected, detail in zip(notes, details):
        winner = detail.get("note")
        if not detail.get("confident") or winner != expected:
            return False
        reads = list(detail.get("reads") or [])
        winner_exact = [
            read for read in reads
            if read.get("eligible") and read.get("exact") and read.get("candidate") == winner
        ]
        exact_crop = [read for read in winner_exact if read.get("variant") != "locator"]
        competing = [
            read for read in reads
            if read.get("eligible") and read.get("candidate") and read.get("candidate") != winner
        ]
        if len(winner_exact) < 2 or not exact_crop or competing:
            return False
    return True



def near_pass_supplemental_evidence(row, fid, notes):
    """Recompute targeted supplemental proof for one previously weak V2 label.

    The stored SUPPLEMENTAL_STRONG_EXACT result is only a hint. All original
    strong labels are rechecked from the current-yellow V2 pilot, while the one
    failed label must have >=2 new exact crop reads and zero competing eligible
    reads in the refinement report. Current FID, ordered sequence and archived
    Social Card must still match the live row.
    """
    c = row_code(row)
    pilot = current_yellow_v2_pilot.get(c)
    validation = current_yellow_v2_validation.get(c)
    refinement = near_pass_refinement.get(c)
    current_audit = ordered_card_audit.get(c)
    if not pilot or not validation or not refinement or not current_audit:
        return False
    if refinement.get("result") != "SUPPLEMENTAL_STRONG_EXACT":
        return False
    if pilot.get("result") != "EXACT_LABEL_SEQUENCE" or validation.get("status") != "REVIEW":
        return False
    if any(str(x.get("fid") or "") != fid for x in (pilot, validation, refinement)):
        return False
    if str(current_audit.get("fragranticaId") or "") != fid:
        return False
    card = str(current_audit.get("card") or "")
    if not card or not (ROOT / card).is_file():
        return False
    if list(pilot.get("catalog") or []) != list(notes) or list(pilot.get("observed") or []) != list(notes):
        return False
    details = list(pilot.get("details") or [])
    labels = list(validation.get("labels") or [])
    if not notes or len(details) != len(notes) or len(labels) != len(notes):
        return False
    failed = [lab for lab in labels if not lab.get("ok")]
    if len(failed) != 1:
        return False
    failed_note = failed[0].get("note")
    if refinement.get("failedNote") != failed_note:
        return False
    refined = refinement.get("refined") or {}
    if refined.get("expected") != failed_note:
        return False
    rreads = list(refined.get("reads") or [])
    rexact = [r for r in rreads if r.get("eligible") and r.get("exact") and r.get("candidate") == failed_note]
    rcompeting = [r for r in rreads if r.get("eligible") and r.get("candidate") and r.get("candidate") != failed_note]
    if len(rexact) < 2 or rcompeting:
        return False
    for expected, detail, label in zip(notes, details, labels):
        if detail.get("note") != expected or label.get("note") != expected or not detail.get("confident"):
            return False
        if expected == failed_note:
            continue
        if not label.get("ok"):
            return False
        reads = list(detail.get("reads") or [])
        winner_exact = [r for r in reads if r.get("eligible") and r.get("exact") and r.get("candidate") == expected]
        exact_crop = [r for r in winner_exact if r.get("variant") != "locator"]
        competing = [r for r in reads if r.get("eligible") and r.get("candidate") and r.get("candidate") != expected]
        if len(winner_exact) < 2 or not exact_crop or competing:
            return False
    return True

def exact_ordered_card_evidence(row, fid, notes):
    """Require independent exact count, identity and order from the current Social Card.

    The primary strict whole-card audit remains authoritative.  Strong V2
    per-label evidence is accepted only after all of its constraints are
    recomputed against the current row and exact archived card.

    CURRENT_FID_FAST_EXACT_PROOF remains supporting evidence only and cannot
    certify a green status.
    """
    item = ordered_card_audit.get(row_code(row))
    card = str(item.get("card") or "") if item else ""
    strict_whole_card = bool(
        item
        and item.get("result") == "EXACT_ORDERED_MATCH"
        and str(item.get("fragranticaId") or "") == fid
        and item.get("catalogNotes") == notes
        and item.get("observedNotes") == notes
        and card
        and (ROOT / card).is_file()
    )
    return strict_whole_card or v2_strong_ordered_evidence(row, fid, notes) or near_pass_supplemental_evidence(row, fid, notes)


def exact_social_card(row, fid, notes):
    """Require an explicit validated record for this code, the same FID, a local file, and exact notes.

    The validated JSON is already keyed by Shobi code, so the filename itself is not evidence and
    must not be used as an additional identity gate. Legacy VALIDATED_MANUAL raw cards keep the
    historical filename guard until their metadata is migrated to the validated source.
    """
    source = validated_notes.get(row_code(row))
    card = str(source.get("card") or "") if source else ""
    suffix = "_" + str(row.get("code")) + "_" + fid + ".jpeg"
    raw = raw_notes.get(row_code(row))
    raw_card = str(raw.get("card") or "") if raw else ""
    manual = str(row.get("fragranticaSocialCardStatus") or "").upper() == "VALIDATED_MANUAL"
    validated_exact = bool(
        source
        and source.get("validated") is True
        and str(source.get("fragranticaId") or "") == fid
        and card
        and (ROOT / card).is_file()
        and source.get("mainNotes") == notes
        and exact_ordered_card_evidence(row, fid, notes)
    )
    manual_exact = bool(
        manual
        and raw
        and str(raw.get("fragranticaId") or "") == fid
        and raw_card.endswith(suffix)
        and (ROOT / raw_card).is_file()
        and bool(notes)
        and exact_ordered_card_evidence(row, fid, notes)
    )
    return validated_exact or manual_exact


def exact_perfume_image(row, fid):
    path = perfume_images.get(row_code(row), "")
    return path == "database/assets/perfumes/" + fid + ".avif" and (ROOT / path).is_file()


def matched_notes_count(row, fid, notes):
    if str(row.get("fragranticaSocialCardStatus") or "").upper() == "VALIDATED_MANUAL" and exact_social_card(row, fid, notes): return len(notes)
    source = validated_notes.get(row_code(row))
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
    parsed_fid = url_id(furl)
    matching_notes = matched_notes_count(row, fid, notes)
    matching_icons = sum(note_key(note) in local_note_icons for note in notes)

    checks = {
        "shobiProduct": bool(row.get("prestashopProductId")) and bool(row.get("shobiUrl")) and row.get("catalogSource") == "database/source/shobi-perfumes-live-unique.csv",
        "shobiIdentity": bool(row.get("brand")) and bool(row.get("inspiredBy")) and row.get("catalogSource") == "database/source/shobi-perfumes-live-unique.csv",
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
SITE.write_text(json.dumps(site_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("validation", counts)
if counts["green"] and any(not all(r.get("validationAudit", {}).get("checks", {}).values()) for r in rows if r.get("validationAudit", {}).get("status") == "green"):
    raise SystemExit("Invalid green validation state")
