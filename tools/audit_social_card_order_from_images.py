#!/usr/bin/env python3
"""Independent, conservative audit of Main Notes against card *images*.

This does not use social-card-main-notes(-validated).json as input.  It reads
the visible note-label area from the exact-ID archived Social Card, preserves
its top-to-bottom / left-to-right order, and compares it to the live catalog.

Only a fully readable ordered list is allowed to pass.  Anything unreadable,
missing, or different is intentionally unresolved; it is never an automatic
pass.
"""
from __future__ import annotations

import json
import os
import re
import csv
import io
import subprocess
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
LEXICON = ROOT / "database/audits/fragrantica-note-lexicon.txt"
CARD_DIR = ROOT / "database/fragrantica" / "social-cards" / "images"
OUT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"

# Coordinates on the 1200x1200 English card.  This is the entire notes panel;
# labels are located dynamically, not forced into fixed three-column slots.
# The second row's labels sit below the icon tiles. Stop below the label
# baseline, not at the bottom of the tiles, otherwise the final note is clipped
# before OCR sees it.
CROP = (45, 730, 465, 1145)
SCALE = 3


def code(value):
    return str(value or "").strip().upper()


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def find_card(row):
    c, fid = code(row.get("code")), str(row.get("fragranticaId") or "").strip()
    if not c or not fid:
        return None
    # Prefer the freshly recovered exact-ID card. It is still bound by both
    # Shobi code and FID, and avoids retaining a stale historical rendering.
    current = CARD_DIR / f"current_{c}_{fid}.jpeg"
    if current.is_file():
        return current
    exact = sorted(CARD_DIR.glob(f"*_{c}_{fid}.jpeg")) + sorted(CARD_DIR.glob(f"*_{c}_{fid}.jpg"))
    if exact:
        return exact[0]
    # Historical files can lack the code only when the Fragrantica ID is unique.
    matches = sorted(CARD_DIR.glob(f"*_{fid}.jpeg")) + sorted(CARD_DIR.glob(f"*_{fid}.jpg"))
    return matches[0] if len(matches) == 1 else None


def component_words(words):
    """Join OCR words belonging to one physical label, without fixed columns."""
    n = len(words)
    parent = list(range(n))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = root(i), root(j)
        if a != b:
            parent[b] = a

    for i, a in enumerate(words):
        for j in range(i):
            b = words[j]
            # Same text line: words in one note label are close; distinct notes
            # are separated by the flex-layout gap on the Social Card.
            same_line = abs(a["cy"] - b["cy"]) <= 13
            hgap = max(0, max(a["x"], b["x"]) - min(a["right"], b["right"]))
            if same_line and hgap <= 10:
                union(i, j)
                continue
            # Wrapped labels (for example "Orris Root") overlap horizontally.
            x_overlap = min(a["right"], b["right"]) - max(a["x"], b["x"])
            vgap = max(0, max(a["y"], b["y"]) - min(a["bottom"], b["bottom"]))
            if x_overlap >= -5 and vgap <= 28:
                union(i, j)

    groups = defaultdict(list)
    for i, word in enumerate(words):
        groups[root(i)].append(word)
    out = []
    for items in groups.values():
        items.sort(key=lambda w: (w["y"], w["x"]))
        out.append({
            "raw": " ".join(w["text"] for w in items),
            "x": min(w["x"] for w in items),
            "y": min(w["y"] for w in items),
            "row": min(w["row"] for w in items),
            "confidence": round(min(w["confidence"] for w in items), 1),
        })
    return out


