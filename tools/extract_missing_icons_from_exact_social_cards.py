#!/usr/bin/env python3
"""Fill only missing note icons by cropping their proved Social Card tiles.

No note name is inferred here. A crop is allowed only when the current catalog
sequence is already an EXACT_ORDERED_MATCH from the same Fragrantica ID.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
ICON_DIR = ROOT / "database/assets/note-icons"
MAP = ICON_DIR / "map.js"
REPORT = ROOT / "database/audits/missing-icons-from-exact-social-cards.json"
X_RANGES = ((75, 167), (195, 287), (316, 408))


def key(value):
    return " ".join(str(value or "").strip().lower().split())


def slug(value):
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "note"


def crop_icon(image, slot, note_count):
    rows = 1 if note_count <= 3 else 2
    panel_top = 852 - 116 * (rows - 1)
    x1, x2 = X_RANGES[slot % 3]
    y1 = panel_top + 53 + 158 * (slot // 3)
    y2 = y1 + 92
    sx, sy = image.width / 1200, image.height / 1200
    return image.crop((round(x1 * sx), round(y1 * sy), round(x2 * sx), round(y2 * sy)))


def main():
    prefix = "window.FRAGRANTICA_NOTE_ICON_MAP="
    raw_map = MAP.read_text(encoding="utf-8").strip()
    if not raw_map.startswith(prefix):
        raise SystemExit("Invalid note icon map")
    icon_map = json.loads(raw_map[len(prefix):].rstrip(";"))
    audit_rows = json.loads(AUDIT.read_text(encoding="utf-8")).get("rows", [])
    audit_by_code = {key(item.get("code")).upper(): item for item in audit_rows}
    changes = []

    for row in json.loads(DB.read_text(encoding="utf-8-sig")):
        notes = list(row.get("fragranticaSocialCardNotes") or [])
        if not notes:
            continue
        missing = [(slot, note) for slot, note in enumerate(notes[:6]) if key(note) not in icon_map]
        if not missing:
            continue
        audit = audit_by_code.get(key(row.get("code")).upper())
        fid = str(row.get("fragranticaId") or "")
        if not audit or audit.get("result") != "EXACT_ORDERED_MATCH":
            continue
        if str(audit.get("fragranticaId") or "") != fid or list(audit.get("observedNotes") or []) != notes:
            continue
        card = ROOT / str(audit.get("card") or "")
        if not card.is_file():
            continue
        try:
            image = Image.open(card).convert("RGB")
        except Exception:
            continue
        for slot, note in missing:
            icon = crop_icon(image, slot, len(notes)).resize((96, 96), Image.Resampling.LANCZOS)
            filename = f"{slug(note)}.webp"
            target = ICON_DIR / filename
            icon.save(target, "WEBP", quality=82, method=6)
            icon_map[key(note)] = f"database/assets/note-icons/{filename}"
            changes.append({"code": row.get("code"), "fragranticaId": fid, "note": note,
                            "slot": slot + 1, "card": str(audit.get("card") or ""),
                            "icon": str(target.relative_to(ROOT))})

    MAP.write_text(prefix + json.dumps(icon_map, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    REPORT.write_text(json.dumps({
        "rule": "Icon crops come only from the exact ordered Social Card that proved the saved note sequence.",
        "count": len(changes), "changes": changes,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"exactSocialCardIconCrops": len(changes)}, indent=2))


if __name__ == "__main__":
    main()
