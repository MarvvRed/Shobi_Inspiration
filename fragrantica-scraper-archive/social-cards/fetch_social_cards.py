#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
MAPPING = ROOT / "data" / "shobi-fragrantica-mapping.csv"
OUT_DIR = ROOT / "fragrantica-scraper-archive" / "social-cards" / "images"
MANIFEST = ROOT / "fragrantica-scraper-archive" / "social-cards" / "manifest.csv"
BASE = "https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{id}.jpeg"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
TIMEOUT = 30
RETRIES = 3
DELAY = float(os.environ.get("SOCIAL_CARD_DELAY", "0.15"))

FIELDS = [
    "prestashop_product_id", "shobi_code", "inspired_by", "original_brand",
    "original_perfume", "identity_status", "fragrantica_status", "fragrantica_id",
    "fragrantica_url", "social_card_url", "local_path", "card_status", "bytes",
    "sha256", "error"
]


def safe(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    return value.strip("._") or "unknown"


def is_jpeg(data: bytes) -> bool:
    return len(data) > 16 and data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")


def fetch(url: str) -> tuple[bytes | None, str]:
    last = ""
    for attempt in range(1, RETRIES + 1):
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"})
            with urlopen(req, timeout=TIMEOUT) as r:
                data = r.read(5_000_000)
            if not is_jpeg(data):
                return None, f"invalid jpeg payload ({len(data)} bytes)"
            return data, ""
        except HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 404:
                break
        except (URLError, TimeoutError, OSError) as e:
            last = f"{type(e).__name__}: {e}"
        if attempt < RETRIES:
            time.sleep(attempt * 1.5)
    return None, last or "download failed"


def row_result(row: dict[str, str]) -> dict[str, str]:
    out = {k: row.get(k, "") for k in FIELDS}
    fid = (row.get("fragrantica_id") or "").strip()
    identity = (row.get("identity_status") or "").strip().upper()
    fstatus = (row.get("fragrantica_status") or "").strip().upper()

    if identity != "CONFIRMED" or fstatus != "FOUND" or not fid.isdigit():
        out.update(card_status="NO_CONFIRMED_ID", social_card_url="", local_path="", bytes="", sha256="", error="")
        return out

    url = BASE.format(id=fid)
    filename = f"{safe(row.get('prestashop_product_id',''))}_{safe(row.get('shobi_code',''))}_{fid}.jpeg"
    path = OUT_DIR / filename
    rel = path.relative_to(ROOT).as_posix()
    out["social_card_url"] = url
    out["local_path"] = rel

    if path.exists():
        data = path.read_bytes()
        if is_jpeg(data):
            out.update(card_status="EXISTS", bytes=str(len(data)), sha256=hashlib.sha256(data).hexdigest(), error="")
            return out
        path.unlink(missing_ok=True)

    data, error = fetch(url)
    if data is None:
        out.update(card_status="MISSING", bytes="", sha256="", error=error)
        return out

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    out.update(card_status="DOWNLOADED", bytes=str(len(data)), sha256=hashlib.sha256(data).hexdigest(), error="")
    return out


def main() -> int:
    if not MAPPING.exists():
        print(f"Mapping not found: {MAPPING}", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with MAPPING.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    results = []
    counts: dict[str, int] = {}
    for idx, row in enumerate(rows, 1):
        result = row_result(row)
        results.append(result)
        status = result["card_status"]
        counts[status] = counts.get(status, 0) + 1
        print(f"[{idx}/{len(rows)}] {row.get('shobi_code','')} | fid={row.get('fragrantica_id','')} | {status}")
        if status in {"DOWNLOADED", "MISSING"}:
            time.sleep(DELAY)

    with MANIFEST.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(results)

    print("\nSUMMARY")
    print(f"total={len(results)}")
    for key in sorted(counts):
        print(f"{key}={counts[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
