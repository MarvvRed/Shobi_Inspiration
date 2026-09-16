#!/usr/bin/env python3
"""Find additional *exact* Social Card proofs without rewriting catalog notes.

This is deliberately a recovery pass, not a correction pass: only an observed
sequence identical to the existing catalog sequence can be emitted.  Missing
or contradictory OCR stays unresolved.
"""
from __future__ import annotations

import csv
import io
import json
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import (
    CARD_DIR, CROP, DB, LEXICON, OUT, SCALE, code, find_card, is_subsequence,
    parse_attempt,
)

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_OUT = ROOT / "database/audits/exact-card-proof-multipass.json"


def variants(source):
    """Return independent high-legibility representations of the note panel."""
    base = ImageOps.autocontrast(source)
    contrast = ImageEnhance.Contrast(base).enhance(2.0)
    enlarged = contrast.resize((contrast.width * SCALE, contrast.height * SCALE), Image.Resampling.LANCZOS)
    yield "contrast", enlarged.filter(ImageFilter.SHARPEN)
    yield "threshold-175", enlarged.point(lambda value: 0 if value < 175 else 255)
    yield "threshold-205", enlarged.point(lambda value: 0 if value < 205 else 255)


def parse_image(row, card_text, lexicon):
    base = {
        "code": code(row.get("code")),
        "fragranticaId": str(row.get("fragranticaId") or ""),
        "catalogNotes": list(row.get("fragranticaSocialCardNotes") or []),
        "card": str(Path(card_text).relative_to(ROOT)) if card_text else None,
    }
    if not card_text or not base["catalogNotes"]:
        return {**base, "result": "NO_CANDIDATE"}
    try:
        with Image.open(card_text) as src:
            if src.width < 800 or src.height < 800 or src.height / src.width < 0.85:
                return {**base, "result": "UNSUPPORTED_CARD_GEOMETRY"}
            sx, sy = src.width / 1200, src.height / 1200
            x1, y1, x2, y2 = CROP
            panel = src.crop((round(x1 * sx), round(y1 * sy), round(x2 * sx), round(y2 * sy))).convert("L").resize((420, 380), Image.Resampling.LANCZOS)
        readings = []
        for variant_name, image in variants(panel):
            payload = io.BytesIO(); image.save(payload, format="PNG")
            for psm in (6, 11):
                run = subprocess.run(
                    ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
                    input=payload.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                    env={**os.environ, "OMP_THREAD_LIMIT": "1"}, timeout=12,
                )
                reading = parse_attempt(list(csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t")), lexicon)
                readings.append({"variant": variant_name, "psm": psm, **reading})
    except Exception as exc:
        return {**base, "result": "OCR_ERROR", "error": str(exc)}

    strict = [item for item in readings if item["strict"]]
    exact = [item for item in strict if item["notes"] == base["catalogNotes"]]
    if not exact:
        # A second, independently-preprocessed reading can corroborate an exact
        # sequence that falls just below the normal 50% OCR confidence cutoff.
        # This is deliberately narrower than the normal rule: every label must
        # still be an exact lexicon label, every confidence must be >= 35, and
        # two distinct variant/PSM readings must agree on the whole sequence.
        relaxed = [
            item for item in readings
            if item["notes"] == base["catalogNotes"]
            and len(item.get("components") or []) == len(base["catalogNotes"])
            and all(
                component.get("exactText")
                and float(component.get("confidence") or -1) >= 35
                for component in item.get("components") or []
            )
        ]
        independent = {(item["variant"], item["psm"]) for item in relaxed}
        if len(independent) < 2:
            return {**base, "result": "NO_EXACT_PROOF", "readings": readings}
        selected = max(relaxed, key=lambda item: sum(float(c.get("confidence") or 0) for c in item["components"]))
        if not all(is_subsequence(item["notes"], selected["notes"]) for item in strict):
            return {**base, "result": "CONFLICTING_STRICT_READ", "readings": readings}
        return {
            **base,
            "result": "EXACT_ORDERED_MATCH_RELAXED_MULTIPASS",
            "observedNotes": selected["notes"],
            "proof": "TWO_INDEPENDENT_EXACT_LABEL_READS_AT_LEAST_35_PERCENT; ALL_STRICT_READS_ORDERED_SUBSEQUENCES",
            "selected": {"variant": selected["variant"], "psm": selected["psm"], "components": selected["components"]},
            "readings": readings,
        }
    selected = max(exact, key=lambda item: len(item["components"]))
    if not all(is_subsequence(item["notes"], selected["notes"]) for item in strict):
        independent = {(item["variant"], item["psm"]) for item in exact}
        # A strict majority from at least three independent OCR passes is a
        # stronger signal than a single failed pass.  The majority requirement
        # avoids promoting a two-versus-two disagreement or a duplicated read.
        if len(independent) >= 3 and len(exact) > len(strict) / 2:
            return {
                **base,
                "result": "EXACT_ORDERED_MATCH_CONSENSUS_MULTIPASS",
                "observedNotes": selected["notes"],
                "proof": "STRICT_EXACT_MAJORITY_FROM_AT_LEAST_THREE_INDEPENDENT_READS",
                "selected": {"variant": selected["variant"], "psm": selected["psm"], "components": selected["components"]},
                "readings": readings,
            }
        return {**base, "result": "CONFLICTING_STRICT_READ", "readings": readings}
    return {
        **base,
        "result": "EXACT_ORDERED_MATCH_MULTIPASS",
        "observedNotes": selected["notes"],
        "proof": "EXACT_HIGH_CONFIDENCE_LABELS; ALL_OTHER_STRICT_READS_ORDERED_SUBSEQUENCES",
        "selected": {"variant": selected["variant"], "psm": selected["psm"], "components": selected["components"]},
        "readings": readings,
    }


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    original = json.loads(OUT.read_text(encoding="utf-8"))
    unresolved = {item["code"] for item in original.get("rows", []) if item.get("result") == "READING_NOT_STRICT_ENOUGH"}
    lexicon = [line.strip() for line in LEXICON.read_text(encoding="utf-8").splitlines() if line.strip()]
    tasks = [(row, str(find_card(row) or ""), lexicon) for row in rows if code(row.get("code")) in unresolved]
    workers = max(1, min(int(os.environ.get("SOCIAL_CARD_RECOVERY_WORKERS", "6")), 6, os.cpu_count() or 2))
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(parse_image, *task) for task in tasks]
        for number, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if number % 100 == 0:
                print(f"recovered {number}/{len(tasks)}", flush=True)
    results.sort(key=lambda item: item["code"])
    proven = [item for item in results if item["result"] in {"EXACT_ORDERED_MATCH_MULTIPASS", "EXACT_ORDERED_MATCH_RELAXED_MULTIPASS", "EXACT_ORDERED_MATCH_CONSENSUS_MULTIPASS"}]
    RECOVERY_OUT.write_text(json.dumps({
        "rule": "Only an exact reading of the existing ordered catalog notes is proof: high-confidence with no conflict; two independent exact-label reads at >=35% with no contradictory strict read; or a strict exact majority from at least three independent reads. Non-matches never edit notes.",
        "targets": len(tasks), "proven": len(proven), "rows": results,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"targets": len(tasks), "proven": len(proven), "output": str(RECOVERY_OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
