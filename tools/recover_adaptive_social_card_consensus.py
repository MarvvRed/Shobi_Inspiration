#!/usr/bin/env python3
"""Recover ordered Main Notes from the Social Card image only.

This pass never uses catalog notes to recognize text, choose a note candidate,
choose the number of notes, or choose occupied slots. It reads the archived
Fragrantica Social Card through several independent image preprocessing
families, maps OCR text only against the global Fragrantica note lexicon, and
builds a physical slot consensus from image coordinates. Only after a complete
independent sequence has been obtained is it compared with the catalog.
"""
from __future__ import annotations

import csv
import io
import json
import os
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import (
    CROP, DB, OUT, SCALE, candidate, code, find_card, is_subsequence, parse_attempt,
)

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "database/audits/fragrantica-note-lexicon.txt"


def preprocess_families(panel):
    """Return genuinely different pixel transforms; PSM variants are not families."""
    auto = ImageOps.autocontrast(panel)
    contrast = ImageEnhance.Contrast(auto).enhance(2.0)
    equalized = ImageOps.equalize(panel).filter(ImageFilter.SHARPEN)
    unsharp = ImageOps.autocontrast(panel).filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=3))
    t175 = auto.point(lambda p: 255 if p > 175 else 0)
    t205 = auto.point(lambda p: 255 if p > 205 else 0)
    return {
        "contrast": contrast,
        "equalize": equalized,
        "unsharp": unsharp,
        "threshold175": t175,
        "threshold205": t205,
    }


