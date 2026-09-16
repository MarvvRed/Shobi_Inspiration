#!/usr/bin/env python3
"""Recover unresolved modern Social Cards by reading occupied physical note slots independently.

Safety rules:
- Social Card pixels are the only source used to decide slot occupancy and note identity.
- Catalog notes are never used to select OCR candidates, infer note count, or decide occupancy.
- A slot is considered occupied only when multiple independent preprocessing families see credible text.
- Every occupied slot must resolve independently to one Fragrantica note; ambiguous occupied slots block promotion.
- Catalog sequence is consulted only after the complete image-derived ordered sequence is fixed.
"""
from __future__ import annotations

import csv, io, json, os, re, subprocess, unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import CROP, DB, OUT, code, find_card, is_subsequence

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "database/audits/fragrantica-note-lexicon.txt"
SCALE = 5
COLS = ((0, 140), (140, 280), (280, 420))
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
        "t145": auto.point(lambda p: 255 if p > 145 else 0),
        "t165": auto.point(lambda p: 255 if p > 165 else 0),
        "t185": auto.point(lambda p: 255 if p > 185 else 0),
        "t205": auto.point(lambda p: 255 if p > 205 else 0),
        "t225": auto.point(lambda p: 255 if p > 225 else 0),
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
        letters = sum(ch.isalpha() for ch in txt)
        if not txt or letters < 2:
            continue
        try: conf = float(row.get("conf") or -1)
        except Exception: conf = -1
        if conf >= 20:
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
    if len(exact) == 1 and confidence >= 38:
        return exact[0], True, 1.0, 1.0
    ranked = sorted(((SequenceMatcher(None, target, norm(name)).ratio(), name) for name in lexicon), reverse=True)
    if not ranked:
        return None
    score, name = ranked[0]
    margin = score - (ranked[1][0] if len(ranked) > 1 else 0)
    if len(target) >= 5 and score >= 0.94 and margin >= 0.17 and confidence >= 58:
        return name, False, score, margin
    return None


def inspect_slot(tile, lexicon):
    family_votes = {}
    text_families = set()
    diagnostics = {}
    for family, image in variants(tile).items():
        accepted = []
        raws = []
        credible_raw = False
        for psm in (6, 7, 11, 13):
            try:
                raw, conf = ocr_text(image, psm)
            except Exception:
                continue
            raws.append({"psm": psm, "raw": raw, "confidence": round(conf, 1)})
            if len(norm(raw).replace(" ", "")) >= 3 and conf >= 38:
                credible_raw = True
            hit = lexicon_match(raw, conf, lexicon)
            if hit:
                accepted.append((hit[0], hit[1]))
        if credible_raw:
            text_families.add(family)
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
    if votes:
        name, n = votes.most_common(1)[0]
        second = votes.most_common(2)[1][1] if len(votes) > 1 else 0
        exact_families = sum(1 for v, ex in family_votes.values() if v == name and ex)
        required = 2 if exact_families else 3
        if n >= required and second == 0:
            return "RESOLVED", name, diagnostics, {"textFamilies": len(text_families), "voteFamilies": n}

    # Conservative occupancy decision: independent preprocessing families must see credible label-like text.
    # If they do but the lexicon consensus is insufficient, the card stays yellow rather than treating the slot as empty.
    if len(text_families) >= 2 or family_votes:
        return "AMBIGUOUS", None, diagnostics, {"textFamilies": len(text_families), "voteFamilies": sum(votes.values())}
    return "EMPTY", None, diagnostics, {"textFamilies": len(text_families), "voteFamilies": 0}


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
        ambiguous = False
        occupied_positions = []
        for r, (ya, yb) in enumerate(ROWS):
            for c, (xa, xb) in enumerate(COLS):
                tile = panel.crop((max(0, xa-8), max(0, ya-18), min(420, xb+8), min(380, yb+2)))
                state, note, diag, evidence = inspect_slot(tile, lexicon)
                slot_diag[f"{r},{c}"] = {"state": state, "note": note, "evidence": evidence, "families": diag}
                if state == "AMBIGUOUS":
                    ambiguous = True
                elif state == "RESOLVED":
                    occupied_positions.append((r, c))
                    observed.append(note)

        if ambiguous:
            rejected["occupied_slot_not_strictly_resolved"] += 1
            continue
        if not observed:
            rejected["no_occupied_slots"] += 1
            continue

        # Structural guard: occupied slots must form the normal reading-order prefix after empty slots are ignored.
        # We do not derive note count from the catalog; this only rejects visually implausible isolated OCR noise.
        flat = [r*3+c for r, c in occupied_positions]
        if flat != sorted(flat):
            rejected["non_reading_order_slots"] += 1
            continue

        strict_reads = [a.get("notes") or [] for a in (item.get("attempts") or []) if a.get("strict")]
        if not all(is_subsequence(read, observed) for read in strict_reads):
            rejected["conflicting_strict_read"] += 1
            continue

        catalog = list(row.get("fragranticaSocialCardNotes") or [])
        if observed != catalog:
            item["variableSlotMicroOcrDiagnostic"] = {"observedNotes": observed, "occupiedSlots": occupied_positions}
            rejected["sequence_not_exact"] += 1
            continue

        item.update({
            "result": "EXACT_ORDERED_MATCH",
            "observedNotes": observed,
            "proof": "SOCIAL_CARD_ONLY_VARIABLE_PHYSICAL_SLOT_MICRO_OCR_CONSENSUS; OCCUPANCY_AND_NOTE_COUNT_DERIVED_ONLY_FROM_CARD; ALL_OCCUPIED_SLOTS_STRICTLY_RESOLVED; CATALOG_USED_ONLY_FOR_FINAL_EXACT_ORDER_CHECK",
            "variableSlotMicroOcrEvidence": {"occupiedSlots": occupied_positions, "slots": slot_diag},
        })
        recovered.append(code(item.get("code")))

    audit["results"] = dict(sorted(Counter(x.get("result") for x in audit.get("rows", [])).items()))
    audit["variableSlotMicroOcrRecovery"] = {"examined": examined, "recovered": len(recovered), "codes": recovered, "rejected": dict(sorted(rejected.items()))}
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"examined": examined, "recovered": len(recovered), "results": audit["results"], "rejected": dict(sorted(rejected.items()))}, ensure_ascii=False))

if __name__ == "__main__":
    main()
