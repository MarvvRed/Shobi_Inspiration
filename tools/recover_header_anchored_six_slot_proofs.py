#!/usr/bin/env python3
"""Recover exact six-note Social Card proofs with header-anchored slot geometry.

This pass is intentionally conservative:
- it only considers rows still marked READING_NOT_STRICT_ENOUGH;
- it only handles standard near-square cards with exactly six catalog notes;
- it derives vertical slot bands from the independently OCR-read Notes header;
- each slot must produce one exact lexicon label supported by at least two
  independent preprocessing families;
- the final six-label sequence must equal the existing catalog sequence exactly;
- any strict full-panel OCR read must remain an ordered subsequence.

No catalog note is rewritten or inferred.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

from PIL import Image

from audit_social_card_order_from_images import CARD_DIR, CROP, DB, OUT, code, find_card, is_subsequence
from recover_exact_card_proofs_multipass import read_six_slot_consensus

ROOT = Path(__file__).resolve().parents[1]


def header_y_from_attempts(item):
    values = []
    for attempt in item.get("attempts") or []:
        value = attempt.get("notesHeaderY")
        if isinstance(value, (int, float)):
            values.append(float(value))
    return statistics.median(values) if values else None


def shifted_panel(panel, header_y):
    """Translate a card-specific Notes header to the calibration used by the slot reader.

    The six-slot reader was calibrated around a Notes header near y=53 on the
    normalized 420x380 panel. Rather than changing slot semantics or using
    catalog labels, translate the whole panel vertically so the independently
    observed header is aligned to that calibration. Blank pixels are introduced
    at the exposed edge; no image content is synthesized.
    """
    target_header_y = 53.0
    shift = int(round(target_header_y - header_y))
    if shift == 0:
        return panel, 0

    shifted = Image.new("L", panel.size, 255)
    if shift > 0:
        source_box = (0, 0, panel.width, panel.height - shift)
        shifted.paste(panel.crop(source_box), (0, shift))
    else:
        amount = -shift
        source_box = (0, amount, panel.width, panel.height)
        shifted.paste(panel.crop(source_box), (0, 0))
    return shifted, shift


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    audit = json.loads(OUT.read_text(encoding="utf-8"))
    by_code = {code(row.get("code")): row for row in rows}

    examined = 0
    recovered = []
    rejected = Counter()

    for item in audit.get("rows", []):
        if item.get("result") != "READING_NOT_STRICT_ENOUGH":
            continue

        row = by_code.get(code(item.get("code")))
        if not row:
            rejected["missing_catalog_row"] += 1
            continue

        notes = list(row.get("fragranticaSocialCardNotes") or [])
        if len(notes) != 6:
            rejected[f"note_count_{len(notes)}"] += 1
            continue

        header_y = header_y_from_attempts(item)
        if header_y is None:
            rejected["no_header_y"] += 1
            continue

        card = find_card(row)
        if not card:
            rejected["no_exact_card"] += 1
            continue

        examined += 1
        try:
            with Image.open(card) as src:
                if src.width < 800 or src.height < 800 or src.height / src.width < 0.85:
                    rejected["unsupported_geometry"] += 1
                    continue
                sx, sy = src.width / 1200, src.height / 1200
                x1, y1, x2, y2 = CROP
                panel = src.crop(
                    (round(x1 * sx), round(y1 * sy), round(x2 * sx), round(y2 * sy))
                ).convert("L").resize((420, 380), Image.Resampling.LANCZOS)
        except Exception:
            rejected["image_error"] += 1
            continue

        aligned, shift = shifted_panel(panel, header_y)
        observed, components, diagnostics = read_six_slot_consensus(
            aligned,
            [line.strip() for line in (ROOT / "database/audits/fragrantica-note-lexicon.txt").read_text(encoding="utf-8").splitlines() if line.strip()],
        )

        if observed is None:
            rejected["slot_consensus_failed"] += 1
            continue
        if observed != notes:
            rejected["sequence_not_exact"] += 1
            continue

        strict_reads = [
            attempt.get("notes") or []
            for attempt in item.get("attempts") or []
            if attempt.get("strict")
        ]
        if not all(is_subsequence(strict, observed) for strict in strict_reads):
            rejected["conflicting_strict_read"] += 1
            continue

        item.update({
            "result": "EXACT_ORDERED_MATCH",
            "observedNotes": observed,
            "components": components,
            "proof": "HEADER_ANCHORED_SIX_SLOT_EXACT_LEXICON_CONSENSUS_FROM_AT_LEAST_TWO_PREPROCESSING_FAMILIES_PER_SLOT; ALL_STRICT_READS_ORDERED_SUBSEQUENCES",
            "headerAnchoredSixSlotEvidence": {
                "observedHeaderY": header_y,
                "alignmentShift": shift,
                "targetHeaderY": 53.0,
                "slotDiagnostics": diagnostics,
            },
        })
        recovered.append(code(item.get("code")))

    audit["results"] = dict(sorted(Counter(item.get("result") for item in audit.get("rows", [])).items()))
    audit["headerAnchoredSixSlotRecovery"] = {
        "examined": examined,
        "recovered": len(recovered),
        "codes": recovered,
        "rejected": dict(sorted(rejected.items())),
    }
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "examined": examined,
        "recovered": len(recovered),
        "results": audit["results"],
        "rejected": dict(sorted(rejected.items())),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
