#!/usr/bin/env python3
"""Recover exact ordered Social Card proofs from already archived independent evidence.

This pass deliberately avoids the deprecated CURRENT_FID_FAST_EXACT_PROOF path.
A yellow row can be promoted only when the current catalog code/FID/note sequence
matches a strong historical Social Card source for the same identity:

1. direct visual review of the archived Social Card notes panel, or
2. historical validated slot OCR whose slot sequence is complete and whose
   fuzzy slots meet strict score/margin/confidence thresholds.

The source card must still exist locally. Nothing rewrites catalog notes.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
VALIDATED = ROOT / "database/fragrantica/social-cards/records/social-card-main-notes-validated.json"
VISUAL = ROOT / "database/fragrantica/social-cards/records/social-card-main-notes-visual-review.json"

FAST_MARKER = "CURRENT_FID_FAST_EXACT_PROOF"


def code(value):
    return str(value or "").strip().upper()


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def exact_url_fid(url, fid):
    text = str(url or "").strip()
    for pattern in (r"-(\d+)\.html(?:$|[?#])", r"/p/(\d+)(?:/?$|[?#])"):
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1) == fid
    return False


def strong_historical_ocr(item, notes):
    if item.get("validated") is not True:
        return False, "not_validated"
    if str(item.get("validationMethod") or "").upper() == FAST_MARKER:
        return False, "fast_marker_method"
    if list(item.get("mainNotes") or []) != notes:
        return False, "notes_differ"

    slots = list(item.get("validatedSlots") or [])
    if len(slots) != len(notes):
        return False, "incomplete_slots"
    ordered_names = [str(slot.get("name") or "") for slot in slots]
    if ordered_names != notes:
        return False, "slot_sequence_differ"

    for expected, slot in zip(notes, slots):
        raw = str(slot.get("raw") or "")
        if FAST_MARKER in raw.upper():
            return False, "fast_marker_slot"
        if norm(raw) == norm(expected):
            continue
        try:
            score = float(slot.get("matchScore"))
        except (TypeError, ValueError):
            score = -1.0
        try:
            margin = float(slot.get("margin"))
        except (TypeError, ValueError):
            margin = -1.0
        try:
            confidence = float(slot.get("ocrConfidence"))
        except (TypeError, ValueError):
            confidence = -1.0
        # Historical fuzzy acceptance is intentionally stricter than the old
        # validator. It must be a close, clearly separated OCR match.
        if not (score >= 0.95 and margin >= 0.08 and confidence >= 50.0):
            return False, "weak_fuzzy_slot"
    return True, "strong_historical_slot_ocr"


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    historical = json.loads(VALIDATED.read_text(encoding="utf-8"))
    visual = json.loads(VISUAL.read_text(encoding="utf-8"))

    by_code = {code(row.get("code")): row for row in rows}
    hist_index = defaultdict(list)
    for item in historical:
        hist_index[(code(item.get("code")), str(item.get("fragranticaId") or "").strip())].append(item)
    visual_index = defaultdict(list)
    for item in visual:
        visual_index[(code(item.get("code")), str(item.get("fragranticaId") or "").strip())].append(item)

    recovered = []
    rejected = Counter()
    evidence_counts = Counter()

    for item in audit.get("rows", []):
        if item.get("result") != "READING_NOT_STRICT_ENOUGH":
            continue
        c = code(item.get("code"))
        row = by_code.get(c)
        if not row:
            rejected["missing_catalog_row"] += 1
            continue
        fid = str(row.get("fragranticaId") or "").strip()
        notes = list(row.get("fragranticaSocialCardNotes") or [])
        if not fid or not notes:
            rejected["missing_fid_or_notes"] += 1
            continue
        if not exact_url_fid(row.get("fragranticaUrl"), fid):
            rejected["url_fid_not_exact"] += 1
            continue

        proof = None
        proof_source = None
        proof_card = None

        # Strongest source first: explicit direct visual reading of the notes panel.
        for source in visual_index.get((c, fid), []):
            card = str(source.get("card") or "")
            if (source.get("source") == "direct_visual_social_card_notes_panel"
                    and list(source.get("mainNotes") or []) == notes
                    and card and (ROOT / card).is_file()):
                proof = "DIRECT_VISUAL_SOCIAL_CARD_NOTES_PANEL_EXACT_ORDER"
                proof_source = "social-card-main-notes-visual-review.json"
                proof_card = card
                break

        if not proof:
            for source in hist_index.get((c, fid), []):
                card = str(source.get("card") or "")
                ok, reason = strong_historical_ocr(source, notes)
                if not ok:
                    rejected[reason] += 1
                    continue
                if not card or not (ROOT / card).is_file():
                    rejected["historical_card_missing"] += 1
                    continue
                proof = "HISTORICAL_VALIDATED_SOCIAL_CARD_SLOTS_EXACT_ORDER"
                proof_source = "social-card-main-notes-validated.json"
                proof_card = card
                break

        if not proof:
            rejected["no_strong_cross_source_proof"] += 1
            continue

        # The audit's exact identity must agree with the catalog before promotion.
        if str(item.get("fragranticaId") or "") != fid or list(item.get("catalogNotes") or []) != notes:
            rejected["audit_identity_or_notes_differ"] += 1
            continue

        item.update({
            "result": "EXACT_ORDERED_MATCH",
            "observedNotes": notes,
            "components": [],
            "proof": proof,
            "crossSourceEvidence": {
                "source": proof_source,
                "card": proof_card,
                "code": c,
                "fragranticaId": fid,
                "sequence": notes,
                "deprecatedFastProofUsed": False,
            },
        })
        recovered.append(c)
        evidence_counts[proof] += 1

    audit["results"] = dict(sorted(Counter(entry.get("result") for entry in audit.get("rows", [])).items()))
    audit["crossSourceRecovery"] = {
        "recovered": len(recovered),
        "codes": recovered,
        "evidence": dict(sorted(evidence_counts.items())),
        "rejected": dict(sorted(rejected.items())),
        "policy": "No CURRENT_FID_FAST_EXACT_PROOF. Only same-code same-FID direct visual review or strong historical slot OCR with exact final order.",
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "recovered": len(recovered),
        "results": audit["results"],
        "evidence": dict(sorted(evidence_counts.items())),
        "rejected": dict(sorted(rejected.items())),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
