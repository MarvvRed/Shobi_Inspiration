#!/usr/bin/env python3
"""Fast conservative recovery for unresolved Social Cards using whole-panel OCR consensus.

The catalog is never used to guide OCR. Multiple independent image preprocessing
families read the entire notes panel. A yellow is promoted only when at least two
families independently produce the same complete strict ordered sequence and that
sequence equals the catalog exactly. Any contradictory strict read blocks promotion.
"""
from __future__ import annotations

import csv, io, json, os, subprocess
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import (
    ROOT, DB, OUT, CROP, SCALE, LEXICON, code, find_card, parse_attempt
)


def panel_variants(panel):
    auto = ImageOps.autocontrast(panel)
    return {
        "contrast": ImageEnhance.Contrast(auto).enhance(2.0).filter(ImageFilter.SHARPEN),
        "equalize": ImageOps.equalize(panel).filter(ImageFilter.SHARPEN),
        "unsharp": auto.filter(ImageFilter.UnsharpMask(radius=2, percent=220, threshold=2)),
        "t165": auto.point(lambda p: 255 if p > 165 else 0),
        "t190": auto.point(lambda p: 255 if p > 190 else 0),
        "t215": auto.point(lambda p: 255 if p > 215 else 0),
    }


def read_variant(image, lexicon):
    scaled = image.resize((image.width * SCALE, image.height * SCALE), Image.Resampling.LANCZOS)
    payload = io.BytesIO(); scaled.save(payload, format="PNG")
    reads = []
    for psm in (6, 11):
        try:
            run = subprocess.run(
                ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
                input=payload.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=True, timeout=15, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
            )
            data = list(csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t"))
            reads.append({"psm": psm, **parse_attempt(data, lexicon)})
        except Exception as exc:
            reads.append({"psm": psm, "strict": False, "reason": "OCR_ERROR", "error": str(exc), "notes": []})
    return reads


def inspect(task):
    row, audit_item, lexicon = task
    c = code(row.get("code")); card = find_card(row)
    if not card:
        return {"code": c, "promote": False, "reason": "NO_CARD"}
    try:
        with Image.open(card) as src:
            if src.width < 800 or src.height < 800 or src.height / src.width < 0.85:
                return {"code": c, "promote": False, "reason": "UNSUPPORTED_GEOMETRY"}
            sx, sy = src.width / 1200, src.height / 1200
            x1, y1, x2, y2 = CROP
            panel = src.crop((round(x1*sx), round(y1*sy), round(x2*sx), round(y2*sy))).convert("L").resize((420, 380), Image.Resampling.LANCZOS)
    except Exception as exc:
        return {"code": c, "promote": False, "reason": "IMAGE_ERROR", "error": str(exc)}

    family_sequences = {}
    diagnostics = {}
    contradictory = set()
    for family, image in panel_variants(panel).items():
        reads = read_variant(image, lexicon)
        strict = [tuple(r.get("notes") or []) for r in reads if r.get("strict") and r.get("notes")]
        diagnostics[family] = reads
        if not strict:
            continue
        counts = Counter(strict)
        seq, n = counts.most_common(1)[0]
        if any(x != seq for x in strict):
            contradictory.update(strict)
            continue
        family_sequences[family] = seq

    if contradictory:
        return {"code": c, "promote": False, "reason": "CONTRADICTORY_STRICT_READS", "sequences": [list(x) for x in sorted(contradictory)]}
    votes = Counter(family_sequences.values())
    if not votes:
        return {"code": c, "promote": False, "reason": "NO_STRICT_WHOLE_PANEL_READ"}
    seq, families = votes.most_common(1)[0]
    if families < 2:
        return {"code": c, "promote": False, "reason": "NO_MULTI_FAMILY_CONSENSUS", "best": list(seq), "families": families}
    if any(other != seq for other in votes):
        return {"code": c, "promote": False, "reason": "FAMILY_DISAGREEMENT"}

    catalog = tuple(row.get("fragranticaSocialCardNotes") or [])
    if seq != catalog:
        return {"code": c, "promote": False, "reason": "SEQUENCE_NOT_EXACT", "observed": list(seq), "catalog": list(catalog), "families": families}

    agreeing = sorted(k for k, v in family_sequences.items() if v == seq)
    return {
        "code": c, "promote": True, "observed": list(seq), "families": agreeing,
        "proof": "SOCIAL_CARD_ONLY_WHOLE_PANEL_MULTI_PREPROCESSING_CONSENSUS; >=2 INDEPENDENT FAMILIES; COMPLETE STRICT ORDERED READ; CATALOG_USED_ONLY_FOR_FINAL EXACT CHECK",
    }


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    audit = json.loads(OUT.read_text(encoding="utf-8"))
    by_code = {code(r.get("code")): r for r in rows}
    lexicon = [x.strip() for x in LEXICON.read_text(encoding="utf-8").splitlines() if x.strip()]
    targets = [x for x in audit.get("rows", []) if x.get("result") == "READING_NOT_STRICT_ENOUGH" and code(x.get("code")) in by_code]
    tasks = [(by_code[code(x.get("code"))], x, lexicon) for x in targets]

    results = []
    workers = max(1, min(int(os.environ.get("WHOLE_PANEL_WORKERS", "4")), 6, os.cpu_count() or 2))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(inspect, t) for t in tasks]
        for i, fut in enumerate(as_completed(futs), 1):
            results.append(fut.result())
            if i % 50 == 0:
                print(f"processed {i}/{len(tasks)}", flush=True)

    result_by_code = {x["code"]: x for x in results}
    recovered = []
    rejected = Counter()
    for item in audit.get("rows", []):
        r = result_by_code.get(code(item.get("code")))
        if not r:
            continue
        if r.get("promote"):
            item.update({
                "result": "EXACT_ORDERED_MATCH",
                "observedNotes": r["observed"],
                "proof": r["proof"],
                "wholePanelConsensusEvidence": {"families": r["families"]},
            })
            recovered.append(r["code"])
        else:
            rejected[r.get("reason") or "UNKNOWN"] += 1
            item["wholePanelConsensusDiagnostic"] = {k:v for k,v in r.items() if k not in {"code","promote"}}

    audit["results"] = dict(sorted(Counter(x.get("result") for x in audit.get("rows", [])).items()))
    audit["wholePanelConsensusRecovery"] = {
        "examined": len(tasks), "recovered": len(recovered), "codes": sorted(recovered),
        "rejected": dict(sorted(rejected.items())),
    }
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"examined": len(tasks), "recovered": len(recovered), "results": audit["results"], "rejected": dict(sorted(rejected.items()))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
