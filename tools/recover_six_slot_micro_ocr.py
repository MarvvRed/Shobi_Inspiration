#!/usr/bin/env python3
"""Recover unresolved modern six-slot Social Cards by OCRing each physical slot independently.

Safety rules:
- Social Card pixels are the only recognition source.
- Catalog notes are never used to select OCR candidates, infer slot occupancy, or choose note count.
- This pass only promotes cards where all six physical slots are independently occupied and resolved.
- Recognition maps OCR text only to the global Fragrantica note lexicon.
- Catalog sequence is compared only after the six-note image-derived sequence is complete.
"""
from __future__ import annotations

import csv, io, json, os, re, subprocess, unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import CROP, DB, OUT, code, find_card, is_subsequence

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "database/audits/fragrantica-note-lexicon.txt"
SCALE = 5
COLS = ((0, 140), (140, 280), (280, 420))
# Label bands calibrated from the visible modern-card notes panel. These are physical geometry,
# not derived from the expected catalog sequence.
ROWS = ((130, 235), (275, 378))


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def variants(tile):
    auto = ImageOps.autocontrast(tile)
    return {
        "contrast": ImageEnhance.Contrast(auto).enhance(2.3),
        "equalize": ImageOps.equalize(tile).filter(ImageFilter.SHARPEN),
        "unsharp": auto.filter(ImageFilter.UnsharpMask(radius=2, percent=220, threshold=2)),
        "t155": auto.point(lambda p: 255 if p > 155 else 0),
        "t175": auto.point(lambda p: 255 if p > 175 else 0),
        "t195": auto.point(lambda p: 255 if p > 195 else 0),
        "t215": auto.point(lambda p: 255 if p > 215 else 0),
    }


def ocr_text(image, psm):
    scaled = image.resize((image.width * SCALE, image.height * SCALE), Image.Resampling.LANCZOS)
    buf = io.BytesIO(); scaled.save(buf, format="PNG")
    run = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
        input=buf.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        timeout=10, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    )
    words = []
    for row in csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t"):
        txt = " ".join(str(row.get("text") or "").split())
        if not txt or sum(ch.isalpha() for ch in txt) < 2:
            continue
        try: conf = float(row.get("conf") or -1)
        except Exception: conf = -1
        if conf >= 25:
            words.append((int(row.get("top") or 0), int(row.get("left") or 0), txt, conf))
    words.sort()
    text = " ".join(w[2] for w in words)
    conf = min((w[3] for w in words), default=-1)
    return text, conf


def lexicon_match(raw, confidence, lexicon):
    target = norm(raw)
    if len(target) < 2:
        return None
    exact = [name for name in lexicon if norm(name) == target]
    if len(exact) == 1 and confidence >= 40:
        return exact[0], True, 1.0, 1.0
    ranked = sorted(((SequenceMatcher(None, target, norm(name)).ratio(), name) for name in lexicon), reverse=True)
    if not ranked:
        return None
    score, name = ranked[0]
    margin = score - (ranked[1][0] if len(ranked) > 1 else 0)
    if len(target) >= 5 and score >= 0.93 and margin >= 0.16 and confidence >= 58:
        return name, False, score, margin
    return None


