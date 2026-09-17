#!/usr/bin/env python3
"""Non-destructive pilot: identify Social Card Main Notes from note icons.

This script does NOT promote any catalog row. It measures whether the remaining
READING_NOT_STRICT_ENOUGH cards can be reconstructed from the visible note icons
using the local Fragrantica icon archive.

Safety properties:
- Catalog notes never guide segmentation or icon recognition.
- Each detected icon is matched against the full local icon corpus.
- A match is considered high-confidence only when both absolute similarity and
  separation from the runner-up clear conservative thresholds.
- The catalog sequence is compared only after the full image-derived sequence is fixed.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from audit_social_card_order_from_images import ROOT, DB, OUT, CROP, code, find_card

MAP = ROOT / "database/assets/note-icons/map.js"
PILOT_OUT = ROOT / "database/audits/icon-match-pilot.json"
ICON_SIZE = 48
ABS_THRESHOLD = 0.72
MARGIN_THRESHOLD = 0.055


def parse_map():
    txt = MAP.read_text(encoding="utf-8").strip()
    m = re.match(r"^window\.[A-Z0-9_]+\s*=\s*(\{.*\})\s*;?$", txt, re.S)
    if not m:
        raise SystemExit("Cannot parse note icon map")
    obj = json.loads(m.group(1))
    return [(name, ROOT / rel) for name, rel in obj.items() if (ROOT / rel).is_file()]


def foreground_bbox(arr):
    # RGB array on white background. Keep colored/dark icon pixels, ignore white.
    dist = 255 - arr.min(axis=2)
    mask = dist > 14
    ys, xs = np.where(mask)
    if len(xs) < 20:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def normalize_icon(im):
    rgb = im.convert("RGBA")
    bg = Image.new("RGBA", rgb.size, (255, 255, 255, 255))
    bg.alpha_composite(rgb)
    arr = np.asarray(bg.convert("RGB"), dtype=np.uint8)
    box = foreground_bbox(arr)
    if not box:
        return None
    x1, y1, x2, y2 = box
    crop = Image.fromarray(arr[y1:y2, x1:x2])
    # Preserve aspect ratio on a square white canvas.
    crop.thumbnail((ICON_SIZE - 4, ICON_SIZE - 4), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (ICON_SIZE, ICON_SIZE), 255)
    gray = crop.convert("L")
    canvas.paste(gray, ((ICON_SIZE - gray.width)//2, (ICON_SIZE - gray.height)//2))
    vec = np.asarray(canvas, dtype=np.float32).reshape(-1)
    vec = 255.0 - vec  # foreground becomes positive signal
    norm = float(np.linalg.norm(vec))
    if norm < 1e-6:
        return None
    return vec / norm


def build_reference_matrix(items):
    names, vecs = [], []
    for name, path in items:
        try:
            with Image.open(path) as im:
                vec = normalize_icon(im)
        except Exception:
            continue
        if vec is not None:
            names.append(name)
            vecs.append(vec)
    if not vecs:
        raise SystemExit("No reference icons loaded")
    return names, np.stack(vecs).astype(np.float32)


def locate_notes_header(panel):
    # One cheap OCR pass only to locate the heading; note identity never comes from OCR here.
    scaled = panel.resize((panel.width*3, panel.height*3), Image.Resampling.LANCZOS)
    buf = io.BytesIO(); scaled.save(buf, format="PNG")
    try:
        run = subprocess.run(
            ["tesseract", "stdin", "stdout", "--psm", "11", "-l", "eng", "tsv"],
            input=buf.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10, check=True, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        )
    except Exception:
        return None
    hits = []
    for row in csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t"):
        text = re.sub(r"[^a-z]", "", str(row.get("text") or "").lower())
        if text != "notes":
            continue
        try:
            y = int(row.get("top") or 0) / 3
            x = int(row.get("left") or 0) / 3
            conf = float(row.get("conf") or -1)
        except Exception:
            continue
        if x < 180 and y < 150 and conf >= 30:
            hits.append(y)
    return min(hits) if hits else None


def segments_from_band(panel_rgb, y1, y2):
    arr = panel_rgb[max(0, int(y1)):min(panel_rgb.shape[0], int(y2)), :, :]
    if arr.size == 0:
        return []

    # Icons are colored/dark against white. Text labels are below these narrow bands.
    # Keep segmentation deliberately independent from catalog note count/content.
    dist = 255 - arr.min(axis=2)
    mask = dist > 18
    active = (mask.sum(axis=0) >= 3).tolist()

    # Bridge only tiny holes inside a silhouette. The old <=10 px bridge could join
    # neighbouring note tiles before they were even measured.
    i = 0
    while i < len(active):
        if active[i]:
            i += 1
            continue
        j = i
        while j < len(active) and not active[j]:
            j += 1
        if i > 0 and j < len(active) and (j - i) <= 4:
            for k in range(i, j):
                active[k] = True
        i = j

    # First collect raw foreground runs without generous padding. Small fragments are
    # retained here because one icon can legitimately contain disconnected shapes.
    raw, start = [], None
    for x, val in enumerate(active + [False]):
        if val and start is None:
            start = x
        elif start is not None and not val:
            width = x - start
            if 5 <= width <= 90:
                raw.append((start, x))
            start = None

    # Join fragments only when the union still has the geometry of ONE icon.
    # This is the critical guard missing from the first pilot: previously any chain of
    # gaps <16 px could grow into a 200-300 px crop containing multiple icons/text.
    merged = []
    for seg in raw:
        if merged:
            prev = merged[-1]
            gap = seg[0] - prev[1]
            union_width = seg[1] - prev[0]
            if 0 <= gap <= 8 and union_width <= 82:
                merged[-1] = (prev[0], seg[1])
                continue
        merged.append(seg)

    # Add a small context margin only after merging and reject residual noise. A note
    # tile in these 74 px bands must have a meaningful horizontal AND vertical span.
    out = []
    band_h = arr.shape[0]
    for xa, xb in merged:
        xa = max(0, xa - 4)
        xb = min(panel_rgb.shape[1], xb + 4)
        width = xb - xa
        if not (18 <= width <= 90):
            continue
        local_mask = mask[:, max(0, xa):min(mask.shape[1], xb)]
        ys = np.where(local_mask)[0]
        if len(ys) < 20:
            continue
        vertical_span = int(ys.max()) - int(ys.min()) + 1
        if vertical_span < max(16, int(band_h * 0.28)):
            continue
        out.append((xa, xb))

    # Social Card geometry supports at most four note tiles per row. Sorting keeps
    # visual left-to-right order explicit and prevents edge noise from reordering it.
    out.sort(key=lambda p: p[0])
    return out[:4]


def match_tile(tile, ref_names, ref_matrix):
    vec = normalize_icon(tile)
    if vec is None:
        return None
    scores = ref_matrix @ vec
    if len(scores) < 2:
        return None
    idx = np.argpartition(scores, -2)[-2:]
    idx = idx[np.argsort(scores[idx])[::-1]]
    best, second = int(idx[0]), int(idx[1])
    s1, s2 = float(scores[best]), float(scores[second])
    return {
        "note": ref_names[best],
        "score": round(s1, 4),
        "runnerUp": ref_names[second],
        "runnerUpScore": round(s2, 4),
        "margin": round(s1-s2, 4),
        "confident": bool(s1 >= ABS_THRESHOLD and s1-s2 >= MARGIN_THRESHOLD),
    }


def inspect(row, ref_names, ref_matrix):
    c = code(row.get("code")); card = find_card(row)
    base = {"code": c, "fid": str(row.get("fragranticaId") or "")}
    if not card:
        return {**base, "result": "NO_CARD"}
    try:
        with Image.open(card) as src:
            if src.width < 800 or src.height < 800 or src.height/src.width < 0.85:
                return {**base, "result": "UNSUPPORTED_GEOMETRY", "size": [src.width, src.height]}
            sx, sy = src.width/1200, src.height/1200
            x1,y1,x2,y2 = CROP
            panel = src.crop((round(x1*sx), round(y1*sy), round(x2*sx), round(y2*sy))).convert("RGB").resize((420,380), Image.Resampling.LANCZOS)
    except Exception as exc:
        return {**base, "result": "IMAGE_ERROR", "error": str(exc)}

    header_y = locate_notes_header(panel)
    if header_y is None:
        return {**base, "result": "NO_NOTES_HEADER"}
    arr = np.asarray(panel, dtype=np.uint8)
    # Icon-only bands end before the label bands used by the existing OCR parser.
    bands = [(header_y+12, header_y+86), (header_y+148, header_y+222)]
    sequence, details = [], []
    for row_idx, (ya,yb) in enumerate(bands):
        segs = segments_from_band(arr, ya, yb)
        for xa, xb in segs:
            tile = panel.crop((xa, max(0,int(ya)), xb, min(380,int(yb))))
            hit = match_tile(tile, ref_names, ref_matrix)
            if hit:
                details.append({"row": row_idx, "x": [xa,xb], **hit})
                if hit["confident"]:
                    sequence.append(hit["note"])
                else:
                    sequence.append(None)
    if not details:
        return {**base, "result": "NO_ICON_SEGMENTS", "headerY": round(header_y,1)}
    all_conf = all(x["confident"] for x in details)
    observed = [x["note"] for x in details] if all_conf else []
    catalog = list(row.get("fragranticaSocialCardNotes") or [])
    exact = bool(all_conf and observed and observed == catalog)
    return {
        **base,
        "result": "EXACT_ICON_SEQUENCE" if exact else ("COMPLETE_ICON_SEQUENCE_DIFFERENT" if all_conf else "ICON_MATCH_AMBIGUOUS"),
        "headerY": round(header_y,1),
        "detectedCount": len(details),
        "observed": observed,
        "catalog": catalog,
        "details": details,
    }


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    audit = json.loads(OUT.read_text(encoding="utf-8"))
    by_code = {code(r.get("code")): r for r in rows}
    targets = [by_code[code(x.get("code"))] for x in audit.get("rows", [])
               if x.get("result") == "READING_NOT_STRICT_ENOUGH" and code(x.get("code")) in by_code]
    limit = int(os.environ.get("ICON_PILOT_LIMIT", "0"))
    if limit > 0:
        targets = targets[:limit]
    ref_names, ref_matrix = build_reference_matrix(parse_map())
    print(json.dumps({"referenceIcons": len(ref_names), "targets": len(targets)}), flush=True)
    results = []
    for i, row in enumerate(targets, 1):
        results.append(inspect(row, ref_names, ref_matrix))
        if i % 25 == 0:
            print(f"processed {i}/{len(targets)}", flush=True)
    counts = {}
    for r in results:
        counts[r["result"]] = counts.get(r["result"], 0) + 1
    payload = {
        "mode": "NON_DESTRUCTIVE_ICON_MATCH_PILOT",
        "thresholds": {"absoluteCosine": ABS_THRESHOLD, "runnerUpMargin": MARGIN_THRESHOLD},
        "referenceIcons": len(ref_names),
        "targets": len(targets),
        "counts": dict(sorted(counts.items())),
        "rows": results,
    }
    PILOT_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"targets": len(targets), "counts": payload["counts"], "output": str(PILOT_OUT)}, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