def candidate(raw, lexicon):
    target = norm(raw)
    exact = [name for name in lexicon if norm(name) == target]
    if len(exact) == 1:
        return exact[0], 1.0, 1.0, True
    # Tesseract can reverse the two words of a wrapped label while retaining
    # every visible letter ("Leaf Violet" for the Fragrantica label "Violet
    # Leaf"). This is an OCR layout artefact, not a substitute supplied by
    # the catalog, and is accepted only when that unordered word set has one
    # unique official note name.
    word_set = sorted(target.split())
    reordered_exact = [name for name in lexicon if sorted(norm(name).split()) == word_set]
    if len(reordered_exact) == 1:
        return reordered_exact[0], 1.0, 1.0, True
    # A note label may be complete while the OCR also captures one or two
    # stray glyphs from its icon ("Uk Vetiver", "Sandalwood lf"). Keep this
    # literal only when one official note is a contiguous full word sequence
    # and every leftover token is at most two characters of non-semantic OCR
    # noise. Common connective words deliberately never count as noise.
    artifact_exact = []
    for name in lexicon:
        note_words = norm(name).split()
        for start in range(len(target.split()) - len(note_words) + 1):
            raw_words = target.split()
            if raw_words[start:start + len(note_words)] != note_words:
                continue
            remainder = raw_words[:start] + raw_words[start + len(note_words):]
            if remainder and all(len(word) <= 2 and word not in {"of", "or", "and", "the"} for word in remainder):
                artifact_exact.append(name)
    if len(set(artifact_exact)) == 1:
        return artifact_exact[0], 1.0, 1.0, True
    # For a longer label, one repeated OCR glyph substitution is still direct
    # card evidence when it identifies exactly one note (for example
    # ``lris Pallida`` → ``Iris Pallida`` or ``Labdanu`` → ``Labdanum``).
    # Short labels and multi-character repairs intentionally remain unresolved.
    compact = target.replace(" ", "")
    if len(compact) >= 6:
        def edit_distance_one_or_less(left, right):
            if abs(len(left) - len(right)) > 1:
                return False
            if len(left) == len(right):
                return sum(a != b for a, b in zip(left, right)) <= 1
            if len(left) > len(right):
                left, right = right, left
            index_left = index_right = edits = 0
            while index_left < len(left) and index_right < len(right):
                if left[index_left] == right[index_right]:
                    index_left += 1; index_right += 1
                else:
                    edits += 1; index_right += 1
                    if edits > 1:
                        return False
            return True
        one_glyph = [name for name in lexicon if edit_distance_one_or_less(compact, norm(name).replace(" ", ""))]
        if len(one_glyph) == 1:
            return one_glyph[0], 1.0, 1.0, True
    # Typography only: a card can render a space as joined ("ISOE", "FigLeaf")
    # without changing a single visible letter. Never use this if it is ambiguous.
    compact_target = target.replace(" ", "")
    compact_exact = [name for name in lexicon if norm(name).replace(" ", "") == compact_target]
    if len(compact_exact) == 1:
        return compact_exact[0], 1.0, 1.0, True
    # Some genuine Social Card labels are CSS-truncated with an ellipsis. The
    # visible prefix remains direct evidence only if it has enough letters and
    # identifies one, and only one, official Fragrantica note name.
    if "..." in str(raw):
        prefix = target.split(" ")
        compact_prefix = "".join(prefix)
        prefix_exact = [name for name in lexicon if norm(name).replace(" ", "").startswith(compact_prefix)]
        if len(compact_prefix) >= 8 and len(prefix_exact) == 1:
            return prefix_exact[0], 1.0, 1.0, True
    ranked = sorted(((SequenceMatcher(None, target, norm(name)).ratio(), name) for name in lexicon), reverse=True)
    if not ranked:
        return None, 0.0, 0.0, False
    score, name = ranked[0]
    margin = score - (ranked[1][0] if len(ranked) > 1 else 0)
    return name, round(score, 3), round(margin, 3), False