def resolve_slot(tile, lexicon):
    family_votes = {}
    diagnostics = {}
    for family, image in variants(tile).items():
        accepted = []
        raws = []
        for psm in (6, 7, 11, 13):
            try:
                raw, conf = ocr_text(image, psm)
            except Exception:
                continue
            raws.append({"psm": psm, "raw": raw, "confidence": round(conf, 1)})
            hit = lexicon_match(raw, conf, lexicon)
            if hit:
                accepted.append((hit[0], hit[1]))
        counts = Counter(x[0] for x in accepted)
        chosen = None
        exact = False
        if counts:
            name, n = counts.most_common(1)[0]
            competitors = sum(v for k, v in counts.items() if k != name)
            if competitors == 0 and (n >= 2 or any(x[0] == name and x[1] for x in accepted)):
                chosen = name
                exact = any(x[0] == name and x[1] for x in accepted)
        if chosen:
            family_votes[family] = (chosen, exact)
        diagnostics[family] = {"reads": raws, "chosen": chosen, "exact": exact}

    votes = Counter(name for name, _ in family_votes.values())
    if not votes:
        return None, diagnostics
    name, n = votes.most_common(1)[0]
    second = votes.most_common(2)[1][1] if len(votes) > 1 else 0
    exact_families = sum(1 for v, ex in family_votes.values() if v == name and ex)
    required = 2 if exact_families else 3
    if n < required or second:
        return None, diagnostics
    return name, diagnostics


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    audit = json.loads(OUT.read_text(encoding="utf-8"))
    by_code = {code(r.get("code")): r for r in rows}
    lexicon = [x.strip() for x in LEXICON.read_text(encoding="utf-8").splitlines() if x.strip()]

    recovered, rejected = [], Counter()
    examined = 0
    for item in audit.get("rows", []):
        if item.get("result") != "READING_NOT_STRICT_ENOUGH":
            continue
        row = by_code.get(code(item.get("code")))
        if not row:
            continue
        card = find_card(row)
        if not card:
            continue
        try:
            with Image.open(card) as src:
                if src.width < 800 or src.height < 800 or src.height / src.width < 0.85:
                    continue
                sx, sy = src.width / 1200, src.height / 1200
                x1, y1, x2, y2 = CROP
                panel = src.crop((round(x1*sx), round(y1*sy), round(x2*sx), round(y2*sy))).convert("L").resize((420, 380), Image.Resampling.LANCZOS)
        except Exception:
            continue

        examined += 1
        observed, slot_diag = [], {}
        failed = False
        for r, (ya, yb) in enumerate(ROWS):
            for c, (xa, xb) in enumerate(COLS):
                # generous local crop; physical slot is fixed by card geometry, never by catalog content
                tile = panel.crop((max(0, xa-8), max(0, ya-18), min(420, xb+8), min(380, yb+2)))
                note, diag = resolve_slot(tile, lexicon)
                slot_diag[f"{r},{c}"] = {"note": note, "families": diag}
                if not note:
                    failed = True
                    break
                observed.append(note)
            if failed:
                break
        if failed:
            rejected["six_slot_not_fully_resolved"] += 1
            continue

        # Require exactly six independent physical slot readings. This is the completeness guard.
        if len(observed) != 6:
            rejected["not_six_observed"] += 1
            continue

        strict_reads = [a.get("notes") or [] for a in (item.get("attempts") or []) if a.get("strict")]
        if not all(is_subsequence(read, observed) for read in strict_reads):
            rejected["conflicting_strict_read"] += 1
            continue

        catalog = list(row.get("fragranticaSocialCardNotes") or [])
        if observed != catalog:
            item["microOcrDiagnostic"] = {"observedNotes": observed}
            rejected["sequence_not_exact"] += 1
            continue

        item.update({
            "result": "EXACT_ORDERED_MATCH",
            "observedNotes": observed,
            "proof": "SOCIAL_CARD_ONLY_SIX_PHYSICAL_SLOTS_INDEPENDENT_MICRO_OCR_CONSENSUS; ALL_SIX_SLOTS_REQUIRED; CATALOG_USED_ONLY_FOR_FINAL_EXACT_ORDER_CHECK",
            "microOcrEvidence": {"slots": slot_diag},
        })
        recovered.append(code(item.get("code")))

    audit["results"] = dict(sorted(Counter(x.get("result") for x in audit.get("rows", [])).items()))
    audit["sixSlotMicroOcrRecovery"] = {"examined": examined, "recovered": len(recovered), "codes": recovered, "rejected": dict(sorted(rejected.items()))}
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"examined": examined, "recovered": len(recovered), "results": audit["results"], "rejected": dict(sorted(rejected.items()))}, ensure_ascii=False))

if __name__ == "__main__":
    main()
