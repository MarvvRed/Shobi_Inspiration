#!/usr/bin/env python3
"""Non-destructive pilot: identify Social Card Main Notes from note icons.

This script does NOT promote any catalog row. It measures whether the remaining
READING_NOT_STRICT_ENOUGH cards can be reconstructed from the visible note icons
using the local Fragrantica icon archive.

Safety properties:
- Catalog notes never guide segmentation or icon recognition.
- Each detected icon is matched against the full local icon corpus.
- Recognition combines shape, colour and a perceptual edge hash.
- A match is high-confidence only when absolute similarity and runner-up separation
  both clear conservative thresholds.
- The catalog sequence is compared only after the full image-derived sequence is fixed.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess

import numpy as np
from PIL import Image

from audit_social_card_order_from_images import ROOT, DB, OUT, CROP, code, find_card

MAP = ROOT / "database/assets/note-icons/map.js"
PILOT_OUT = ROOT / "database/audits/icon-match-pilot.json"
ICON_SIZE = 48
RGB_SIZE = 24
HASH_SIZE = 16
ABS_THRESHOLD = 0.78
MARGIN_THRESHOLD = 0.030


def parse_map():
    txt = MAP.read_text(encoding="utf-8").strip()
    m = re.match(r"^window\.[A-Z0-9_]+\s*=\s*(\{.*\})\s*;?$", txt, re.S)
    if not m:
        raise SystemExit("Cannot parse note icon map")
    obj = json.loads(m.group(1))
    return [(name, ROOT / rel) for name, rel in obj.items() if (ROOT / rel).is_file()]


def foreground_bbox(arr):
    dist = 255 - arr.min(axis=2)
    mask = dist > 14
    ys, xs = np.where(mask)
    if len(xs) < 20:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _unit(vec):
    vec = np.asarray(vec, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vec))
    if norm < 1e-6:
        return None
    return vec / norm


def normalize_icon(im):
    rgba = im.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    bg.alpha_composite(rgba)
    arr = np.asarray(bg.convert("RGB"), dtype=np.uint8)
    box = foreground_bbox(arr)
    if not box:
        return None
    x1, y1, x2, y2 = box
    crop = Image.fromarray(arr[y1:y2, x1:x2])

    shape_crop = crop.copy()
    shape_crop.thumbnail((ICON_SIZE - 4, ICON_SIZE - 4), Image.Resampling.LANCZOS)
    shape_canvas = Image.new("L", (ICON_SIZE, ICON_SIZE), 255)
    gray = shape_crop.convert("L")
    shape_canvas.paste(gray, ((ICON_SIZE-gray.width)//2, (ICON_SIZE-gray.height)//2))
    shape = _unit(255.0 - np.asarray(shape_canvas, dtype=np.float32))
    if shape is None:
        return None

    rgb_crop = crop.copy()
    rgb_crop.thumbnail((RGB_SIZE - 2, RGB_SIZE - 2), Image.Resampling.LANCZOS)
    rgb_canvas = Image.new("RGB", (RGB_SIZE, RGB_SIZE), (255, 255, 255))
    rgb_canvas.paste(rgb_crop, ((RGB_SIZE-rgb_crop.width)//2, (RGB_SIZE-rgb_crop.height)//2))
    rgb_arr = np.asarray(rgb_canvas, dtype=np.float32)
    colour = _unit((255.0 - rgb_arr).reshape(-1))
    if colour is None:
        return None

    h = crop.convert("L").resize((HASH_SIZE + 1, HASH_SIZE), Image.Resampling.LANCZOS)
    ha = np.asarray(h, dtype=np.float32)
    dhash = _unit((ha[:, 1:] < ha[:, :-1]).astype(np.float32).reshape(-1))
    if dhash is None:
        dhash = np.zeros(HASH_SIZE * HASH_SIZE, dtype=np.float32)

    combined = np.concatenate((shape * 0.52, colour * 0.36, dhash * 0.12))
    return _unit(combined)


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


def _best_grid_centres(smooth, gutter, width):
    """Infer 2/3/4 equally-spaced Social Card cells from image energy only."""
    usable = smooth[gutter:width-gutter]
    if usable.size == 0 or float(usable.max()) < 2.0:
        return []
    best = None
    # Social Card rows are laid out on a regular horizontal grid. Score candidate
    # 2/3/4-cell grids by summed local foreground energy minus irregularity penalty.
    for n in (2, 3, 4):
        span = width - 2 * gutter
        step = span / n
        centres = [gutter + step * (i + 0.5) for i in range(n)]
        snapped = []
        score = 0.0
        for c in centres:
            lo = max(gutter, int(round(c - step * 0.28)))
            hi = min(width - gutter, int(round(c + step * 0.28)))
            if hi <= lo:
                break
            x = lo + int(np.argmax(smooth[lo:hi]))
            snapped.append(x)
            score += float(smooth[x])
        if len(snapped) != n:
            continue
        gaps = np.diff(snapped)
        if len(gaps):
            irregularity = float(np.std(gaps) / max(1.0, np.mean(gaps)))
        else:
            irregularity = 0.0
        mean_peak = score / n
        # Penalize grids that manufacture weak extra cells.
        floor = float(np.percentile(usable, 70))
        weak = sum(float(smooth[x]) < max(1.8, floor) for x in snapped)
        objective = mean_peak - irregularity * 8.0 - weak * 2.5
        if best is None or objective > best[0]:
            best = (objective, snapped, step)
    return best[1:] if best else []


def segments_from_band(panel_rgb, y1, y2):
    """Infer the regular Social Card grid, then crop exactly one icon per cell."""
    arr = panel_rgb[max(0, int(y1)):min(panel_rgb.shape[0], int(y2)), :, :]
    if arr.size == 0:
        return []
    width = arr.shape[1]
    dist = 255 - arr.min(axis=2)
    mask = dist > 18
    gutter = 28
    if width <= gutter * 2 + 80:
        return []
    mask[:, :gutter] = False
    mask[:, width-gutter:] = False

    energy = mask.sum(axis=0).astype(np.float32)
    kernel = np.ones(17, dtype=np.float32) / 17.0
    smooth = np.convolve(energy, kernel, mode="same")
    grid = _best_grid_centres(smooth, gutter, width)
    if not grid:
        return []
    centres, step = grid

    out = []
    half = int(min(34, max(24, step * 0.32)))
    for cx in centres:
        xa = max(gutter, int(round(cx - half)))
        xb = min(width - gutter, int(round(cx + half)))
        local = mask[:, xa:xb]
        ys, xs = np.where(local)
        if len(xs) < 35:
            continue
        vertical_span = int(ys.max()) - int(ys.min()) + 1
        horizontal_span = int(xs.max()) - int(xs.min()) + 1
        if vertical_span < 18 or horizontal_span < 12:
            continue
        out.append((xa, xb))
    return out


def match_tile(tile, ref_names, ref_matrix):
    vec = normalize_icon(tile)
    if vec is None:
        return None
    scores = ref_matrix @ vec
    if len(scores) < 3:
        return None
    idx = np.argpartition(scores, -3)[-3:]
    idx = idx[np.argsort(scores[idx])[::-1]]
    best, second, third = map(int, idx[:3])
    s1, s2, s3 = float(scores[best]), float(scores[second]), float(scores[third])
    margin = s1 - s2
    confident = bool(s1 >= ABS_THRESHOLD and margin >= MARGIN_THRESHOLD)
    return {
        "note": ref_names[best],
        "score": round(s1, 4),
        "runnerUp": ref_names[second],
        "runnerUpScore": round(s2, 4),
        "third": ref_names[third],
        "thirdScore": round(s3, 4),
        "margin": round(margin, 4),
        "confident": confident,
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
    bands = [(header_y+12, header_y+86), (header_y+148, header_y+222)]
    details = []
    row_counts = []
    for row_idx, (ya,yb) in enumerate(bands):
        segs = segments_from_band(arr, ya, yb)
        row_counts.append(len(segs))
        for xa, xb in segs:
            tile = panel.crop((xa, max(0,int(ya)), xb, min(380,int(yb))))
            hit = match_tile(tile, ref_names, ref_matrix)
            if hit:
                details.append({"row": row_idx, "x": [xa,xb], **hit})
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
        "rowCounts": row_counts,
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
        "mode": "NON_DESTRUCTIVE_GRID_INFERRED_MULTIMODAL_ICON_PILOT",
        "thresholds": {"combinedCosine": ABS_THRESHOLD, "runnerUpMargin": MARGIN_THRESHOLD},
        "featureWeights": {"shape": 0.52, "colour": 0.36, "dHash": 0.12},
        "referenceIcons": len(ref_names),
        "targets": len(targets),
        "counts": dict(sorted(counts.items())),
        "rows": results,
    }
    PILOT_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"targets": len(targets), "counts": payload["counts"], "output": str(PILOT_OUT)}, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
