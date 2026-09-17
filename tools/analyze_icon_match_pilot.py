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
    crop.thumbnail((ICON_SIZE - 4, ICON_SIZE - 4), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (ICON_SIZE, ICON_SIZE), 255)
    gray = crop.convert("L")
    canvas.paste(gray, ((ICON_SIZE - gray.width)//2, (ICON_SIZE - gray.height)//2))
    vec = np.asarray(canvas, dtype=np.float32).reshape(-1)
    vec = 255.0 - vec
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
    """Find icon slots by foreground-energy peaks, not by connected-run width.

    The card crop has persistent decorative/edge pixels near x=0 and x=420. The old
    run-merging segmenter treated those as icons and could also merge several nearby
    fragments into an 80+ px pseudo-icon. Here we first remove the unsafe side gutters,
    then identify independent icon centres from a smoothed horizontal energy profile.
    Fixed-width crops around those centres prevent one candidate from swallowing two
    neighbouring note tiles. No catalog note count or identity is used.
    """
    arr = panel_rgb[max(0, int(y1)):min(panel_rgb.shape[0], int(y2)), :, :]
    if arr.size == 0:
        return []

    width = arr.shape[1]
    dist = 255 - arr.min(axis=2)
    mask = dist > 18

    # The first/last ~25 px repeatedly contain card border/background artifacts.
    gutter = 28
    if width <= gutter * 2 + 40:
        return []
    mask[:, :gutter] = False
    mask[:, width-gutter:] = False

    # Horizontal foreground energy. Smooth over 13 px so disconnected pieces of one
    # pictogram vote for the same centre while remaining much narrower than tile gaps.
    energy = mask.sum(axis=0).astype(np.float32)
    kernel = np.ones(13, dtype=np.float32) / 13.0
    smooth = np.convolve(energy, kernel, mode="same")

    # Reject weak noise relative to this row. An actual icon occupies many rows and has
    # a broad local peak; edge specks and isolated letters do not.
    usable = smooth[gutter:width-gutter]
    if usable.size == 0 or float(usable.max()) < 2.0:
        return []
    threshold = max(1.8, float(usable.max()) * 0.24)

    candidates = []
    for x in range(gutter + 1, width - gutter - 1):
        v = float(smooth[x])
        if v < threshold:
            continue
        if v >= float(smooth[x-1]) and v >= float(smooth[x+1]):
            candidates.append((v, x))

    # Non-maximum suppression: one centre per icon. Social Card note tiles are well
    # separated horizontally; 62 px is conservative even for four-column layouts.
    chosen = []
    for score, x in sorted(candidates, reverse=True):
        if all(abs(x - cx) >= 62 for _, cx in chosen):
            chosen.append((score, x))
        if len(chosen) == 4:
            break

    # Validate each centre using a fixed 76 px crop. This eliminates the old failure
    # mode where a merged run became 100-300 px wide and included adjacent icons/text.
    out = []
    half = 38
    for _, cx in sorted(chosen, key=lambda p: p[1]):
        xa = max(gutter, cx - half)
        xb = min(width - gutter, cx + half)
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
