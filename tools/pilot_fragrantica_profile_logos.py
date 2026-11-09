#!/usr/bin/env python3
"""Isolated pilot: fetch Fragrantica profile-page logo images (o.*.jpg).

Does not modify the main brand archive or its existing t.* assets.
"""
from __future__ import annotations
import argparse, hashlib, json, re, time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "database/assets/brand-logos-profile-pilot"
MANIFEST = ROOT / "database/brands/brands_logos_profile_pilot.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
DEFAULTS = {
    "Avon": "https://www.fragrantica.com/designers/Avon.html",
    "Guerlain": "https://www.fragrantica.com/designers/Guerlain.html",
    "Zara": "https://www.fragrantica.com/designers/Zara.html",
}

def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=5.0)
    ap.add_argument("--brand", action="append", help="Brand name; may be repeated")
    args = ap.parse_args()
    selected = {name: DEFAULTS[name] for name in (args.brand or list(DEFAULTS)) if name in DEFAULTS}
    if not selected:
        ap.error("No known pilot brands selected. Available: " + ", ".join(DEFAULTS))
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for idx, (brand, page_url) in enumerate(selected.items()):
        row = {"brand_name": brand, "profile_url": page_url, "status": "failed"}
        try:
            response = session.get(page_url, timeout=45)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            candidates = []
            for a in soup.find_all("a", href=True):
                href = urljoin(page_url, a["href"])
                path = urlparse(href).path
                if not re.search(r"/dizajneri/o\.\d+\.jpg$", path, re.I):
                    continue
                labels = [a.get_text(" ", strip=True), a.get("title", ""), a.get("aria-label", "")]
                labels.extend(img.get("alt", "") for img in a.find_all("img"))
                labels.extend(img.get("title", "") for img in a.find_all("img"))
                label = " ".join(x for x in labels if x).strip()
                if "logo" in label.lower() and all(existing[0] != href for existing in candidates):
                    candidates.append((href, label))
            if len(candidates) != 1:
                row["status"] = "ambiguous" if candidates else "no_profile_logo_link"
                row["candidate_links"] = [{"url": u, "label": l} for u, l in candidates]
            else:
                image_url, label = candidates[0]
                img_response = session.get(image_url, timeout=45)
                img_response.raise_for_status()
                with Image.open(BytesIO(img_response.content)) as im:
                    im.verify()
                with Image.open(BytesIO(img_response.content)) as im:
                    im.seek(0); im.load()
                    width, height = im.size
                    im.thumbnail((640, 640), Image.Resampling.LANCZOS)
                    if im.mode not in ("RGB", "RGBA"):
                        im = im.convert("RGBA" if "transparency" in im.info else "RGB")
                    target = OUT / f"{slug(brand)}.webp"
                    im.save(target, "WEBP", quality=90, method=6)
                row.update({"status": "downloaded", "source_image_url": image_url,
                            "source_label": label, "width": width, "height": height,
                            "local_path": target.relative_to(ROOT).as_posix(),
                            "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        except (requests.RequestException, OSError, ValueError, UnidentifiedImageError) as exc:
            row["error"] = str(exc)[:300]
        results.append(row)
        print(f"[{row['status'].upper()}] {brand}: {row.get('source_image_url', row.get('error', 'no unique logo link'))}", flush=True)
        if idx < len(selected) - 1:
            time.sleep(max(5.0, args.delay))
    output = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "purpose": "isolated comparison pilot; does not replace directory-thumbnail archive",
              "brands": results}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[DONE] {MANIFEST}", flush=True)
    return 0 if any(x["status"] == "downloaded" for x in results) else 2

if __name__ == "__main__":
    raise SystemExit(main())