def parse_attempt(data, lexicon):
    """Return one independent OCR reading, or its reason for not being strict."""
    all_words = []
    for item in data:
        text = " ".join(str(item.get("text") or "").split())
        if not text or sum(ch.isalpha() for ch in text) < 2:
            continue
        try:
            confidence = float(item.get("conf") or -1)
        except Exception:
            confidence = -1
        if confidence < 35:
            continue
        x, y = int(item["left"]) / SCALE, int(item["top"]) / SCALE
        w, h = int(item["width"]) / SCALE, int(item["height"]) / SCALE
        all_words.append({"text": text, "confidence": confidence, "x": x, "right": x + w,
                          "y": y, "bottom": y + h, "cy": y + h / 2})
    headings = [w for w in all_words if norm(w["text"]) == "notes" and w["y"] < 180]
    if not headings:
        return {"strict": False, "reason": "NO_NOTES_PANEL_HEADER", "notes": [], "components": []}
    header_y = min(w["y"] for w in headings)
    bands = ((header_y + 90, header_y + 190), (header_y + 225, header_y + 350))
    words = []
    for word in all_words:
        # Exclude only the panel heading. A later "Notes" token belongs to a real\n        # label such as "Woody Notes", "Green Notes" or "Spicy Notes".\n        if norm(word["text"]) in {"note", "notes"} and abs(word["y"] - header_y) <= 13:\n            continue
        row_index = next((idx for idx, (lo, hi) in enumerate(bands) if lo <= word["cy"] < hi), None)
        if row_index is not None:
            words.append({**word, "row": row_index})
    components = component_words(words)
    parsed, uncertain = [], []
    for item in components:
        name, score, margin, exact = candidate(item["raw"], lexicon)
        record = {**item, "note": name, "score": score, "margin": margin, "exactText": exact}
        # Decorative icon strokes can be OCR'd as 1–3 characters. They are not
        # labels unless they are an exact note name; keeping them would invent
        # a seventh/eighth tile and reject an otherwise complete card reading.
        if not exact and len(norm(item["raw"]).replace(" ", "")) < 4:
            continue
        parsed.append(record)
        if not exact or item["confidence"] < 50:
            uncertain.append(record)
    parsed.sort(key=lambda x: (x["row"], x["x"]))
    observed = [x["note"] for x in parsed if x["note"]]
    strict = bool(observed) and len(observed) <= 6 and not uncertain
    reason = "" if strict else ("NO_READABLE_NOTES" if not observed else
                                 "UNSUPPORTED_NOTE_LAYOUT" if len(observed) > 6 else
                                 "READING_NOT_STRICT_ENOUGH")
    return {"strict": strict, "reason": reason, "notes": observed, "components": parsed,
            "uncertainComponents": uncertain, "notesHeaderY": round(header_y, 1)}


def is_subsequence(shorter, longer):
    pos = 0
    for item in longer:
        if pos < len(shorter) and shorter[pos] == item:
            pos += 1
    return pos == len(shorter)


def compatible_partial_labels(attempt, complete):
    """Accept omissions and literal partial labels from the same physical tiles.

    This is deliberately narrower than fuzzy matching. It handles an OCR pass
    that reads "Fig" from "Fig tree", or "Orange" from "Mandarin Orange",
    after another pass has already read the complete card literally. A different
    literal note, or a label at a tile absent from the complete pass, remains a
    conflict.
    """
    complete_by_tile = {(item["row"], round(item["x"] / 30)): item for item in complete["components"]}
    for item in attempt["components"]:
        reference = complete_by_tile.get((item["row"], round(item["x"] / 30)))
        if not reference:
            return False
        if item["note"] == reference["note"]:
            continue
        raw = norm(item.get("raw", "")).replace(" ", "")
        label = norm(reference["note"]).replace(" ", "")
        # A short read must be a literal contiguous portion of the label at
        # this exact tile. Three characters avoids accepting decorative OCR
        # fragments.
        if len(raw) < 3 or raw not in label:
            return False
    return True


def visible_icon_counts(panel, header_y, rows):
    """Count separated note-icon groups before each visible label row.

    This is a completeness guard: an OCR list cannot pass if the card visibly
    contains more note icons than the labels it read.
    """
    import numpy as np
    pixels = np.asarray(panel)
    counts = []
    for row in range(rows):
        lo, hi = (header_y + 15, header_y + 125) if row == 0 else (header_y + 150, header_y + 260)
        lo, hi = max(0, int(lo)), min(pixels.shape[0], int(hi))
        active = ((pixels[lo:hi, :] < 200).sum(axis=0) > 3).tolist()
        # Join holes inside a detailed icon, but never the larger gap between
        # two separately rendered note tiles.
        i = 0
        while i < len(active):
            if active[i]:
                i += 1; continue
            j = i
            while j < len(active) and not active[j]: j += 1
            if i > 0 and j < len(active) and j - i <= 14:
                for k in range(i, j): active[k] = True
            i = j
        segments, start = [], None
        for x, value in enumerate(active + [False]):
            if value and start is None: start = x
            if start is not None and not value:
                if x - start >= 20: segments.append((start, x))
                start = None
        counts.append(len(segments))
    return counts


