#!/usr/bin/env python3
"""Independent Tesseract re-check for V6 neural exact Social Card candidates.

This script neither imports V6 nor reuses its crop/preprocessing code.  It
starts from its report only as a work list, resolves the current exact-FID
image again, derives every slot from pixels with separately inset geometry,
and fails closed on a single non-exact or competing read.
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
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# The workflow trigger below intentionally starts the verifier after a bot-published V6 report.
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
V6 = ROOT / "database/audits/current-yellow-neural-ocr-v6.json"
LEXICON = ROOT / "database/audits/fragrantica-note-lexicon.txt"
CARDS = ROOT / "database/fragrantica/social-cards/images"
OUT = ROOT / "database/audits/current-yellow-neural-ocr-v6-independent-verification.json"


def code(value): return str(value or "").strip().upper()


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def load(path): return json.loads(path.read_text(encoding="utf-8-sig"))


def current_cards(shobi_code, fid):
    return sorted({path for ext in ("jpeg", "jpg", "png", "webp") for path in CARDS.glob(f"current_{shobi_code}_{fid}.{ext}")})


def resolve_exact_fid_card(shobi_code, fid):
    current = current_cards(shobi_code, fid)
    if len(current) == 1:
        return current[0], "CURRENT_EXACT_FID_CARD", current
    archived = sorted({path for ext in ("jpeg", "jpg", "png", "webp") for path in CARDS.glob(f"*_{shobi_code}_{fid}.{ext}")})
    if not current and len(archived) == 1:
        return archived[0], "ARCHIVED_EXACT_CODE_AND_FID_CARD", archived
    return None, None, current if current else archived


def notes_panel(path):
    with Image.open(path) as source:
        if source.width < 800 or source.height < 800 or source.height / source.width < .85:
            return None
        image = source.convert("RGB").resize((1200, 1200), Image.Resampling.LANCZOS)
    # This includes both known official layouts: labels above icons and labels
    # below icons.  It is deliberately wider than a fixed-label crop.
    return image.crop((45, 700, 465, 1145))


def variants(tile):
    gray = ImageOps.autocontrast(tile.convert("L"))
    sharp = ImageEnhance.Contrast(gray).enhance(2.4).filter(ImageFilter.UnsharpMask(1, 190, 1))
    return {
        "equalized": ImageOps.equalize(gray),
        "threshold175": sharp.point(lambda value: 255 if value > 175 else 0),
        "threshold205": sharp.point(lambda value: 255 if value > 205 else 0),
    }


def read_tesseract(image, psm):
    payload = io.BytesIO(); image.save(payload, format="PNG")
    result = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
        input=payload.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=12, check=True, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    )
    words = []
    confidence = []
    for row in csv.DictReader(io.StringIO(result.stdout.decode("utf-8", "replace")), delimiter="\t"):
        text = " ".join(str(row.get("text") or "").split())
        if not text: continue
        try: value = float(row.get("conf") or -1)
        except ValueError: value = -1
        if value >= 35:
            words.append(text); confidence.append(value)
    return " ".join(words), min(confidence) if confidence else -1


def read_positioned_words(image, psm, scale):
    payload = io.BytesIO(); image.save(payload, format="PNG")
    result = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
        input=payload.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=16, check=True, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    )
    words = []
    for row in csv.DictReader(io.StringIO(result.stdout.decode("utf-8", "replace")), delimiter="\t"):
        text = " ".join(str(row.get("text") or "").split())
        if not text: continue
        try: confidence = float(row.get("conf") or -1)
        except ValueError: confidence = -1
        if confidence < 35: continue
        try:
            x = (float(row.get("left") or 0) + float(row.get("width") or 0) / 2) / scale
            y = (float(row.get("top") or 0) + float(row.get("height") or 0) / 2) / scale
        except ValueError:
            continue
        words.append({"text": text, "x": x, "y": y, "confidence": confidence})
    return words


def exact(raw, lexicon):
    matches = [note for note in lexicon if norm(note) == norm(raw)]
    return matches[0] if len(matches) == 1 else None


def exact_phrase(words, lexicon):
    """Find one exact lexicon phrase in a spatial cell, never a fuzzy match."""
    hits = set()
    for start in range(len(words)):
        for end in range(start + 1, len(words) + 1):
            note = exact(" ".join(item["text"] for item in words[start:end]), lexicon)
            if note: hits.add(note)
    return next(iter(hits)) if len(hits) == 1 else None


def two_column_notes(words, lexicon):
    """Derive the two top-to-bottom labels in one physical column.

    Their vertical gap is not fixed: long top labels can occupy two lines.
    Select two non-overlapping exact lexicon phrases, preferring the pair that
    accounts for most recognised words.  Ties fail closed.
    """
    spans = []
    for start in range(len(words)):
        for end in range(start + 1, len(words) + 1):
            note = exact(" ".join(item["text"] for item in words[start:end]), lexicon)
            if note:
                spans.append((start, end, note))
    pairs = []
    for first in spans:
        for second in spans:
            if first[1] <= second[0]:
                pairs.append((first, second))
    if not pairs:
        return None, None
    best_width = max((first[1] - first[0]) + (second[1] - second[0]) for first, second in pairs)
    best = [(first, second) for first, second in pairs if (first[1] - first[0]) + (second[1] - second[0]) == best_width]
    meanings = {(first[2], second[2]) for first, second in best}
    return next(iter(meanings)) if len(meanings) == 1 else (None, None)


def panel_sequence(panel, lexicon):
    """Read all six labels spatially from the complete Notes panel.

    The two rows are separated by their physical vertical bands, while text
    stays attached to its closest column whether it sits above or below the
    corresponding icon.  Recognition searches the full note lexicon only.
    """
    scale = 5
    sequences = []
    for family, image in variants(panel).items():
        scaled = image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
        for psm in (11, 12):
            try: words = read_positioned_words(scaled, psm, scale)
            except Exception as exc:
                sequences.append({"family": family, "psm": psm, "error": str(exc)}); continue
            columns = [[] for _ in range(3)]
            for word in words:
                # Header/footer and the Fragrantica logo are outside the two
                # label bands.  The rows themselves are inferred per column.
                if word["y"] < 105 or word["y"] > 415: continue
                column = min(range(3), key=lambda index: abs(word["x"] - (75 + index * 120)))
                columns[column].append(word)
            pairs, raw = [], []
            for column in columns:
                column.sort(key=lambda item: (item["y"], item["x"]))
                raw.append(" ".join(item["text"] for item in column))
                pairs.append(two_column_notes(column, lexicon))
            notes = [pairs[index][0] for index in range(3)] + [pairs[index][1] for index in range(3)]
            sequences.append({"family": family, "psm": psm, "rawSlots": raw, "observed": notes, "complete": all(notes)})
    complete = [item for item in sequences if item.get("complete")]
    counts = Counter(tuple(item["observed"]) for item in complete)
    winner, count = counts.most_common(1)[0] if counts else (None, 0)
    winner_reads = [item for item in complete if tuple(item["observed"]) == winner]
    families = sorted({item["family"] for item in winner_reads})
    competitors = [list(sequence) for sequence in counts if sequence != winner]
    # V6 already requires two exact neural preprocessing reads.  This second,
    # different engine must independently derive one complete exact sequence;
    # a second Tesseract variant is not treated as a substitute for that
    # cross-engine independence.  Any complete competing sequence still fails.
    return {"observed": list(winner) if winner and count >= 1 and not competitors else None, "exactReads": count, "families": families, "competitors": competitors, "reads": sequences}


def inspect_slot(tile, lexicon):
    reads = []
    for family, image in variants(tile).items():
        scaled = image.resize((image.width * 7, image.height * 7), Image.Resampling.LANCZOS)
        for psm in (6, 7, 13):
            try: raw, confidence = read_tesseract(scaled, psm)
            except Exception as exc:
                reads.append({"family": family, "psm": psm, "error": str(exc)}); continue
            note = exact(raw, lexicon)
            reads.append({"family": family, "psm": psm, "raw": raw, "confidence": round(confidence, 2), "exactNote": note, "eligible": bool(note and confidence >= 35)})
    exact_reads = [read for read in reads if read.get("eligible")]
    counts = Counter(read["exactNote"] for read in exact_reads)
    winner, count = counts.most_common(1)[0] if counts else (None, 0)
    winner_reads = [read for read in exact_reads if read["exactNote"] == winner]
    families = sorted({read["family"] for read in winner_reads})
    modes = sorted({f"{read['family']}:psm{read['psm']}" for read in winner_reads})
    competitors = sorted(note for note in counts if note != winner)
    return {"winner": winner if count >= 2 and len(families) >= 2 and not competitors else None, "exactReads": count, "families": families, "modes": modes, "competitors": competitors, "reads": reads}


def verify(candidate, db_by_code, audit_by_code, lexicon):
    shobi_code = code(candidate.get("code")); row = db_by_code.get(shobi_code); audit = audit_by_code.get(shobi_code)
    base = {"code": shobi_code, "sourceV6Result": candidate.get("result")}
    if not row or not audit: return {**base, "result": "INDEPENDENT_REJECTED_MISSING_RECORD"}
    fid = str(row.get("fragranticaId") or "").strip(); catalog = list(row.get("fragranticaSocialCardNotes") or [])
    base.update({"fid": fid, "catalog": catalog})
    if candidate.get("fid") != fid or list(candidate.get("catalog") or []) != catalog or str(audit.get("fragranticaId") or "") != fid:
        return {**base, "result": "INDEPENDENT_REJECTED_STALE_TARGET"}
    if audit.get("result") != "READING_NOT_STRICT_ENOUGH":
        return {**base, "result": "INDEPENDENT_REJECTED_UNEXPECTED_AUDIT_STATE", "currentAuditResult": audit.get("result")}
    card, card_source, candidates = resolve_exact_fid_card(shobi_code, fid)
    if not card: return {**base, "result": "INDEPENDENT_REJECTED_CARD_AMBIGUITY", "cards": [str(item.relative_to(ROOT)) for item in candidates]}
    if str(candidate.get("card") or "") != str(card.relative_to(ROOT)) or candidate.get("cardSource") != card_source:
        return {**base, "result": "INDEPENDENT_REJECTED_CARD_PROVENANCE_CHANGED"}
    panel = notes_panel(card)
    if not panel: return {**base, "result": "INDEPENDENT_REJECTED_UNSUPPORTED_CARD_GEOMETRY"}
    evidence = panel_sequence(panel, lexicon)
    observed = evidence["observed"]
    result = "INDEPENDENT_REJECTED_UNRESOLVED_LAYOUT_SEQUENCE" if observed is None else "INDEPENDENT_REJECTED_SEQUENCE_NOT_EXACT"
    if observed == catalog:
        result = "INDEPENDENT_EXACT_NEURAL_SEQUENCE"
    return {**base, "result": result, "card": str(card.relative_to(ROOT)), "cardSource": card_source, "observed": observed or [], "layoutEvidence": evidence}


def main():
    db = load(DB); audit = load(AUDIT).get("rows", []); report = load(V6)
    lexicon = [line.strip() for line in LEXICON.read_text(encoding="utf-8").splitlines() if line.strip()]
    db_by_code = {code(row.get("code")): row for row in db}; audit_by_code = {code(row.get("code")): row for row in audit}
    candidates = [row for row in report.get("rows", []) if row.get("result") == "EXACT_NEURAL_SLOT_SEQUENCE"]
    rows = [verify(candidate, db_by_code, audit_by_code, lexicon) for candidate in candidates]
    payload = {"mode": "INDEPENDENT_V6_LAYOUT_AWARE_TESSERACT_VERIFIER", "source": str(V6.relative_to(ROOT)), "rule": "V6 first requires two exact neural preprocessing reads; this independent Tesseract pass derives one complete spatial 3x2 sequence with zero competing exact sequence. Catalog is used only after recognition.", "sourceExactCandidates": len(candidates), "counts": dict(sorted(Counter(row["result"] for row in rows).items())), "rows": rows}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidates": len(candidates), "counts": payload["counts"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__": main()
