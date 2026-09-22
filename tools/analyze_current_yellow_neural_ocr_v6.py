#!/usr/bin/env python3
"""Fail-closed neural-OCR analysis of unresolved Social Card note slots.

This is intentionally separate from the Tesseract V4 pipeline: it uses the
PaddleOCR recognition model, a corrected physical 2x3 notes geometry, and a
fresh exact-current-FID card resolver.  It never narrows recognition using the
target catalog.  A catalog sequence is consulted only after every visible slot
has independently produced the same exact lexicon label twice and no other
exact label competes.

The output is analysis-only.  A separate verifier/apply pair is required
before a result can change an audit state.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from paddleocr import PaddleOCR

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
LEXICON = ROOT / "database/audits/fragrantica-note-lexicon.txt"
CARDS = ROOT / "database/fragrantica/social-cards/images"
OUT = ROOT / "database/audits/current-yellow-neural-ocr-v6.json"

# Full physical cells on a standard 1200×1200 Fragrantica Social Card.  These
# include every label line; V5's former first-row window ended through labels.
ROWS = ((785, 990), (990, 1140))
COLS = ((60, 180), (185, 305), (310, 435))


def code(value):
    return str(value or "").strip().upper()


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def current_cards(shobi_code, fid):
    found = []
    for suffix in ("jpeg", "jpg", "png", "webp"):
        found.extend(CARDS.glob(f"current_{shobi_code}_{fid}.{suffix}"))
    return sorted(set(found))


def cells(path):
    with Image.open(path) as source:
        if source.width < 800 or source.height < 800 or source.height / source.width < 0.85:
            return None
        image = source.convert("RGB").resize((1200, 1200), Image.Resampling.LANCZOS)
    return [image.crop((x1, y1, x2, y2)) for y1, y2 in ROWS for x1, x2 in COLS]


def variants(tile):
    # Distinct raster families for repeatability inside the neural recognizer.
    natural = tile.resize((tile.width * 5, tile.height * 5), Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(tile.convert("L"))
    enhanced = ImageEnhance.Contrast(gray).enhance(2.2).filter(ImageFilter.UnsharpMask(2, 180, 2))
    binary = enhanced.point(lambda value: 255 if value > 180 else 0)
    return {
        "natural_rgb": natural,
        "contrast_gray": enhanced.resize((enhanced.width * 5, enhanced.height * 5), Image.Resampling.LANCZOS),
        "binary": binary.resize((binary.width * 5, binary.height * 5), Image.Resampling.LANCZOS),
    }


def recognize(ocr, image):
    result = ocr.ocr(np.asarray(image), cls=False)
    entries = []
    for block in result or []:
        for line in block or []:
            if not isinstance(line, (list, tuple)) or len(line) < 2:
                continue
            box, pair = line[0], line[1]
            if not isinstance(pair, (list, tuple)) or not pair:
                continue
            text = " ".join(str(pair[0]).split())
            if not text:
                continue
            try:
                confidence = float(pair[1])
            except Exception:
                confidence = 0.0
            try:
                y = min(float(point[1]) for point in box)
            except Exception:
                y = 0.0
            entries.append((y, text, confidence))
    entries.sort(key=lambda item: item[0])
    return " ".join(item[1] for item in entries), (min((item[2] for item in entries), default=0.0))


def exact_note(raw, lexicon):
    compact = norm(raw)
    hits = [note for note in lexicon if norm(note) == compact]
    return hits[0] if len(hits) == 1 else None


def inspect_slot(ocr, tile, lexicon):
    reads = []
    for family, image in variants(tile).items():
        try:
            raw, confidence = recognize(ocr, image)
        except Exception as exc:
            reads.append({"family": family, "error": str(exc)})
            continue
        note = exact_note(raw, lexicon)
        reads.append({
            "family": family, "raw": raw, "confidence": round(confidence, 4),
            "exactNote": note,
            "eligible": bool(note and confidence >= 0.70),
        })
    exact = [item["exactNote"] for item in reads if item.get("eligible")]
    counts = Counter(exact)
    winner, winner_count = counts.most_common(1)[0] if counts else (None, 0)
    competitors = sorted(note for note in counts if note != winner)
    return {
        "winner": winner if winner_count >= 2 and not competitors else None,
        "exactReads": winner_count,
        "competitors": competitors,
        "reads": reads,
    }


def inspect_target(row, lexicon, ocr):
    shobi_code = code(row.get("code"))
    fid = str(row.get("fragranticaId") or "").strip()
    catalog = list(row.get("fragranticaSocialCardNotes") or [])
    base = {"code": shobi_code, "fid": fid, "catalog": catalog}
    cards = current_cards(shobi_code, fid)
    if len(cards) != 1:
        return {**base, "result": "NO_UNIQUE_CURRENT_EXACT_FID_CARD", "cards": [str(path.relative_to(ROOT)) for path in cards]}
    card = cards[0]
    slots = cells(card)
    if not slots:
        return {**base, "result": "UNSUPPORTED_CARD_GEOMETRY", "card": str(card.relative_to(ROOT))}
    details = [inspect_slot(ocr, slot, lexicon) for slot in slots]
    observed = [item["winner"] for item in details]
    if any(note is None for note in observed):
        result = "NEURAL_SLOT_SEQUENCE_UNRESOLVED"
    elif observed == catalog:
        result = "EXACT_NEURAL_SLOT_SEQUENCE"
    else:
        result = "NEURAL_SLOT_SEQUENCE_DIFFERENT"
    return {**base, "result": result, "card": str(card.relative_to(ROOT)), "observed": observed, "slots": details}


def main():
    db = load(DB)
    audit = load(AUDIT).get("rows", [])
    audit_by_code = {code(item.get("code")): item for item in audit}
    lexicon = [line.strip() for line in LEXICON.read_text(encoding="utf-8").splitlines() if line.strip()]
    targets = [
        row for row in db
        if audit_by_code.get(code(row.get("code")), {}).get("result") == "READING_NOT_STRICT_ENOUGH"
        and len(row.get("fragranticaSocialCardNotes") or []) == 6
    ]
    ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
    rows = [inspect_target(row, lexicon, ocr) for row in targets]
    payload = {
        "mode": "ANALYSIS_ONLY_NEURAL_OCR_V6",
        "rule": "PaddleOCR recognises every current exact-FID card slot against the complete lexicon; catalog notes are used only for final ordered equality.",
        "acceptance": ">=2 exact neural reads from distinct preprocessing families per slot; confidence >=0.70; zero competing exact labels; complete 2x3 sequence",
        "targets": len(targets),
        "counts": dict(sorted(Counter(item["result"] for item in rows).items())),
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"targets": len(targets), "counts": payload["counts"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