def ocr_panels(source_panel):
    """Return independent renderings of the same visible notes panel.

    A label is never supplied by the catalog: every candidate still comes from
    Tesseract reading the card itself. The renderings only make a faint or
    anti-aliased glyph legible to the same original reader.
    """
    base = ImageOps.autocontrast(source_panel)
    renderings = [
        ("contrast-200", ImageEnhance.Contrast(base).enhance(2.0)),
        ("contrast-260", ImageEnhance.Contrast(base).enhance(2.6)),
        ("threshold-185", base.point(lambda value: 0 if value < 185 else 255)),
        ("threshold-215", base.point(lambda value: 0 if value < 215 else 255)),
    ]
    out = []
    for variant, panel in renderings:
        panel = panel.resize((panel.width * SCALE, panel.height * SCALE), Image.Resampling.LANCZOS)
        if variant.startswith("contrast"):
            panel = panel.filter(ImageFilter.SHARPEN)
        payload = io.BytesIO()
        panel.save(payload, format="PNG")
        out.append((variant, payload.getvalue()))
    return out


def slotwise_direct_consensus(attempts, expected):
    """Prove each visible 2×3 note position in two renderings of the card."""
    support = [set() for _ in expected]
    conflicts = []
    for attempt in attempts:
        for item in attempt["components"]:
            row = item.get("row")
            if row not in (0, 1):
                continue
            column = min(2, max(0, round((item.get("x", 0) - 32) / 120)))
            position = row * 3 + column
            if position >= len(expected):
                continue
            direct = item["exactText"] or (
                item["confidence"] >= 60 and item["score"] >= 0.88 and item["margin"] >= 0.15
            )
            if not direct:
                continue
            if item["note"] == expected[position]:
                support[position].add(attempt["variant"])
            elif item["exactText"]:
                conflicts.append({"position": position, "note": item["note"], "variant": attempt["variant"]})
    if conflicts or not expected or any(len(variants) < 2 for variants in support):
        return None
    return {"variantsPerPosition": [sorted(variants) for variants in support]}


def direct_position_sequence(attempts, icon_counts):
    """Return a complete sequence proved position-by-position from the card.

    This differs from ``slotwise_direct_consensus`` in one important respect:
    it does not start from the catalog sequence.  That lets a Social Card
    correct a saved note that is plainly different (for example ``Bitter
    Orange`` versus ``Orange``), while retaining a stricter standard: every
    physical position needs two rendering variants with the same literal
    label, and even one literal competing label rejects the position.
    """
    per_position = defaultdict(lambda: defaultdict(set))
    for attempt in attempts:
        variant = attempt.get("variant")
        if not variant:
            continue
        for item in attempt["components"]:
            if not item.get("exactText"):
                continue
            row = item.get("row")
            if row not in (0, 1):
                continue
            column = min(2, max(0, round((item.get("x", 0) - 32) / 120)))
            per_position[(row, column)][item["note"]].add(variant)

    winners = []
    for row in range(2):
        row_positions = [(column, names) for (item_row, column), names in per_position.items() if item_row == row]
        # The exact number of readable physical positions must agree with the
        # visible icon tiles.  This prevents an omitted or spurious tile from
        # becoming a complete sequence.
        if len(row_positions) != icon_counts[row]:
            return None
        for column, names in row_positions:
            # A literal competing note, even in only one rendering, is a
            # contradiction rather than something to decide from the catalog.
            if len(names) != 1:
                return None
            note, variants = next(iter(names.items()))
            if len(variants) < 2:
                return None
            winners.append((row, column, note, sorted(variants)))

    winners.sort(key=lambda item: (item[0], item[1]))
    if not winners:
        return None
    return {
        "notes": [note for _, _, note, _ in winners],
        "evidence": [
            {"row": row, "column": column, "note": note, "variants": variants}
            for row, column, note, variants in winners
        ],
    }


