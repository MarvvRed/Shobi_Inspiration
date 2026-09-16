#!/usr/bin/env python3
"""Second conservative whole-panel OCR pass for only unresolved OCR cases.

Targets only cards whose first whole-panel pass failed because no strict read,
no multi-family consensus, or family disagreement. It deliberately excludes
sequence mismatches and contradictory strict reads. Catalog notes never guide
OCR; they are consulted only after a complete image-derived sequence is fixed.
Promotion requires >=3 independent preprocessing families agreeing on the same
complete strict ordered sequence, with no competing strict sequence.
"""
from __future__ import annotations

import csv, io, json, os, subprocess
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import ROOT, DB, OUT, CROP, SCALE, LEXICON, code, find_card, parse_attempt

TARGET_REASONS = {"NO_STRICT_WHOLE_PANEL_READ", "NO_MULTI_FAMILY_CONSENSUS", "FAMILY_DISAGREEMENT"}


def panel_variants(panel):
    auto = ImageOps.autocontrast(panel)
    eq = ImageOps.equalize(panel)
    return {
        "contrast17": ImageEnhance.Contrast(auto).enhance(1.7).filter(ImageFilter.SHARPEN),
        "contrast26": ImageEnhance.Contrast(auto).enhance(2.6).filter(ImageFilter.SHARPEN),
        "equalize2": ImageEnhance.Contrast(eq).enhance(1.5).filter(ImageFilter.SHARPEN),
        "unsharp1": auto.filter(ImageFilter.UnsharpMask(radius=1, percent=180, threshold=1)),
        "unsharp3": auto.filter(ImageFilter.UnsharpMask(radius=3, percent=260, threshold=2)),
        "t150": auto.point(lambda p: 255 if p > 150 else 0),
        "t178": auto.point(lambda p: 255 if p > 178 else 0),
        "t202": auto.point(lambda p: 255 if p > 202 else 0),
        "t228": auto.point(lambda p: 255 if p > 228 else 0),
    }


def read_variant(image, lexicon):
    scaled = image.resize((image.width * SCALE, image.height * SCALE), Image.Resampling.LANCZOS)
    payload = io.BytesIO(); scaled.save(payload, format="PNG")
    reads = []
    for psm in (3, 4, 6, 11, 12):
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
    row, lexicon = task
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
    all_strict = set()
    for family, image in panel_variants(panel).items():
        reads = read_variant(image, lexicon)
        strict = [tuple(r.get("notes") or []) for r in reads if r.get("strict") and r.get("notes")]
        if not strict:
            continue
        counts = Counter(strict)
        seq, n = counts.most_common(1)[0]
        # A preprocessing family is usable only if every strict PSM read in that family agrees.
        if any(x != seq for x in strict):
            all_strict.update(strict)
            continue
        family_sequences[family] = seq
        all_strict.add(seq)

    if not family_sequences:
        return {"code": c, "promote": False, "reason": "NO_STRICT_SECOND_PASS"}
    if len(all_strict) > 1:
        return {"code": c, "promote": False, "reason": "COMPETING_STRICT_SEQUENCE", "sequences": [list(x) for x in sorted(all_strict)]}

    votes = Counter(family_sequences.values())
    seq, families = votes.most_common(1)[0]
    if families < 3:
        return {"code": c, "promote": False, "reason": "LESS_THAN_3_FAMILIES", "best": list(seq), "families": families}
    if any(other != seq for other in votes):
        return {"code": c, "promote": False, "reason": "FAMILY_DISAGREEMENT"}

    catalog = tuple(row.get("fragranticaSocialCardNotes") or [])
    if seq != catalog:
        return {"code": c, "promote": False, "reason": "SEQUENCE_NOT_EXACT", "observed": list(seq), "catalog": list(catalog), "families": families}

    agreeing = sorted(k for k, v in family_sequences.items() if v == seq)
    return {"code": c, "promote": True, "observed": list(seq), "families": agreeing,
            "proof": "SOCIAL_CARD_ONLY_WHOLE_PANEL_SECOND_PASS; >=3 INDEPENDENT PREPROCESSING FAMILIES; ALL STRICT READS AGREE; COMPLETE ORDERED SEQUENCE; CATALOG_USED_ONLY_FOR_FINAL EXACT CHECK"}


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    audit = json.loads(OUT.read_text(encoding="utf-8"))
    by_code = {code(r.get("code")): r for r in rows}
    lexicon = [x.strip() for x in LEXICON.read_text(encoding="utf-8").splitlines() if x.strip()]

    targets = []
    for item in audit.get("rows", []):
        if item.get("result") != "READING_NOT_STRICT_ENOUGH":
            continue
        diag = item.get("wholePanelConsensusDiagnostic") or {}
        if diag.get("reason") not in TARGET_REASONS:
            continue
        c = code(item.get("code"))
        if c in by_code:
            targets.append(by_code[c])

    results = []
    workers = max(1, min(int(os.environ.get("SECOND_PASS_WORKERS", "4")), 6, os.cpu_count() or 2))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(inspect, (row, lexicon)) for row in targets]
        for i, fut in enumerate(as_completed(futs), 1):
            results.append(fut.result())
            if i % 40 == 0:
                print(f"processed {i}/{len(targets)}", flush=True)

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
                "wholePanelSecondPassEvidence": {"families": r["families"]},
            })
            recovered.append(r["code"])
        else:
            rejected[r.get("reason") or "UNKNOWN"] += 1
            item["wholePanelSecondPassDiagnostic"] = {k:v for k,v in r.items() if k not in {"code","promote"}}

    audit["results"] = dict(sorted(Counter(x.get("result") for x in audit.get("rows", [])).items()))
    audit["wholePanelSecondPassRecovery"] = {"examined": len(targets), "recovered": len(recovered), "codes": sorted(recovered), "rejected": dict(sorted(rejected.items()))}
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"examined": len(targets), "recovered": len(recovered), "results": audit["results"], "rejected": dict(sorted(rejected.items()))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
