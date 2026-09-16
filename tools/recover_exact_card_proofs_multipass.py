#!/usr/bin/env python3
"""Find additional *exact* Social Card proofs without rewriting catalog notes.

This is deliberately a recovery pass, not a correction pass: only an observed
sequence identical to the existing catalog sequence can be emitted. Missing
or contradictory OCR stays unresolved.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
import unicodedata
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import (
    CARD_DIR, CROP, DB, LEXICON, OUT, SCALE, code, find_card, is_subsequence,
    parse_attempt,
)

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_OUT = ROOT / "database/audits/exact-card-proof-multipass.json"

# Calibrated only for the dominant, validated six-note 1200x1200 Social Card
# layout. Coordinates are on the 420x380 normalized notes panel below.
SIX_SLOT_COLUMNS = ((0, 140), (140, 280), (280, 420))
SIX_SLOT_ROWS = ((153, 245), (304, 380))


def variants(source):
    """Return independent high-legibility representations of the note panel."""
    base = ImageOps.autocontrast(source)
    contrast = ImageEnhance.Contrast(base).enhance(2.0)
    enlarged = contrast.resize((contrast.width * SCALE, contrast.height * SCALE), Image.Resampling.LANCZOS)
    yield "contrast", enlarged.filter(ImageFilter.SHARPEN)
    yield "threshold-175", enlarged.point(lambda value: 0 if value < 175 else 255)
    yield "threshold-205", enlarged.point(lambda value: 0 if value < 205 else 255)


def normalize_exact(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", value))


def exact_lexicon_candidates(text, lexicon):
    """Return only exact, whole-token lexicon labels observed in OCR text.

    Longer labels dominate contained shorter labels (for example "rose water"
    over "rose"). Equal-length distinct labels remain ambiguous.
    """
    normalized = normalize_exact(text)
    if not normalized:
        return []
    padded = f" {normalized} "
    matches = []
    for name in lexicon:
        candidate = normalize_exact(name)
        if candidate and f" {candidate} " in padded:
            matches.append((len(candidate.split()), len(candidate), name))
    if not matches:
        return []
    max_tokens = max(item[0] for item in matches)
    token_matches = [item for item in matches if item[0] == max_tokens]
    max_chars = max(item[1] for item in token_matches)
    names = []
    for _, length, name in token_matches:
        if length == max_chars and name not in names:
            names.append(name)
    return names


def slot_variants(source):
    """Independent preprocessing families for a single note-label slot."""
    base = ImageOps.autocontrast(source.convert("L"))
    contrast = ImageEnhance.Contrast(base).enhance(2.1)
    enlarged = contrast.resize(
        (max(1, contrast.width * 5), max(1, contrast.height * 5)),
        Image.Resampling.LANCZOS,
    ).filter(ImageFilter.SHARPEN)
    yield "slot-contrast", enlarged
    yield "slot-threshold-175", enlarged.point(lambda value: 0 if value < 175 else 255)
    yield "slot-threshold-205", enlarged.point(lambda value: 0 if value < 205 else 255)
    threshold_185 = enlarged.point(lambda value: 0 if value < 185 else 255)
    yield "slot-threshold-185-invert", ImageOps.invert(threshold_185)


def tesseract_slot_read(image, psm, lexicon):
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    run = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
        input=payload.getvalue(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        timeout=8,
    )
    words = []
    confidences = []
    for row in csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t"):
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        try:
            confidence = float(row.get("conf") or -1)
        except (TypeError, ValueError):
            confidence = -1
        if confidence < 35:
            continue
        words.append(text)
        confidences.append(confidence)
    text = " ".join(words)
    candidates = exact_lexicon_candidates(text, lexicon)
    return {
        "text": text,
        "confidence": round(sum(confidences) / len(confidences), 2) if confidences else -1,
        "candidates": candidates,
    }


def read_six_slot_consensus(panel, lexicon):
    """Read six standard slots independently without using catalog notes.

    A slot passes only when the same exact lexicon label is independently seen
    in at least two preprocessing families. Different PSMs inside one family do
    not count as independent corroboration. Two-family support for a competing
    label is a hard ambiguity and rejects the whole card.
    """
    observed = []
    components = []
    diagnostics = []
    slot_number = 0
    for y1, y2 in SIX_SLOT_ROWS:
        for x1, x2 in SIX_SLOT_COLUMNS:
            slot_number += 1
            slot = panel.crop((x1 + 3, y1 + 1, x2 - 3, y2 - 1))
            attempts = []
            family_candidates = {}
            for variant_name, image in slot_variants(slot):
                seen = set()
                for psm in (6, 7, 11, 13):
                    reading = tesseract_slot_read(image, psm, lexicon)
                    attempt = {"variant": variant_name, "psm": psm, **reading}
                    attempts.append(attempt)
                    if len(reading["candidates"]) == 1:
                        seen.add(reading["candidates"][0])
                if len(seen) == 1:
                    family_candidates[variant_name] = next(iter(seen))

            support = {}
            for variant_name, name in family_candidates.items():
                support.setdefault(name, []).append(variant_name)
            corroborated = {name: families for name, families in support.items() if len(families) >= 2}
            diagnostics.append({
                "slot": slot_number,
                "familyCandidates": family_candidates,
                "corroborated": corroborated,
                "attempts": attempts,
            })
            if len(corroborated) != 1:
                return None, [], diagnostics
            name, families = next(iter(corroborated.items()))

            supporting_attempts = [
                attempt for attempt in attempts
                if attempt["variant"] in families and attempt["candidates"] == [name]
            ]
            strongest = max(
                supporting_attempts,
                key=lambda item: item["confidence"],
                default={"confidence": -1, "text": "", "variant": None, "psm": None},
            )
            if strongest["confidence"] < 50:
                return None, [], diagnostics

            observed.append(name)
            components.append({
                "slot": slot_number,
                "name": name,
                "raw": strongest["text"],
                "confidence": strongest["confidence"],
                "exactText": True,
                "variantSupport": sorted(families),
                "strongestVariant": strongest["variant"],
                "strongestPsm": strongest["psm"],
            })
    return observed, components, diagnostics


def parse_image(row, card_text, lexicon):
    base = {
        "code": code(row.get("code")),
        "fragranticaId": str(row.get("fragranticaId") or ""),
        "catalogNotes": list(row.get("fragranticaSocialCardNotes") or []),
        "card": str(Path(card_text).relative_to(ROOT)) if card_text else None,
    }
    if not card_text or not base["catalogNotes"]:
        return {**base, "result": "NO_CANDIDATE"}
    panel = None
    source_ratio = None
    try:
        with Image.open(card_text) as src:
            if src.width < 800 or src.height < 800 or src.height / src.width < 0.85:
                return {**base, "result": "UNSUPPORTED_CARD_GEOMETRY"}
            source_ratio = src.height / src.width
            sx, sy = src.width / 1200, src.height / 1200
            x1, y1, x2, y2 = CROP
            panel = src.crop(
                (round(x1 * sx), round(y1 * sy), round(x2 * sx), round(y2 * sy))
            ).convert("L").resize((420, 380), Image.Resampling.LANCZOS)
        readings = []
        for variant_name, image in variants(panel):
            payload = io.BytesIO()
            image.save(payload, format="PNG")
            for psm in (6, 11):
                run = subprocess.run(
                    ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
                    input=payload.getvalue(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    env={**os.environ, "OMP_THREAD_LIMIT": "1"},
                    timeout=12,
                )
                reading = parse_attempt(
                    list(csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t")),
                    lexicon,
                )
                readings.append({"variant": variant_name, "psm": psm, **reading})
    except Exception as exc:
        return {**base, "result": "OCR_ERROR", "error": str(exc)}

    strict = [item for item in readings if item["strict"]]
    exact = [item for item in strict if item["notes"] == base["catalogNotes"]]
    if not exact:
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
        if len(independent) >= 2:
            selected = max(
                relaxed,
                key=lambda item: sum(float(c.get("confidence") or 0) for c in item["components"]),
            )
            if all(is_subsequence(item["notes"], selected["notes"]) for item in strict):
                return {
                    **base,
                    "result": "EXACT_ORDERED_MATCH_RELAXED_MULTIPASS",
                    "observedNotes": selected["notes"],
                    "proof": "TWO_INDEPENDENT_EXACT_LABEL_READS_AT_LEAST_35_PERCENT; ALL_STRICT_READS_ORDERED_SUBSEQUENCES",
                    "selected": {
                        "variant": selected["variant"],
                        "psm": selected["psm"],
                        "components": selected["components"],
                    },
                    "readings": readings,
                }

        if len(base["catalogNotes"]) == 6 and 0.95 <= source_ratio <= 1.05:
            slot_notes, slot_components, slot_diagnostics = read_six_slot_consensus(panel, lexicon)
            if slot_notes == base["catalogNotes"]:
                if all(is_subsequence(item["notes"], slot_notes) for item in strict):
                    return {
                        **base,
                        "result": "EXACT_ORDERED_MATCH_CONSENSUS_MULTIPASS",
                        "observedNotes": slot_notes,
                        "proof": "SIX_SLOT_EXACT_LEXICON_CONSENSUS_FROM_AT_LEAST_TWO_PREPROCESSING_FAMILIES_PER_SLOT; ALL_STRICT_READS_ORDERED_SUBSEQUENCES",
                        "selected": {
                            "variant": "six-slot-consensus",
                            "psm": None,
                            "components": slot_components,
                        },
                        "slotDiagnostics": slot_diagnostics,
                        "readings": readings,
                    }
            elif slot_notes is not None:
                return {
                    **base,
                    "result": "SLOT_SEQUENCE_CONTRADICTS_CATALOG",
                    "observedNotes": slot_notes,
                    "slotDiagnostics": slot_diagnostics,
                    "readings": readings,
                }

        if relaxed:
            selected = max(
                relaxed,
                key=lambda item: sum(float(c.get("confidence") or 0) for c in item["components"]),
            )
            if not all(is_subsequence(item["notes"], selected["notes"]) for item in strict):
                return {**base, "result": "CONFLICTING_STRICT_READ", "readings": readings}
        return {**base, "result": "NO_EXACT_PROOF", "readings": readings}

    selected = max(exact, key=lambda item: len(item["components"]))
    if not all(is_subsequence(item["notes"], selected["notes"]) for item in strict):
        independent = {(item["variant"], item["psm"]) for item in exact}
        if len(independent) >= 3 and len(exact) > len(strict) / 2:
            return {
                **base,
                "result": "EXACT_ORDERED_MATCH_CONSENSUS_MULTIPASS",
                "observedNotes": selected["notes"],
                "proof": "STRICT_EXACT_MAJORITY_FROM_AT_LEAST_THREE_INDEPENDENT_READS",
                "selected": {
                    "variant": selected["variant"],
                    "psm": selected["psm"],
                    "components": selected["components"],
                },
                "readings": readings,
            }
        return {**base, "result": "CONFLICTING_STRICT_READ", "readings": readings}
    return {
        **base,
        "result": "EXACT_ORDERED_MATCH_MULTIPASS",
        "observedNotes": selected["notes"],
        "proof": "EXACT_HIGH_CONFIDENCE_LABELS; ALL_OTHER_STRICT_READS_ORDERED_SUBSEQUENCES",
        "selected": {
            "variant": selected["variant"],
            "psm": selected["psm"],
            "components": selected["components"],
        },
        "readings": readings,
    }


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    original = json.loads(OUT.read_text(encoding="utf-8"))
    unresolved = {
        item["code"]
        for item in original.get("rows", [])
        if item.get("result") == "READING_NOT_STRICT_ENOUGH"
    }
    lexicon = [line.strip() for line in LEXICON.read_text(encoding="utf-8").splitlines() if line.strip()]
    tasks = [
        (row, str(find_card(row) or ""), lexicon)
        for row in rows
        if code(row.get("code")) in unresolved
    ]
    workers = max(
        1,
        min(int(os.environ.get("SOCIAL_CARD_RECOVERY_WORKERS", "6")), 6, os.cpu_count() or 2),
    )
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(parse_image, *task) for task in tasks]
        for number, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if number % 100 == 0:
                print(f"recovered {number}/{len(tasks)}", flush=True)
    results.sort(key=lambda item: item["code"])
    proven = [
        item
        for item in results
        if item["result"] in {
            "EXACT_ORDERED_MATCH_MULTIPASS",
            "EXACT_ORDERED_MATCH_RELAXED_MULTIPASS",
            "EXACT_ORDERED_MATCH_CONSENSUS_MULTIPASS",
        }
    ]
    RECOVERY_OUT.write_text(
        json.dumps(
            {
                "rule": (
                    "Only an exact reading of the existing ordered catalog notes is proof: "
                    "high-confidence with no conflict; two independent exact-label reads at "
                    ">=35% with no contradictory strict read; a strict exact majority from at "
                    "least three independent reads; or, for standard six-note cards only, "
                    "exact per-slot lexicon consensus from at least two preprocessing families "
                    "per slot with no contradictory strict read. Non-matches never edit notes."
                ),
                "targets": len(tasks),
                "proven": len(proven),
                "rows": results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"targets": len(tasks), "proven": len(proven), "output": str(RECOVERY_OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