def soft_ordered_match(attempt, expected):
    """Accept a non-literal OCR token only with strong, direct card evidence."""
    components = attempt["components"]
    if len(components) != len(expected) or attempt["notes"] != expected:
        return False
    return all(
        item["exactText"] or (
            item["confidence"] >= 60 and item["score"] >= 0.90 and item["margin"] >= 0.15
        )
        for item in components
    )


def direct_tile_reading(source_panel, header_y, lexicon):
    """Read the six physical label areas on a standard 2×3 Social Card.

    This is still the original Tesseract reader operating on the same card.
    It is used only after the whole-panel pass fails, and requires the exact
    visible text in every tile to recur in two independent renderings.
    """
    slots = []
    variants = [
        ("tile-contrast-260", lambda image: ImageEnhance.Contrast(ImageOps.autocontrast(image)).enhance(2.6).filter(ImageFilter.SHARPEN)),
        ("tile-threshold-185", lambda image: ImageOps.autocontrast(image).point(lambda value: 0 if value < 185 else 255)),
        ("tile-threshold-215", lambda image: ImageOps.autocontrast(image).point(lambda value: 0 if value < 215 else 255)),
    ]
    for row, (top, bottom) in enumerate(((header_y + 115, header_y + 220), (header_y + 270, header_y + 380))):
        for col in range(3):
            left, right = col * 140, (col + 1) * 140
            box = (max(0, int(left)), max(0, int(top)), min(source_panel.width, int(right)), min(source_panel.height, int(bottom)))
            if box[2] <= box[0] or box[3] <= box[1]:
                return None
            raw_reads = []
            for variant, transform in variants:
                tile = transform(source_panel.crop(box)).resize(((box[2] - box[0]) * 5, (box[3] - box[1]) * 5), Image.Resampling.LANCZOS)
                payload = io.BytesIO()
                tile.save(payload, format="PNG")
                run = subprocess.run(
                    ["tesseract", "stdin", "stdout", "--psm", "7", "-l", "eng", "tsv"],
                    input=payload.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                    env={**os.environ, "OMP_THREAD_LIMIT": "1"}, timeout=12,
                )
                words = []
                for item in csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t"):
                    text = " ".join(str(item.get("text") or "").split())
                    try:
                        confidence = float(item.get("conf") or -1)
                    except Exception:
                        confidence = -1
                    if text and sum(char.isalpha() for char in text) >= 2 and confidence >= 45:
                        words.append((int(item.get("left") or 0), text, confidence))
                words.sort()
                raw = " ".join(word for _, word, _ in words)
                if not raw:
                    raw_reads.append({"variant": variant, "raw": raw, "note": None, "exact": False})
                    continue
                name, score, margin, exact = candidate(raw, lexicon)
                raw_reads.append({"variant": variant, "raw": raw, "note": name, "score": score, "margin": margin,
                                  "confidence": min(conf for _, _, conf in words), "exact": exact})
            exact_by_name = defaultdict(list)
            for read in raw_reads:
                if read.get("exact"):
                    exact_by_name[read["note"]].append(read)
            winners = [(name, reads) for name, reads in exact_by_name.items() if len({r["variant"] for r in reads}) >= 2]
            if len(winners) != 1:
                return None
            winner, winner_reads = winners[0]
            # An exact competing label in the same visible tile is a conflict,
            # not a tie to resolve from the catalog.
            if any(read.get("exact") and read.get("note") != winner for read in raw_reads):
                return None
            slots.append({"row": row, "col": col, "note": winner, "reads": raw_reads})
    return {"notes": [slot["note"] for slot in slots], "slots": slots}


