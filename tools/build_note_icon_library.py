#!/usr/bin/env python3
"""Extract one local Fragrantica note icon per validated note name."""

import json
import re
import unicodedata
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "social-card-main-notes-validated.json"
OUTPUT_DIR = ROOT / "note-icons"
MAP_JS = OUTPUT_DIR / "map.js"
X_RANGES = ((75, 167), (195, 287), (316, 408))
Y_RANGES = ((795, 887), (929, 1021))

def slug(value):
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "note"

def main():
    rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(exist_ok=True)
    icons = {}
    for row in rows:
        if not row.get("validated"):
            continue
        card = ROOT / str(row.get("card") or "")
        if not card.is_file():
            continue
        slots = row.get("validatedSlots") or []
        try:
            image = Image.open(card).convert("RGB")
        except Exception:
            continue
        sx, sy = image.width / 1200, image.height / 1200
        for item in slots:
            name = str(item.get("name") or "").strip()
            try:
                slot = int(item.get("slot")) - 1
            except (TypeError, ValueError):
                continue
            key = " ".join(name.lower().split())
            if not name or key in icons or not 0 <= slot < 6:
                continue
            x1, x2 = X_RANGES[slot % 3]
            y1, y2 = Y_RANGES[slot // 3]
            crop = image.crop((round(x1*sx), round(y1*sy), round(x2*sx), round(y2*sy)))
            crop = crop.resize((96, 96), Image.Resampling.LANCZOS)
            filename = f"{slug(name)}.webp"
            crop.save(OUTPUT_DIR / filename, "WEBP", quality=82, method=6)
            icons[key] = f"note-icons/{filename}"
    MAP_JS.write_text("window.FRAGRANTICA_NOTE_ICON_MAP=" + json.dumps(icons, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"Extracted {len(icons)} local note icons")

if __name__ == "__main__":
    main()
