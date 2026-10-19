"""Fetch the four pending Fragrantica social cards and report verifiable file metadata.

This deliberately does not modify the certified catalog or canonical social-card manifest.
"""
import csv
import hashlib
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "database/audits/pending-shobi-additions-2026-10-19.json"
MANIFEST = ROOT / "database/fragrantica/social-cards/manifest.csv"
OUT_DIR = ROOT / "artifacts/shobi-pending-social-cards"
REPORT = ROOT / "database/audits/shobi-pending-social-card-download-2026-10-19.json"
BASE = "https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{fid}.jpeg"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
FIELDS = ["prestashop_product_id", "shobi_code", "inspired_by", "original_brand", "original_perfume",
          "identity_status", "fragrantica_status", "fragrantica_id", "fragrantica_url", "social_card_url",
          "local_path", "card_status", "bytes", "sha256", "error"]

def main():
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    if MANIFEST.exists():
        with MANIFEST.open("r", encoding="utf-8-sig", newline="") as f:
            manifest_rows = list(csv.DictReader(f))
    existing_ids = {str(r.get("prestashop_product_id", "")).strip(): r for r in manifest_rows}
    existing_codes = {str(r.get("shobi_code", "")).strip().upper(): r for r in manifest_rows}
    results = []
    for c in audit["candidates"]:
        product_id = str(c.get("prestashop_product_id") or "").strip()
        code = str(c["code"]).strip()
        # Normalize suffix variants in audit codes to official listing reference.
        reference = str(c.get("reference") or code).strip()
        fid = str(c.get("fragrantica_id") or "").strip()
        url = BASE.format(fid=fid)
        row = {
            "code": code, "reference": reference, "prestashop_product_id": product_id,
            "fragrantica_id": fid, "fragrantica_url": c.get("fragrantica_url"),
            "social_card_url": url, "image_path": None, "card_status": "NOT_ATTEMPTED",
            "bytes": None, "sha256": None, "manifest_existing_by_id": existing_ids.get(product_id),
            "manifest_existing_by_code": existing_codes.get(reference.upper()),
            "error": None
        }
        if not product_id.isdigit() or not fid.isdigit():
            row.update(card_status="BLOCKED_MISSING_ID", error="Product ID or Fragrantica ID missing")
            results.append(row); continue
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.content
            if len(data) < 16 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
                row.update(card_status="INVALID_JPEG", bytes=len(data), error="Downloaded response did not have JPEG start/end markers")
            else:
                filename = f"{product_id}_{reference.replace(' ', '_')}_{fid}.jpeg"
                path = OUT_DIR / filename
                path.write_bytes(data)
                row.update(card_status="DOWNLOADED_JPEG_VALIDATED", image_path=str(path.relative_to(ROOT)),
                           bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        except Exception as exc:
            row.update(card_status="DOWNLOAD_FAILED", error=f"{type(exc).__name__}: {exc}")
        results.append(row)
        time.sleep(0.2)
    summary = {
        "audit_date": "2026-10-19",
        "method": "Download Fragrantica social-card JPEG from FID URL; validate JPEG file markers and compute SHA-256.",
        "catalog_changed": False,
        "canonical_manifest_changed": False,
        "visual_note_order_verified": False,
        "results": results,
        "next_step": "Visually inspect downloaded cards and compare their visible note sequence to official notes before adding any manifest rows or certifying products."
    }
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(results) != 4 or any(r["card_status"] != "DOWNLOADED_JPEG_VALIDATED" for r in results):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
