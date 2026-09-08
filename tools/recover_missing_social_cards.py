#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database_complete.json"
OUT_DIR = ROOT / "fragrantica-scraper-archive" / "social-cards" / "images"
REPORT = ROOT / "missing-social-card-recovery-report.json"
BASE = "https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{id}.jpeg"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
TIMEOUT = 30
RETRIES = 3
DELAY = float(os.environ.get("SOCIAL_CARD_DELAY", "0.35"))


def flatten_records(data):
    if isinstance(data, list) and data and isinstance(data[0], dict) and isinstance(data[0].get("perfumes"), list):
        return [p for block in data for p in block.get("perfumes", [])]
    return data if isinstance(data, list) else []


def official(p):
    status = str(p.get("fragranticaStatus") or p.get("fragrantica_status") or "").upper()
    return not status.startswith("RESOLVED_NO_FORCE")


def fid_of(p):
    for key in ("fragranticaId", "fragrantica_id", "fragranticaID"):
        value = p.get(key)
        if value not in (None, ""):
            try:
                return int(str(value))
            except ValueError:
                pass
    for key in ("fragranticaUrl", "fragrantica_url", "fragranticaLocalUrl"):
        m = re.search(r"-(\d+)\.html", str(p.get(key) or ""))
        if m:
            return int(m.group(1))
    return None


def safe(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    return value.strip("._") or "unknown"


def is_jpeg(data: bytes) -> bool:
    return len(data) > 16 and data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")


def archived_ids():
    ids = set()
    if not OUT_DIR.exists():
        return ids
    for p in OUT_DIR.iterdir():
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        m = re.search(r"_(\d+)$", p.stem)
        if m:
            ids.add(int(m.group(1)))
    return ids


def fetch(url):
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


def main():
    data = json.loads(DB.read_text(encoding="utf-8"))
    records = [p for p in flatten_records(data) if official(p) and fid_of(p)]
    before = archived_ids()
    missing = [p for p in records if fid_of(p) not in before]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for i, p in enumerate(missing, 1):
        fid = fid_of(p)
        code = str(p.get("code") or p.get("id") or p.get("shobiCode") or "").strip()
        prestashop = str(p.get("prestashopProductId") or p.get("prestashop_product_id") or "").strip()
        url = BASE.format(id=fid)
        filename = f"{safe(prestashop)}_{safe(code)}_{fid}.jpeg"
        path = OUT_DIR / filename
        payload, error = fetch(url)
        if payload is not None:
            path.write_bytes(payload)
            status = "RECOVERED"
            size = len(payload)
            sha = hashlib.sha256(payload).hexdigest()
        else:
            status = "MISSING"
            size = 0
            sha = ""
        row = {
            "code": code,
            "prestashopProductId": prestashop,
            "fragranticaId": fid,
            "url": url,
            "status": status,
            "localPath": path.relative_to(ROOT).as_posix() if status == "RECOVERED" else "",
            "bytes": size,
            "sha256": sha,
            "error": error,
        }
        results.append(row)
        print(f"[{i}/{len(missing)}] {code} | {fid} | {status} {error}")
        time.sleep(DELAY)

    after = archived_ids()
    recovered = sum(r["status"] == "RECOVERED" for r in results)
    report = {
        "rule": "Targeted direct retry of exact official Fragrantica social-card IDs missing from local archive.",
        "officialWithFragranticaId": len(records),
        "archiveExactIdsBefore": len(before & {fid_of(p) for p in records}),
        "missingBefore": len(missing),
        "recovered": recovered,
        "stillMissing": len(missing) - recovered,
        "archiveExactIdsAfter": len(after & {fid_of(p) for p in records}),
        "results": results,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
