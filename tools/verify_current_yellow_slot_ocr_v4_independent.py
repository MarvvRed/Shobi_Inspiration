#!/usr/bin/env python3
"""Independently re-verify V4 exact slot candidates before they can be green.

The V4 report is used only as a work list.  This verifier deliberately does
not import its OCR code, slot crop routine or card resolver.  It re-resolves
the current exact-FID card, re-reads every physical 2x3 slot using a separate
preprocessing family, derives the visible ordered sequence from pixels, and
only then checks it against the current catalog.

No result from this script changes an audit or catalog by itself.  Its JSON
report is an input to the separate, fail-closed apply step.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
SITE = ROOT / "database/catalog/catalog_site.json"
ORDERED_AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
V4 = ROOT / "database/audits/current-yellow-slot-ocr-v4.json"
LEXICON = ROOT / "database/audits/fragrantica-note-lexicon.txt"
CARDS = ROOT / "database/fragrantica/social-cards/images"
OUT = ROOT / "database/audits/current-yellow-slot-ocr-v4-independent-verification.json"


def code(value):
    return str(value or "").strip().upper()


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def exact_current_cards(shobi_code, fid):
    """Return the current-card namespace for this code and live FID only.

    Archived numeric-prefix cards are historical snapshots.  The current-card
    fetcher writes ``current_<code>_<fid>``; the verifier deliberately reads
    that namespace rather than choosing from all historical snapshots.
    """
    found = []
    for suffix in ("jpeg", "jpg", "png", "webp"):
        found.extend(CARDS.glob(f"current_{shobi_code}_{fid}.{suffix}"))
    return sorted(set(found))


def run_ocr(image, psm):
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    run = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
        input=payload.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=12, check=True, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    )
    words = []
    for item in csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t"):
        text = " ".join(str(item.get("text") or "").split())
        if not text:
            continue
        try:
            confidence = float(item.get("conf") or -1)
        except Exception:
            confidence = -1
        if confidence >= 35:
            words.append(text)
    return " ".join(words).strip()


def classify(raw, lexicon):
    value = norm(raw)
    if not value:
        return None, 0.0, 0.0, False
    exact = [note for note in lexicon if norm(note) == value]
    if len(exact) == 1:
        return exact[0], 1.0, 1.0, True
    ranked = sorted(((SequenceMatcher(None, value, norm(note)).ratio(), note) for note in lexicon), reverse=True)
    if not ranked:
        return None, 0.0, 0.0, False
    score, note = ranked[0]
    next_score = ranked[1][0] if len(ranked) > 1 else 0.0
    return note, score, score - next_score, False


def preprocessing_families(tile):
    """A separate set of image families from V4's auto/contrast/sharp bins."""
    gray = tile.convert("L")
    equalized = ImageOps.equalize(gray)
    auto = ImageOps.autocontrast(gray)
    return {
        "equalized": ImageEnhance.Contrast(equalized).enhance(1.8).filter(ImageFilter.UnsharpMask(1, 175, 1)),
        "unsharp": auto.filter(ImageFilter.UnsharpMask(2, 230, 2)),
        "threshold160": auto.point(lambda pixel: 255 if pixel > 160 else 0),
        "threshold205": auto.point(lambda pixel: 255 if pixel > 205 else 0),
    }


def inspect_slot(tile, lexicon):
    reads = []
    for family, image in preprocessing_families(tile).items():
        scaled = image.resize((max(1, image.width * 6), max(1, image.height * 6)), Image.Resampling.LANCZOS)
        for psm in (6, 7, 11, 12):
            try:
                raw = run_ocr(scaled, psm)
            except Exception:
                continue
            if not raw:
                continue
            candidate, score, margin, exact = classify(raw, lexicon)
            eligible = bool(candidate and (exact or (score >= 0.92 and margin >= 0.12)))
            reads.append({
                "family": family, "psm": psm, "raw": raw, "candidate": candidate,
                "score": round(score, 3), "margin": round(margin, 3), "exact": exact,
                "eligible": eligible,
            })

    exact_reads = [item for item in reads if item["eligible"] and item["exact"] and item["candidate"]]
    exact_counts = Counter(item["candidate"] for item in exact_reads)
    winner, count = exact_counts.most_common(1)[0] if exact_counts else (None, 0)
    exact_families = sorted({item["family"] for item in exact_reads if item["candidate"] == winner}) if winner else []
    exact_modes = sorted({f"{item['family']}:psm{item['psm']}" for item in exact_reads if item["candidate"] == winner}) if winner else []
    competitors = [
        item for item in reads
        if item["eligible"] and item["candidate"] and item["candidate"] != winner
    ]
    # Two independently invoked OCR configurations are required.  Requiring
    # two image families would silently change V4's published rule and would
    # reject valid exact evidence merely because one threshold family produces
    # the clearest glyphs; the verifier itself is the independent second path.
    strong = bool(winner and count >= 2 and len(exact_modes) >= 2 and not competitors)
    return {
        "winner": winner if strong else None,
        "strong": strong,
        "exactReads": count,
        "exactFamilies": exact_families,
        "exactModes": exact_modes,
        "competingEligibleReads": len(competitors),
        "reads": reads,
    }