def run_ocr(image, psm, lexicon):
    scaled = image.resize((image.width * SCALE, image.height * SCALE), Image.Resampling.LANCZOS)
    payload = io.BytesIO(); scaled.save(payload, format="PNG")
    run = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
        input=payload.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, timeout=12, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    )
    rows = list(csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t"))
    return parse_attempt(rows, lexicon)


def physical_slot(component):
    """Map independently detected label geometry to the card's 2x3 flex grid."""
    row = int(component.get("row", -1))
    x = float(component.get("x", -999))
    if row not in (0, 1) or x < 0 or x >= 420:
        return None
    # The panel itself defines the three equal flex columns. This does not use
    # catalog note count or expected note names.
    col = min(2, int(x // 140))
    return row, col


def acceptable(component):
    """Conservative lexicon recognition from OCR text alone."""
    name = component.get("note")
    if not name:
        return None
    confidence = float(component.get("confidence") or 0)
    score = float(component.get("score") or 0)
    margin = float(component.get("margin") or 0)
    exact = bool(component.get("exactText"))
    if exact and confidence >= 45:
        return name
    if score >= 0.92 and margin >= 0.14 and confidence >= 58:
        return name
    return None


def family_slots(attempts):
    """Collapse PSM 6/11 inside one preprocessing family; they are not independent."""
    raw_support = defaultdict(list)
    accepted = defaultdict(list)
    for attempt in attempts:
        for comp in attempt.get("components") or []:
            slot = physical_slot(comp)
            if slot is None:
                continue
            if comp.get("note"):
                raw_support[slot].append(comp.get("note"))
            name = acceptable(comp)
            if name:
                accepted[slot].append((name, bool(comp.get("exactText")), float(comp.get("confidence") or 0)))

    result = {}
    diagnostics = {}
    for slot in sorted(set(raw_support) | set(accepted)):
        values = accepted.get(slot, [])
        counts = Counter(name for name, _, _ in values)
        chosen = None
        if counts:
            name, count = counts.most_common(1)[0]
            competing = sum(v for k, v in counts.items() if k != name)
            exact = any(n == name and ex for n, ex, _ in values)
            # Within-family PSM disagreement is treated conservatively.
            if competing == 0 and (count >= 2 or exact):
                chosen = name
        result[slot] = chosen
        diagnostics[str(slot)] = {
            "rawCandidates": raw_support.get(slot, []),
            "acceptedCandidates": [v[0] for v in values],
            "chosen": chosen,
        }
    return result, diagnostics


def consensus(families):
    """Build note count/order from image evidence before catalog comparison."""
    slot_presence = Counter()
    slot_votes = defaultdict(Counter)
    exact_family_votes = defaultdict(Counter)
    for family in families.values():
        for slot, data in family.items():
            if data.get("present"):
                slot_presence[slot] += 1
            name = data.get("name")
            if name:
                slot_votes[slot][name] += 1
                if data.get("exact"):
                    exact_family_votes[slot][name] += 1

    # A physical slot must be visible/readable in at least three independent
    # pixel families. A possible extra slot seen by two families makes the card
    # unresolved rather than silently dropping a note.
    occupied = {slot for slot, n in slot_presence.items() if n >= 3}
    ambiguous_extra = {slot for slot, n in slot_presence.items() if n >= 2 and slot not in occupied}
    if ambiguous_extra or not occupied:
        return None, {"reason": "AMBIGUOUS_SLOT_COUNT", "presence": {str(k): v for k, v in slot_presence.items()}}

    observed = []
    per_slot = {}
    for slot in sorted(occupied):
        votes = slot_votes.get(slot, Counter())
        if not votes:
            return None, {"reason": "NO_NOTE_CONSENSUS", "slot": str(slot)}
        name, n = votes.most_common(1)[0]
        second = votes.most_common(2)[1][1] if len(votes) > 1 else 0
        exact_n = exact_family_votes.get(slot, Counter()).get(name, 0)
        # Two independent families suffice only if at least one had exact OCR;
        # otherwise require three independent preprocessing families.
        required = 2 if exact_n >= 1 else 3
        if n < required or second:
            return None, {"reason": "NOTE_CONSENSUS_TOO_WEAK", "slot": str(slot), "votes": dict(votes), "exactFamilies": exact_n}
        observed.append(name)
        per_slot[str(slot)] = {"note": name, "families": n, "exactFamilies": exact_n, "votes": dict(votes)}

    if len(observed) > 6:
        return None, {"reason": "TOO_MANY_NOTES", "count": len(observed)}
    return observed, {"reason": "OK", "presence": {str(k): v for k, v in slot_presence.items()}, "slots": per_slot}


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    audit = json.loads(OUT.read_text(encoding="utf-8"))
    by_code = {code(r.get("code")): r for r in rows}
    lexicon = [x.strip() for x in LEXICON.read_text(encoding="utf-8").splitlines() if x.strip()]

    recovered = []
    rejected = Counter()
    examined = 0

    for item in audit.get("rows", []):
        if item.get("result") != "READING_NOT_STRICT_ENOUGH":
            continue
        row = by_code.get(code(item.get("code")))
        if not row:
            rejected["missing_catalog_row"] += 1; continue
        card = find_card(row)
        if not card:
            rejected["no_card"] += 1; continue
        try:
            with Image.open(card) as src:
                if src.width < 800 or src.height < 800 or src.height / src.width < 0.85:
                    rejected["unsupported_geometry"] += 1; continue
                sx, sy = src.width / 1200, src.height / 1200
                x1, y1, x2, y2 = CROP
                panel = src.crop((round(x1*sx), round(y1*sy), round(x2*sx), round(y2*sy))).convert("L").resize((420, 380), Image.Resampling.LANCZOS)
        except Exception:
            rejected["image_error"] += 1; continue

        examined += 1
        family_results = {}
        family_diag = {}
        strict_reads = []
        for family_name, variant in preprocess_families(panel).items():
            attempts = []
            for psm in (6, 11):
                try:
                    attempt = run_ocr(variant, psm, lexicon)
                except Exception as exc:
                    attempt = {"strict": False, "components": [], "notes": [], "error": str(exc)}
                attempts.append(attempt)
                if attempt.get("strict"):
                    strict_reads.append(attempt.get("notes") or [])
            slots, diag = family_slots(attempts)
            packed = {}
            for slot in set(slots) | {physical_slot(c) for a in attempts for c in (a.get("components") or [])}:
                if slot is None: continue
                comps = [c for a in attempts for c in (a.get("components") or []) if physical_slot(c) == slot]
                chosen = slots.get(slot)
                packed[slot] = {
                    "present": bool(comps),
                    "name": chosen,
                    "exact": bool(chosen and any(acceptable(c) == chosen and c.get("exactText") for c in comps)),
                }
            family_results[family_name] = packed
            family_diag[family_name] = diag

        observed, diag = consensus(family_results)
        if observed is None:
            rejected[diag.get("reason", "consensus_failed")] += 1
            continue

        # Existing strict reads are independent supporting reads and may omit a
        # label, but may never contradict the consensus sequence.
        if not all(is_subsequence(read, observed) for read in strict_reads):
            rejected["conflicting_strict_read"] += 1
            continue

        catalog = list(row.get("fragranticaSocialCardNotes") or [])
        if observed != catalog:
            rejected["sequence_not_exact"] += 1
            # Keep the independently observed mismatch in diagnostics, but never
            # rewrite the catalog automatically.
            item["adaptiveSocialCardDiagnostic"] = {"observedNotes": observed, "consensus": diag}
            continue

        item.update({
            "result": "EXACT_ORDERED_MATCH",
            "observedNotes": observed,
            "components": [],
            "proof": "SOCIAL_CARD_ONLY_ADAPTIVE_PHYSICAL_SLOT_CONSENSUS_ACROSS_INDEPENDENT_PREPROCESSING_FAMILIES; CATALOG_NOT_USED_FOR_RECOGNITION_OR_NOTE_COUNT",
            "adaptiveSocialCardEvidence": {
                "consensus": diag,
                "families": family_diag,
            },
        })
        recovered.append(code(item.get("code")))

    audit["results"] = dict(sorted(Counter(x.get("result") for x in audit.get("rows", [])).items()))
    audit["adaptiveSocialCardRecovery"] = {
        "examined": examined,
        "recovered": len(recovered),
        "codes": recovered,
        "rejected": dict(sorted(rejected.items())),
    }
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"examined": examined, "recovered": len(recovered), "results": audit["results"], "rejected": dict(sorted(rejected.items()))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
