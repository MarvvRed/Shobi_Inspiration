#!/usr/bin/env python3
import json, re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "database" / "assets" / "note-icons"
INDEX = DIR / "index.json"
UPLOAD = DIR / "ChatGPT Image 14 set 2026, 15_12_30.png"
MELBATON_WEBP = DIR / "melbaton-1743.webp"

records = json.loads(INDEX.read_text(encoding="utf-8"))

# Convert user-supplied Melbaton image first.
if UPLOAD.exists():
    with Image.open(UPLOAD) as im:
        im.convert("RGB").save(MELBATON_WEBP, "WEBP", quality=82, method=6)
    UPLOAD.unlink()

converted = 0
for p in sorted(DIR.iterdir()):
    if p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        continue
    if p.name == MELBATON_WEBP.name:
        continue
    out = p.with_suffix(".webp")
    with Image.open(p) as im:
        # Fragrantica note icons are opaque; RGB gives the smallest deterministic output.
        im.convert("RGB").save(out, "WEBP", quality=82, method=6)
    p.unlink()
    converted += 1

for r in records:
    note_id = int(r.get("id") or 0)
    if note_id == 1743:
        r["file"] = "melbaton-1743.webp"
        r["status"] = "ok-manual"
        continue
    f = r.get("file")
    if f:
        r["file"] = re.sub(r"\.(?:jpe?g|png)$", ".webp", f, flags=re.I)

INDEX.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Verify the resulting library.
webps = sorted(DIR.glob("*.webp"))
non_web_images = [p.name for p in DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
missing = []
corrupt = []
for r in records:
    f = r.get("file")
    if not f:
        missing.append(f"{r.get('id')}:{r.get('slug')}")
        continue
    p = DIR / f
    if not p.exists():
        missing.append(f"{r.get('id')}:{r.get('slug')}->{f}")
        continue
    try:
        with Image.open(p) as im:
            im.verify()
    except Exception as e:
        corrupt.append(f"{f}: {e}")

readme = (
    "# Fragrantica note icons\n\n"
    f"WebP icons: {len(webps)}\n"
    f"Index records: {len(records)}\n"
    f"Missing index files: {len(missing)}\n"
    f"Corrupt/unreadable: {len(corrupt)}\n"
    "Format: WebP\n"
    "Source: https://www.fragrantica.com/notes/\n"
    "Melbaton (ID 1743): manual image supplied by repository owner.\n"
)
(DIR / "README.md").write_text(readme, encoding="utf-8")

report = [
    "# Public note icons WebP conversion report",
    "",
    f"- Index records: **{len(records)}**",
    f"- WebP files: **{len(webps)}**",
    f"- Source JPG/PNG remaining: **{len(non_web_images)}**",
    f"- Missing index files: **{len(missing)}**",
    f"- Corrupt/unreadable WebP: **{len(corrupt)}**",
    f"- Converted source files in this run: **{converted}**",
    "- Melbaton ID 1743: **manual image linked as melbaton-1743.webp**",
]
if non_web_images:
    report += ["", "## Remaining non-WebP images", *[f"- {x}" for x in non_web_images]]
if missing:
    report += ["", "## Missing", *[f"- {x}" for x in missing]]
if corrupt:
    report += ["", "## Corrupt", *[f"- {x}" for x in corrupt]]
(ROOT / "database/audits/public-note-icons-webp-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

print(f"records={len(records)} webp={len(webps)} non_web={len(non_web_images)} missing={len(missing)} corrupt={len(corrupt)}")
if non_web_images or missing or corrupt or len(webps) != len(records):
    raise SystemExit(1)