def inspect(task):
    row, card_text, lexicon = task
    card = Path(card_text)
    base = {"code": code(row.get("code")), "fragranticaId": str(row.get("fragranticaId") or ""),
            "card": str(card.relative_to(ROOT)) if card_text else None,
            "catalogNotes": list(row.get("fragranticaSocialCardNotes") or [])}
    if not card_text:
        return {**base, "result": "NO_EXACT_CARD"}
    try:
        with Image.open(card) as src:
            if src.width < 800 or src.height < 800 or src.height / src.width < 0.85:
                return {**base, "result": "UNSUPPORTED_CARD_GEOMETRY", "size": [src.width, src.height]}
            sx, sy = src.width / 1200, src.height / 1200
            x1, y1, x2, y2 = CROP
            source_panel = src.crop((round(x1 * sx), round(y1 * sy), round(x2 * sx), round(y2 * sy))).convert("L").resize((420, 380), Image.Resampling.LANCZOS)
        attempts = []
        for variant, payload in ocr_panels(source_panel):
            for psm in (6, 11):
                run = subprocess.run(
                    ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
                    input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                    # Tesseract otherwise creates its own large OpenMP pool per card;
                    # parallel card workers would then oversubscribe the machine.
                    env={**os.environ, "OMP_THREAD_LIMIT": "1"}, timeout=12,
                )
                attempts.append({"variant": variant, "psm": psm, **parse_attempt(list(csv.DictReader(
                    io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t")), lexicon)})
    except Exception as exc:
        return {**base, "result": "OCR_ERROR", "error": str(exc)}
    strict = [a for a in attempts if a["strict"]]
    # Do not return here. A card can have no byte-for-byte OCR pass while
    # still having a complete, high-confidence ordered reading reproduced by
    # independent renderings below.
    # An exact high-confidence reading of every visible label is proof by
    # itself. A second OCR layout pass may legitimately omit a wrapped label;
    # an omission is not evidence against the complete reading. It must,
    # however, remain an ordered subsequence. Any competing label still fails.
    exact = [a for a in strict if a["notes"] == base["catalogNotes"]]
    if exact:
        selected = max(exact, key=lambda a: len(a["components"]))
        if not all(is_subsequence(a["notes"], selected["notes"]) for a in strict):
            # The original reader can truncate a multi-word label in one
            # layout pass. Admit that only when the whole exact sequence was
            # independently read in two image renderings, every visible icon
            # has a matching label, and each non-identical read is a literal
            # prefix at the same physical tile.
            headers = [attempt.get("notesHeaderY") for attempt in attempts if attempt.get("notesHeaderY") is not None]
            exact_variants = {attempt["variant"] for attempt in exact}
            icon_counts = visible_icon_counts(source_panel, min(headers), 2) if headers else []
            label_counts = [sum(1 for item in selected["components"] if item["row"] == i) for i in range(2)]
            if not (
                len(exact_variants) >= 2
                and label_counts == icon_counts
                and all(compatible_partial_labels(attempt, selected) for attempt in strict)
            ):
                return {**base, "result": "READING_NOT_STRICT_ENOUGH", "attempts": attempts}
            proof = "COMPLETE_EXACT_MULTIPASS; PARTIAL_READS_LITERAL_SAME_TILE; ICON_COUNTS_MATCH"
        else:
            label_counts = [sum(1 for item in selected["components"] if item["row"] == i) for i in range(2)]
            proof = "ALL_LABELS_EXACT_HIGH_CONFIDENCE; OTHER_READS_ORDERED_SUBSEQUENCES"
        return {**base, "result": "EXACT_ORDERED_MATCH", "observedNotes": selected["notes"],
                "components": selected["components"], "notesHeaderY": selected["notesHeaderY"],
                "labelCounts": label_counts, "proof": proof,
                "attempts": attempts}
    # When the catalog itself is wrong, a card must be allowed to correct it.
    # This requires a complete physical-card reading: the number of labels in
    # each row must equal the visible icon count, the same full sequence must
    # be literal OCR in at least two rendering variants, and every other
    # literal read must be an ordered subsequence (never a contradiction).
    headers = [attempt.get("notesHeaderY") for attempt in attempts if attempt.get("notesHeaderY") is not None]
    if headers:
        icon_counts = visible_icon_counts(source_panel, min(headers), 2)
        complete = []
        for attempt in strict:
            label_counts = [sum(1 for item in attempt["components"] if item["row"] == row) for row in range(2)]
            if label_counts == icon_counts and len(attempt["notes"]) == sum(icon_counts):
                complete.append((attempt, label_counts))
        grouped = defaultdict(list)
        for attempt, label_counts in complete:
            grouped[tuple(attempt["notes"])].append((attempt, label_counts))
        certified = []
        for sequence, reads in grouped.items():
            variants = {attempt["variant"] for attempt, _ in reads}
            if len(variants) < 2:
                continue
            if not all(is_subsequence(other["notes"], list(sequence)) for other in strict):
                continue
            certified.append((list(sequence), reads, variants))
        if len(certified) == 1:
            sequence, reads, variants = certified[0]
            selected, label_counts = max(reads, key=lambda item: len(item[0]["components"]))
            base_result = {**base, "observedNotes": sequence, "components": selected["components"],
                           "notesHeaderY": selected["notesHeaderY"], "labelCounts": label_counts,
                           "iconCounts": icon_counts, "attempts": attempts,
                           "proof": "COMPLETE_PHYSICAL_CARD_EXACT_MULTIPASS; ICON_COUNTS_MATCH"}
            if sequence == base["catalogNotes"]:
                return {**base_result, "result": "EXACT_ORDERED_MATCH"}
            return {**base_result, "result": "EXACT_ORDERED_CARD_NOTES_DIFFER"}
        # Whole-panel OCR can miss an otherwise clear label, especially when
        # the saved catalog is the value that differs.  Reuse the same panel
        # OCR by physical position: two independent rendering variants must
        # literally read every visible tile, and the tile count must equal the
        # card's icon count.  No catalog text is used to choose a label.
        positional = direct_position_sequence(attempts, icon_counts)
        if positional:
            sequence = positional["notes"]
            base_result = {
                **base,
                "observedNotes": sequence,
                "iconCounts": icon_counts,
                "labelCounts": icon_counts,
                "attempts": attempts,
                "positionEvidence": positional["evidence"],
                "proof": "POSITIONWISE_LITERAL_CARD_CONSENSUS; TWO_RENDERINGS_PER_TILE; ICON_COUNTS_MATCH",
            }
            if sequence == base["catalogNotes"]:
                return {**base_result, "result": "EXACT_ORDERED_MATCH"}
            return {**base_result, "result": "EXACT_ORDERED_CARD_NOTES_DIFFER"}
    # For the standard 2×3 panel, isolate each physical label and require two
    # exact direct readings per tile. This avoids a neighboring icon or label
    # contaminating the whole-panel OCR while preserving the same source and
    # exact ordering rule.
    headers = [attempt.get("notesHeaderY") for attempt in attempts if attempt.get("notesHeaderY") is not None]
    if len(base["catalogNotes"]) == 6 and headers:
        tiles = direct_tile_reading(source_panel, min(headers), lexicon)
        if tiles and tiles["notes"] == base["catalogNotes"]:
            return {**base, "result": "EXACT_ORDERED_MATCH", "observedNotes": tiles["notes"],
                    "tileEvidence": tiles["slots"],
                    "proof": "SIX_PHYSICAL_LABELS_EXACT_MULTIPASS; ORDERED_SEQUENCE_EXACT",
                    "attempts": attempts}
    # A full card can be proven even when each clear label is recognized by a
    # different rendering. Every physical position must independently agree in
    # two renderings; an exact competing label rejects the card.
    slotwise = slotwise_direct_consensus(attempts, base["catalogNotes"])
    if slotwise:
        return {**base, "result": "EXACT_ORDERED_MATCH", "observedNotes": base["catalogNotes"],
                "proof": "SLOTWISE_DIRECT_CARD_CONSENSUS; TWO_RENDERINGS_PER_POSITION",
                "slotwiseEvidence": slotwise, "attempts": attempts}

    # Some labels are visibly clear but Tesseract adds/removes a single glyph
    # (for example "be Honey"). They remain direct image evidence only when
    # the complete expected sequence is independently read by three rendering
    # variants, or by two variants with one literal reading. This is the same
    # reader and same card; it simply avoids rejecting a correct visible label
    # because one rendering was not byte-for-byte OCR text.
    supported = [a for a in attempts if soft_ordered_match(a, base["catalogNotes"])]
    variants = {a["variant"] for a in supported}
    literal = [a for a in supported if a["strict"]]
    consensus = len(variants) >= 3 or (len(variants) >= 2 and literal)
    if consensus:
        selected = max(supported, key=lambda a: (sum(item["exactText"] for item in a["components"]), min(item["confidence"] for item in a["components"])))
        label_counts = [sum(1 for item in selected["components"] if item["row"] == i) for i in range(2)]
        return {**base, "result": "EXACT_ORDERED_MATCH", "observedNotes": selected["notes"],
                "components": selected["components"], "notesHeaderY": selected["notesHeaderY"],
                "labelCounts": label_counts,
                "proof": "MULTIPASS_DIRECT_CARD_CONSENSUS; ORDERED_SEQUENCE_EXACT",
                "multipassEvidence": {"variants": sorted(variants), "readings": len(supported), "literalReadings": len(literal)},
                "attempts": attempts}
    # A non-matching OCR list is never used to rewrite catalog data in this
    # gate. It may be a partial reading or a misread label, so it remains
    # unresolved until there is separate, repeatable evidence of the complete
    # sequence. This audit promotes proof; it does not infer replacements.
    return {**base, "result": "READING_NOT_STRICT_ENOUGH", "attempts": attempts}


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    only_current_yellows = os.environ.get("SOCIAL_CARD_AUDIT_ONLY_CURRENT_YELLOWS") == "1"
    existing_by_code = {}
    if only_current_yellows:
        # Preserve certified rows exactly as they are. This mode reuses the
        # original reader only on the current unresolved set.
        existing = json.loads(OUT.read_text(encoding="utf-8-sig"))
        existing_by_code = {code(item.get("code")): item for item in existing.get("rows", [])}
        missing = [code(row.get("code")) for row in rows if code(row.get("code")) not in existing_by_code]
        if missing:
            raise SystemExit(f"Canonical audit is incomplete; refusing targeted overwrite: {missing[:10]}")
        target_rows = [
            row for row in rows
            if str((row.get("validationAudit") or {}).get("status") or "").lower() == "yellow"
        ]
    else:
        target_rows = rows
    lexicon = [line.strip() for line in LEXICON.read_text(encoding="utf-8").splitlines() if line.strip()]
    tasks = [(row, str(find_card(row)) if find_card(row) else "", lexicon) for row in target_rows]
    # Hosted CI runners have less headroom than a development machine. Keep
    # the default fast locally, while allowing workflows to lower concurrency.
    requested_workers = int(os.environ.get("SOCIAL_CARD_AUDIT_WORKERS", "6"))
    workers = max(1, min(requested_workers, 6, (os.cpu_count() or 2)))
    batch_size = max(1, int(os.environ.get("SOCIAL_CARD_AUDIT_BATCH", str(len(tasks)))))
    results = []
    for start in range(0, len(tasks), batch_size):
        batch = tasks[start:start + batch_size]
        # Restarting the small OCR worker pool between batches keeps hosted CI
        # memory bounded without changing what is read or accepted as proof.
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(inspect, task) for task in batch]
            for i, future in enumerate(as_completed(futures), start + 1):
                results.append(future.result())
                if i % 100 == 0:
                    print(f"audited {i}/{len(tasks)}", flush=True)
    if only_current_yellows:
        result_by_code = {code(item.get("code")): item for item in results}
        results = [result_by_code.get(code(row.get("code")), existing_by_code[code(row.get("code"))]) for row in rows]
    results.sort(key=lambda r: code(r["code"]))
    counts = Counter(r["result"] for r in results)
    report = {
        "rule": "The exact archived Social Card image is read independently. The visible sequence must match catalog Main Notes position-by-position; count-only equality never passes.",
        "catalogRows": len(rows), "targetedCurrentYellows": len(target_rows) if only_current_yellows else None,
        "results": dict(sorted(counts.items())), "rows": results,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"catalogRows": len(rows), "targetedCurrentYellows": len(target_rows) if only_current_yellows else None, "results": report["results"], "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