def make_slots(source):
    """Independently crop the note grid using canonical card coordinates.

    This intentionally uses an inset geometry and separate values rather than
    V4's `crop_note_grid` implementation.  The fixed slots are only a physical
    reading layout; note identity and occupied-slot count come from OCR.
    """
    sx, sy = source.width / 1200, source.height / 1200
    panel = source.crop((round(45 * sx), round(730 * sy), round(465 * sx), round(1110 * sy)))
    panel = panel.convert("RGB").resize((420, 380), Image.Resampling.LANCZOS)
    rows = ((118, 220), (248, 370))
    columns = ((2, 138), (142, 278), (282, 418))
    slots = []
    for row, (top, bottom) in enumerate(rows):
        for column, (left, right) in enumerate(columns):
            slots.append((row, column, panel.crop((left, top, right, bottom))))
    return slots


def verify_candidate(source_item, db_by_code, site_by_code, audit_by_code, lexicon):
    shobi_code = code(source_item.get("code"))
    row = db_by_code.get(shobi_code)
    site = site_by_code.get(shobi_code)
    audit = audit_by_code.get(shobi_code)
    base = {"code": shobi_code, "sourceV4Result": source_item.get("result")}
    if not row or not site or not audit:
        return {**base, "result": "INDEPENDENT_REJECTED_MISSING_CURRENT_RECORD"}

    fid = str(row.get("fragranticaId") or "").strip()
    catalog = list(row.get("fragranticaSocialCardNotes") or [])
    base.update({"fid": fid, "catalog": catalog})
    # The publication workflow can recover an exact ordered match through an
    # earlier, separate gate before this V4 pass runs.  That must not make the
    # independent pixel re-check stale: it is either still needed to upgrade a
    # READING_NOT_STRICT_ENOUGH row, or it is redundant and must leave the
    # already exact proof untouched.  Site status is deliberately not used
    # here because the builder has not run at this point in the workflow.
    if (str(source_item.get("fid") or "") != fid or
            list(source_item.get("catalog") or []) != catalog or
            str(audit.get("fragranticaId") or "") != fid):
        return {**base, "result": "INDEPENDENT_REJECTED_STALE_TARGET"}
    if audit.get("result") not in {"READING_NOT_STRICT_ENOUGH", "EXACT_ORDERED_MATCH"}:
        return {**base, "result": "INDEPENDENT_REJECTED_UNEXPECTED_AUDIT_STATE", "currentAuditResult": audit.get("result")}

    cards = exact_current_cards(shobi_code, fid)
    relative_cards = [str(card.relative_to(ROOT)) for card in cards]
    base["currentExactCardCandidates"] = relative_cards
    if len(cards) != 1:
        return {**base, "result": "INDEPENDENT_REJECTED_CARD_AMBIGUITY"}
    card = cards[0]
    try:
        with Image.open(card) as image:
            if image.width < 800 or image.height < 800 or image.height / image.width < 0.85:
                return {**base, "result": "INDEPENDENT_REJECTED_UNSUPPORTED_CARD_GEOMETRY", "size": [image.width, image.height]}
            slots = make_slots(image)
    except Exception as exc:
        return {**base, "result": "INDEPENDENT_REJECTED_IMAGE_ERROR", "error": str(exc)}

    observed, slot_results, unresolved = [], [], False
    for row_index, col_index, slot in slots:
        evidence = inspect_slot(slot, lexicon)
        evidence.update({"row": row_index, "col": col_index})
        slot_results.append(evidence)
        if evidence["strong"]:
            observed.append(evidence["winner"])
        elif any(read.get("eligible") for read in evidence["reads"]):
            # Text-like evidence without a zero-competitor exact consensus is
            # not permitted to become an implicit empty slot.
            unresolved = True

    base.update({
        "card": str(card.relative_to(ROOT)),
        "previousAuditCard": str(audit.get("card") or ""),
        "previousAuditResult": audit.get("result"),
        "previousSiteStatus": site.get("validationStatus"),
        "observed": observed,
        "slots": slot_results,
    })
    if unresolved:
        return {**base, "result": "INDEPENDENT_REJECTED_UNRESOLVED_SLOT"}
    if not catalog or observed != catalog:
        return {**base, "result": "INDEPENDENT_REJECTED_SEQUENCE_NOT_EXACT"}
    return {
        **base,
        "result": "INDEPENDENT_EXACT_SLOT_SEQUENCE",
        "proof": "V4_WORKLIST_ONLY; FRESH_EXACT_FID_CARD_RESOLUTION; INDEPENDENT_2X3_SLOT_OCR; >=2_EXACT_READS_FROM_DISTINCT_OCR_CONFIGURATIONS_PER_OCCUPIED_SLOT; ZERO_COMPETING_ELIGIBLE_READS; PIXEL_DERIVED_COMPLETE_SEQUENCE; CATALOG_USED_ONLY_FOR_FINAL_EXACT_COMPARISON",
    }


def main():
    db = read_json(DB)
    site = read_json(SITE)
    ordered = read_json(ORDERED_AUDIT).get("rows", [])
    v4 = read_json(V4)
    lexicon = [line.strip() for line in LEXICON.read_text(encoding="utf-8").splitlines() if line.strip()]
    db_by_code = {code(row.get("code")): row for row in db}
    site_by_code = {code(row.get("code")): row for row in site}
    audit_by_code = {code(row.get("code")): row for row in ordered}
    targets = [row for row in v4.get("rows", []) if row.get("result") == "EXACT_SLOT_SEQUENCE"]
    results = [verify_candidate(item, db_by_code, site_by_code, audit_by_code, lexicon) for item in targets]
    counts = Counter(row["result"] for row in results)
    payload = {
        "mode": "INDEPENDENT_V4_SLOT_VERIFIER",
        "source": str(V4.relative_to(ROOT)),
        "sourceExactCandidates": len(targets),
        "counts": dict(sorted(counts.items())),
        "rows": results,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"targets": len(targets), "counts": payload["counts"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
