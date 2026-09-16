#!/usr/bin/env python3
"""Recover exact six-note proofs using conservative fuzzy OCR consensus.

Recognition never uses the expected catalog note as an OCR hint. Each slot is
read against the global Fragrantica note lexicon. Fuzzy OCR is accepted only
when multiple independent preprocessing families converge on the same lexicon
label with high similarity/margin/confidence. The final six-label sequence must
still equal the existing catalog sequence exactly, and any strict full-panel
reads must remain ordered subsequences.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import statistics
import subprocess
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image

from audit_social_card_order_from_images import CROP, DB, OUT, code, find_card, is_subsequence
from recover_exact_card_proofs_multipass import SIX_SLOT_COLUMNS, SIX_SLOT_ROWS, slot_variants

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "database/audits/fragrantica-note-lexicon.txt"


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", value))


def best_lexicon_match(text, lexicon):
    target = norm(text)
    if not target:
        return None, 0.0, 0.0, False
    exact = [name for name in lexicon if norm(name) == target]
    if len(exact) == 1:
        return exact[0], 1.0, 1.0, True
    ranked = sorted(
        ((SequenceMatcher(None, target, norm(name)).ratio(), name) for name in lexicon if norm(name)),
        reverse=True,
    )
    if not ranked:
        return None, 0.0, 0.0, False
    score, name = ranked[0]
    margin = score - (ranked[1][0] if len(ranked) > 1 else 0.0)
    return name, score, margin, False


def tesseract_text(image, psm):
    payload = io.BytesIO(); image.save(payload, format="PNG")
    run = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
        input=payload.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, timeout=8, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    )
    words, confs = [], []
    for row in csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t"):
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        try: conf = float(row.get("conf") or -1)
        except Exception: conf = -1
        if conf < 35:
            continue
        words.append(text); confs.append(conf)
    return " ".join(words), (sum(confs) / len(confs) if confs else -1)


def acceptable_read(text, confidence, lexicon):
    name, score, margin, exact = best_lexicon_match(text, lexicon)
    if not name:
        return None
    if exact and confidence >= 45:
        return {"name": name, "score": 1.0, "margin": 1.0, "exact": True, "confidence": confidence, "text": text}
    # Fuzzy acceptance is deliberately strict. Short labels are too collision-prone.
    if len(norm(name).replace(" ", "")) < 5:
        return None
    if score >= 0.90 and margin >= 0.15 and confidence >= 60:
        return {"name": name, "score": round(score, 3), "margin": round(margin, 3), "exact": False,
                "confidence": round(confidence, 1), "text": text}
    return None


def header_y(item):
    values = [float(a["notesHeaderY"]) for a in item.get("attempts") or [] if isinstance(a.get("notesHeaderY"), (int, float))]
    return statistics.median(values) if values else None


def shifted_panel(panel, observed_header_y):
    shift = int(round(53.0 - observed_header_y))
    if shift == 0:
        return panel, 0
    shifted = Image.new("L", panel.size, 255)
    if shift > 0:
        shifted.paste(panel.crop((0, 0, panel.width, panel.height - shift)), (0, shift))
    else:
        amount = -shift
        shifted.paste(panel.crop((0, amount, panel.width, panel.height)), (0, 0))
    return shifted, shift


def read_slots(panel, lexicon):
    observed, components, diagnostics = [], [], []
    slot_no = 0
    for y1, y2 in SIX_SLOT_ROWS:
        for x1, x2 in SIX_SLOT_COLUMNS:
            slot_no += 1
            crop = panel.crop((x1 + 3, y1 + 1, x2 - 3, y2 - 1))
            family_votes = {}
            attempts = []
            for family, image in slot_variants(crop):
                accepted = []
                for psm in (6, 7, 11, 13):
                    text, conf = tesseract_text(image, psm)
                    read = acceptable_read(text, conf, lexicon)
                    attempts.append({"family": family, "psm": psm, "text": text, "confidence": round(conf, 1), "accepted": read})
                    if read:
                        accepted.append(read)
                names = {r["name"] for r in accepted}
                if len(names) == 1:
                    name = next(iter(names))
                    strongest = max((r for r in accepted if r["name"] == name), key=lambda r: (r["exact"], r["confidence"], r["score"]))
                    family_votes[family] = strongest

            support = {}
            for family, read in family_votes.items():
                support.setdefault(read["name"], []).append((family, read))
            strong = {}
            for name, votes in support.items():
                exact_count = sum(1 for _, r in votes if r["exact"])
                # 2 independent families suffice if at least one is exact;
                # fuzzy-only proof requires 3 independent preprocessing families.
                if (len(votes) >= 2 and exact_count >= 1) or len(votes) >= 3:
                    strong[name] = votes
            diagnostics.append({"slot": slot_no, "familyVotes": family_votes, "strong": {k: [f for f, _ in v] for k, v in strong.items()}, "attempts": attempts})
            if len(strong) != 1:
                return None, [], diagnostics
            name, votes = next(iter(strong.items()))
            best = max((r for _, r in votes), key=lambda r: (r["exact"], r["confidence"], r["score"]))
            observed.append(name)
            components.append({"slot": slot_no, "name": name, "raw": best["text"], "confidence": best["confidence"],
                               "score": best["score"], "margin": best["margin"], "exactText": best["exact"],
                               "variantSupport": sorted(f for f, _ in votes)})
    return observed, components, diagnostics


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    audit = json.loads(OUT.read_text(encoding="utf-8"))
    by_code = {code(r.get("code")): r for r in rows}
    lexicon = [x.strip() for x in LEXICON.read_text(encoding="utf-8").splitlines() if x.strip()]
    examined = 0; recovered = []; rejected = Counter()

    for item in audit.get("rows", []):
        if item.get("result") != "READING_NOT_STRICT_ENOUGH":
            continue
        row = by_code.get(code(item.get("code")))
        notes = list((row or {}).get("fragranticaSocialCardNotes") or [])
        if len(notes) != 6:
            rejected[f"note_count_{len(notes)}"] += 1; continue
        hy = header_y(item)
        card = find_card(row) if row else None
        if hy is None or not card:
            rejected["missing_header_or_card"] += 1; continue
        examined += 1
        try:
            with Image.open(card) as src:
                if src.width < 800 or src.height < 800 or src.height / src.width < 0.85:
                    rejected["unsupported_geometry"] += 1; continue
                sx, sy = src.width / 1200, src.height / 1200
                x1, y1, x2, y2 = CROP
                panel = src.crop((round(x1*sx), round(y1*sy), round(x2*sx), round(y2*sy))).convert("L").resize((420, 380), Image.Resampling.LANCZOS)
        except Exception:
            rejected["image_error"] += 1; continue
        aligned, shift = shifted_panel(panel, hy)
        observed, components, diagnostics = read_slots(aligned, lexicon)
        if observed is None:
            rejected["slot_consensus_failed"] += 1; continue
        if observed != notes:
            rejected["sequence_not_exact"] += 1; continue
        strict_reads = [a.get("notes") or [] for a in item.get("attempts") or [] if a.get("strict")]
        if not all(is_subsequence(s, observed) for s in strict_reads):
            rejected["conflicting_strict_read"] += 1; continue
        item.update({
            "result": "EXACT_ORDERED_MATCH", "observedNotes": observed, "components": components,
            "proof": "CONSERVATIVE_FUZZY_SIX_SLOT_CONSENSUS; FUZZY_ONLY_REQUIRES_THREE_PREPROCESSING_FAMILIES; FINAL_SEQUENCE_EXACT; STRICT_READS_ORDERED_SUBSEQUENCES",
            "fuzzySlotEvidence": {"observedHeaderY": hy, "alignmentShift": shift, "slotDiagnostics": diagnostics},
        })
        recovered.append(code(item.get("code")))

    audit["results"] = dict(sorted(Counter(i.get("result") for i in audit.get("rows", [])).items()))
    audit["conservativeFuzzySlotRecovery"] = {"examined": examined, "recovered": len(recovered), "codes": recovered, "rejected": dict(sorted(rejected.items()))}
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"examined": examined, "recovered": len(recovered), "results": audit["results"], "rejected": dict(sorted(rejected.items()))}, ensure_ascii=False))

if __name__ == "__main__":
    main()
