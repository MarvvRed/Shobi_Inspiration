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


def crop_slots(path):
    with Image.open(path) as source:
        if source.width < 800 or source.height < 800 or source.height / source.width < .85:
            return None
        image = source.convert("RGB").resize((1200, 1200), Image.Resampling.LANCZOS)
    # Independently inset from V6: each region is label-only and has complete
    # first/second-line coverage for standard six-note Social Cards.
    rows, cols = ((920, 988), (1088, 1138)), ((67, 176), (192, 300), (316, 427))
    return [image.crop((left, top, right, bottom)) for top, bottom in rows for left, right in cols]


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


def exact(raw, lexicon):
    matches = [note for note in lexicon if norm(note) == norm(raw)]
    return matches[0] if len(matches) == 1 else None


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
    cards = current_cards(shobi_code, fid)
    if len(cards) != 1: return {**base, "result": "INDEPENDENT_REJECTED_CARD_AMBIGUITY", "cards": [str(card.relative_to(ROOT)) for card in cards]}
    slots = crop_slots(cards[0])
    if not slots: return {**base, "result": "INDEPENDENT_REJECTED_UNSUPPORTED_CARD_GEOMETRY"}
    evidence = [inspect_slot(slot, lexicon) for slot in slots]
    observed = [item["winner"] for item in evidence]
    result = "INDEPENDENT_REJECTED_UNRESOLVED_SLOT" if any(note is None for note in observed) else "INDEPENDENT_REJECTED_SEQUENCE_NOT_EXACT"
    if observed == catalog:
        result = "INDEPENDENT_EXACT_NEURAL_SEQUENCE"
    return {**base, "result": result, "card": str(cards[0].relative_to(ROOT)), "observed": observed, "slots": evidence}


def main():
    db = load(DB); audit = load(AUDIT).get("rows", []); report = load(V6)
    lexicon = [line.strip() for line in LEXICON.read_text(encoding="utf-8").splitlines() if line.strip()]
    db_by_code = {code(row.get("code")): row for row in db}; audit_by_code = {code(row.get("code")): row for row in audit}
    candidates = [row for row in report.get("rows", []) if row.get("result") == "EXACT_NEURAL_SLOT_SEQUENCE"]
    rows = [verify(candidate, db_by_code, audit_by_code, lexicon) for candidate in candidates]
    payload = {"mode": "INDEPENDENT_V6_TESSERACT_SLOT_VERIFIER", "source": str(V6.relative_to(ROOT)), "sourceExactCandidates": len(candidates), "counts": dict(sorted(Counter(row["result"] for row in rows).items())), "rows": rows}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidates": len(candidates), "counts": payload["counts"], "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__": main()
