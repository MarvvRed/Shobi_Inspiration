#!/usr/bin/env python3
"""Non-OCR visual-template audit for unresolved six-note Social Cards.

This is deliberately an analysis-only path.  It does not import or invoke any
OCR implementation and it never uses target catalog notes while recognising a
card.  Instead, it learns two independent raster templates for each note from
already strict ``EXACT_ORDERED_MATCH`` Social Cards:

* the rendered note-label glyph silhouette; and
* the note-icon colour/shape crop.

Only current exact-FID target cards are examined.  A candidate is reported as
an exact sequence only when every physical slot has the same unique winning
note in *both* visual channels, with conservative absolute scores and margins.
The target catalog sequence is consulted only after that image-derived sequence
has been fixed.  This report has no apply step yet: its calibration and every
candidate must be independently verified before it can affect a yellow badge.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
CARDS = ROOT / "database/fragrantica/social-cards/images"
OUT = ROOT / "database/audits/current-yellow-visual-template-v5.json"

# Canonical physical grid coordinates, expressed in the 1200px Social Card
# coordinate space.  Unlike V4 these crops are never passed to Tesseract.
ROWS = ((848, 950), (978, 1100))
COLS = ((47, 185), (187, 325), (327, 465))
LABEL_MIN_SCORE = 0.935
ICON_MIN_SCORE = 0.900
LABEL_MIN_MARGIN = 0.070
ICON_MIN_MARGIN = 0.050


def code(value):
    return str(value or "").strip().upper()


def norm(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def unique_current_card(shobi_code, fid):
    found = []
    for ext in ("jpeg", "jpg", "png", "webp"):
        found.extend(CARDS.glob(f"current_{shobi_code}_{fid}.{ext}"))
    found = sorted(set(found))
    return found[0] if len(found) == 1 else None


def audit_card(item, fid):
    path = ROOT / str(item.get("card") or "")
    # An archived source is allowed only when it remains visibly bound to the
    # audited FID.  This prevents accidental borrowing of another card.
    if not path.is_file() or not re.search(rf"(?:^|[_-]){re.escape(fid)}(?:\.[^.]+)?$", path.name):
        return None
    return path


def slots(path):
    with Image.open(path) as source:
        if source.width < 800 or source.height < 800 or source.height / source.width < 0.85:
            return None
        image = source.convert("RGB").resize((1200, 1200), Image.Resampling.LANCZOS)
    return [image.crop((x1, y1, x2, y2)) for y1, y2 in ROWS for x1, x2 in COLS]


def unit(values):
    vec = np.asarray(values, dtype=np.float32).reshape(-1)
    length = float(np.linalg.norm(vec))
    return vec / length if length > 1e-7 else None


def label_feature(tile):
    # The lower part of a physical cell contains the rendered note label.  A
    # binary dark-glyph mask suppresses the card background without reading it.
    crop = tile.crop((2, 38, tile.width - 2, tile.height - 1)).convert("L")
    crop = ImageOps.autocontrast(crop).resize((28, 16), Image.Resampling.LANCZOS)
    pixels = np.asarray(crop, dtype=np.float32)
    return unit(np.clip((205.0 - pixels) / 205.0, 0.0, 1.0))


def icon_feature(tile):
    # The upper part is a visual icon region.  Keep RGB information; its
    # rendering is independent from the text-shape channel above.
    crop = tile.crop((5, 0, tile.width - 5, 62)).resize((18, 18), Image.Resampling.LANCZOS)
    pixels = np.asarray(crop, dtype=np.float32)
    # White/card-background is removed before cosine comparison.
    return unit(np.clip((248.0 - pixels) / 248.0, 0.0, 1.0))


def build_prototypes(audit_rows, db_by_code):
    samples = defaultdict(lambda: {"label": [], "icon": [], "fids": set(), "cards": set()})
    source_count = 0
    for item in audit_rows:
        if item.get("result") != "EXACT_ORDERED_MATCH":
            continue
        shobi_code = code(item.get("code"))
        row = db_by_code.get(shobi_code)
        observed = list(item.get("observedNotes") or [])
        if not row or len(observed) != 6 or observed != list(row.get("fragranticaSocialCardNotes") or []):
            continue
        fid = str(row.get("fragranticaId") or "").strip()
        card = audit_card(item, fid)
        if not fid or not card:
            continue
        cells = slots(card)
        if not cells:
            continue
        source_count += 1
        for note, cell in zip(observed, cells):
            label, icon = label_feature(cell), icon_feature(cell)
            if label is None or icon is None:
                continue
            group = samples[note]
            group["label"].append(label)
            group["icon"].append(icon)
            group["fids"].add(fid)
            group["cards"].add(str(card.relative_to(ROOT)))

    names, labels, icons, support = [], [], [], {}
    for note in sorted(samples, key=norm):
        group = samples[note]
        # A template is only accepted when at least two distinct strictly
        # audited FIDs supplied it.  This prevents one card from becoming an
        # implicit per-perfume whitelist.
        if len(group["fids"]) < 2:
            continue
        label = unit(np.mean(np.stack(group["label"]), axis=0))
        icon = unit(np.mean(np.stack(group["icon"]), axis=0))
        if label is None or icon is None:
            continue
        names.append(note)
        labels.append(label)
        icons.append(icon)
        support[note] = {"distinctFids": len(group["fids"]), "cards": len(group["cards"])}
    if not names:
        raise SystemExit("No independent six-note visual templates could be built")
    return names, np.stack(labels), np.stack(icons), support, source_count


def winner(scores, names):
    order = np.argsort(scores)[::-1]
    first, second = int(order[0]), int(order[1])
    return {
        "note": names[first],
        "score": round(float(scores[first]), 4),
        "runnerUp": names[second],
        "runnerUpScore": round(float(scores[second]), 4),
        "margin": round(float(scores[first] - scores[second]), 4),
    }


def inspect_target(row, label_matrix, icon_matrix, names):
    shobi_code = code(row.get("code"))
    fid = str(row.get("fragranticaId") or "").strip()
    catalog = list(row.get("fragranticaSocialCardNotes") or [])
    base = {"code": shobi_code, "fid": fid, "catalog": catalog}
    card = unique_current_card(shobi_code, fid)
    if not card:
        return {**base, "result": "NO_UNIQUE_CURRENT_EXACT_FID_CARD"}
    cells = slots(card)
    if not cells:
        return {**base, "result": "UNSUPPORTED_CARD_GEOMETRY", "card": str(card.relative_to(ROOT))}
    details, observed, complete = [], [], True
    for index, cell in enumerate(cells, 1):
        label, icon = label_feature(cell), icon_feature(cell)
        if label is None or icon is None:
            complete = False
            details.append({"slot": index, "result": "EMPTY_VISUAL_FEATURE"})
            continue
        text_hit = winner(label_matrix @ label, names)
        icon_hit = winner(icon_matrix @ icon, names)
        strong = (
            text_hit["note"] == icon_hit["note"] and
            text_hit["score"] >= LABEL_MIN_SCORE and text_hit["margin"] >= LABEL_MIN_MARGIN and
            icon_hit["score"] >= ICON_MIN_SCORE and icon_hit["margin"] >= ICON_MIN_MARGIN
        )
        details.append({"slot": index, "label": text_hit, "icon": icon_hit, "strong": strong})
        if not strong:
            complete = False
        else:
            observed.append(text_hit["note"])
    result = "VISUAL_TEMPLATE_SEQUENCE_UNRESOLVED"
    if complete and observed == catalog:
        result = "EXACT_VISUAL_TEMPLATE_SEQUENCE"
    elif complete:
        result = "VISUAL_TEMPLATE_SEQUENCE_DIFFERENT"
    return {**base, "result": result, "card": str(card.relative_to(ROOT)), "observed": observed, "slots": details}


def main():
    db = load(DB)
    audit = load(AUDIT).get("rows", [])
    db_by_code = {code(row.get("code")): row for row in db}
    names, labels, icons, support, source_cards = build_prototypes(audit, db_by_code)
    targets = [
        db_by_code[code(item.get("code"))]
        for item in audit
        if item.get("result") == "READING_NOT_STRICT_ENOUGH"
        and code(item.get("code")) in db_by_code
        and len(db_by_code[code(item.get("code"))].get("fragranticaSocialCardNotes") or []) == 6
    ]
    results = [inspect_target(row, labels, icons, names) for row in targets]
    counts = Counter(item["result"] for item in results)
    payload = {
        "mode": "ANALYSIS_ONLY_NON_OCR_DUAL_CHANNEL_VISUAL_TEMPLATE_V5",
        "rule": "Target catalog notes are used only after label-raster and icon-raster channels independently yield a complete physical-slot sequence.",
        "thresholds": {
            "labelMinScore": LABEL_MIN_SCORE, "labelMinMargin": LABEL_MIN_MARGIN,
            "iconMinScore": ICON_MIN_SCORE, "iconMinMargin": ICON_MIN_MARGIN,
        },
        "source": {"strictSixNoteCards": source_cards, "templateNotes": len(names), "support": support},
        "targets": len(targets),
        "counts": dict(sorted(counts.items())),
        "rows": results,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sources": source_cards, "templates": len(names), "targets": len(targets), "counts": payload["counts"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
