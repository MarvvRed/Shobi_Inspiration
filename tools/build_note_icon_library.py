#!/usr/bin/env python3
"""Extract one local Fragrantica note icon per validated note name."""

import json
import re
import unicodedata
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "social-card-main-notes-validated.json"
RAW_SOURCE = ROOT / "social-card-main-notes.json"
DATABASE = ROOT / "database_complete.json"
OUTPUT_DIR = ROOT / "note-icons"
MAP_JS = OUTPUT_DIR / "map.js"

X_RANGES = ((75, 167), (195, 287), (316, 408))


def slug(value):
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "note"


def crop_note_icon(image, slot, note_count):
    """Social cards bottom-align the notes panel; its height follows row count."""
    rows = 1 if note_count <= 3 else 2
    panel_top = 852 - 116 * (rows - 1)
    x1, x2 = X_RANGES[slot % 3]
    y1 = panel_top + 53 + 158 * (slot // 3)
    y2 = y1 + 92
    sx, sy = image.width / 1200, image.height / 1200
    return image.crop((round(x1 * sx), round(y1 * sy), round(x2 * sx), round(y2 * sy)))


def main():
    rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(exist_ok=True)
    for old_icon in OUTPUT_DIR.glob("*.webp"):
        old_icon.unlink()
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
        note_count = len(row.get("mainNotes") or [])
        for item in slots:
            name = str(item.get("name") or "").strip()
            try:
                slot = int(item.get("slot")) - 1
            except (TypeError, ValueError):
                continue
            key = " ".join(name.lower().split())
            if not name or key in icons or not 0 <= slot < 6:
                continue
            crop = crop_note_icon(image, slot, note_count)
            crop = crop.resize((96, 96), Image.Resampling.LANCZOS)
            filename = f"{slug(name)}.webp"
            crop.save(OUTPUT_DIR / filename, "WEBP", quality=82, method=6)
            icons[key] = f"note-icons/{filename}"

    # Some note labels were corrected after OCR validation. Their associated
    # card and slot are still authoritative, so use the matching original icon.
    raw_by_code = {
        str(row.get("code") or "").strip(): row
        for row in json.loads(RAW_SOURCE.read_text(encoding="utf-8"))
    }
    catalog = json.loads(DATABASE.read_text(encoding="utf-8"))
    for perfume in catalog:
        source = raw_by_code.get(str(perfume.get("code") or "").strip())
        if not source:
            continue
        card = ROOT / str(source.get("card") or "")
        notes = perfume.get("fragranticaSocialCardNotes") or []
        if not card.is_file():
            continue
        try:
            image = Image.open(card).convert("RGB")
        except Exception:
            continue
        for slot, name in enumerate(notes[:6]):
            name = str(name or "").strip()
            key = " ".join(name.lower().split())
            if not name or key in icons:
                continue
            crop = crop_note_icon(image, slot, len(notes))
            crop = crop.resize((96, 96), Image.Resampling.LANCZOS)
            filename = f"{slug(name)}.webp"
            crop.save(OUTPUT_DIR / filename, "WEBP", quality=82, method=6)
            icons[key] = f"note-icons/{filename}"

    MAP_JS.write_text(
        "window.FRAGRANTICA_NOTE_ICON_MAP=" + json.dumps(icons, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"Extracted {len(icons)} local note icons")


if __name__ == "__main__":
    main()
