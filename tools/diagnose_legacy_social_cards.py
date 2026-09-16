#!/usr/bin/env python3
"""Capture OCR/layout diagnostics for the four legacy Fragrantica Social Cards.

Diagnostic only: never changes verification state or catalog data.
"""
from __future__ import annotations

import csv, io, json, os, subprocess
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps

from audit_social_card_order_from_images import DB, OUT, code, find_card

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "database/fragrantica/social-cards/records/legacy-social-card-diagnostics.json"
TARGETS = {"118-HAM", "1251-ROM", "235-HOLL", "325-PECK"}


def run_ocr(image, psm):
    img = ImageOps.autocontrast(image.convert("L"))
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    run = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng", "tsv"],
        input=buf.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        timeout=25, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    )
    words = []
    for r in csv.DictReader(io.StringIO(run.stdout.decode("utf-8", "replace")), delimiter="\t"):
        text = " ".join(str(r.get("text") or "").split())
        if not text:
            continue
        try: conf = float(r.get("conf") or -1)
        except Exception: conf = -1
        if conf < 20:
            continue
        words.append({
            "text": text,
            "confidence": round(conf, 1),
            "left": round(int(r.get("left") or 0) / 2, 1),
            "top": round(int(r.get("top") or 0) / 2, 1),
            "width": round(int(r.get("width") or 0) / 2, 1),
            "height": round(int(r.get("height") or 0) / 2, 1),
            "block": int(r.get("block_num") or 0),
            "line": int(r.get("line_num") or 0),
        })
    lines = {}
    for w in words:
        key = f'{w["block"]}:{w["line"]}'
        lines.setdefault(key, []).append(w)
    readable_lines = []
    for key, ws in lines.items():
        ws.sort(key=lambda x: x["left"])
        readable_lines.append({
            "key": key,
            "text": " ".join(x["text"] for x in ws),
            "left": min(x["left"] for x in ws),
            "top": min(x["top"] for x in ws),
            "right": max(x["left"] + x["width"] for x in ws),
            "bottom": max(x["top"] + x["height"] for x in ws),
            "minConfidence": min(x["confidence"] for x in ws),
        })
    readable_lines.sort(key=lambda x: (x["top"], x["left"]))
    return {"psm": psm, "lines": readable_lines, "words": words}


def main():
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    audit = json.loads(OUT.read_text(encoding="utf-8"))
    audit_by_code = {code(x.get("code")): x for x in audit.get("rows", [])}
    output = []
    for row in rows:
        c = code(row.get("code"))
        if c not in TARGETS:
            continue
        card = find_card(row)
        rec = {
            "code": c,
            "fragranticaId": str(row.get("fragranticaId") or ""),
            "catalogNotes": list(row.get("fragranticaSocialCardNotes") or []),
            "currentAuditResult": (audit_by_code.get(c) or {}).get("result"),
            "card": str(card.relative_to(ROOT)) if card else None,
        }
        if not card:
            rec["error"] = "NO_CARD_FILE"
            output.append(rec)
            continue
        try:
            with Image.open(card) as im:
                rec["size"] = [im.width, im.height]
                rec["ocr"] = [run_ocr(im, psm) for psm in (3, 6, 11, 12)]
        except Exception as exc:
            rec["error"] = str(exc)
        output.append(rec)
    DIAG.write_text(json.dumps({"targets": sorted(TARGETS), "rows": output}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{k: r.get(k) for k in ("code","fragranticaId","size","card","error")} for r in output], ensure_ascii=False))

if __name__ == "__main__":
    main()
