from __future__ import annotations

import csv
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "fragrantica-scraper-archive" / "corpus-match" / "shobi-fragrantica-corpus-match.csv"
OUT_DIR = ROOT / "perfume-images"
MANIFEST = OUT_DIR / "manifest.csv"
BASE = "https://fimgs.net/mdimg/perfume-thumbs/dark-375x500.{fid}.avif"
DELAY = float(os.environ.get("PERFUME_IMAGE_DELAY", "0.08"))
TIMEOUT = float(os.environ.get("PERFUME_IMAGE_TIMEOUT", "20"))
RETRIES = int(os.environ.get("PERFUME_IMAGE_RETRIES", "3"))


def valid_avif(data: bytes, content_type: str) -> bool:
    if len(data) < 1000:
        return False
    head = data[:32]
    return (b"ftypavif" in head or b"ftypavis" in head) or "image/avif" in content_type.lower()


def fetch(url: str) -> tuple[str, bytes | None, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ShobiImageArchive/1.0)",
        "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
        "Referer": "https://www.fragrantica.com/",
    }
    for attempt in range(1, RETRIES + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                data = response.read()
                ctype = response.headers.get("Content-Type", "")
                if valid_avif(data, ctype):
                    return "DOWNLOADED", data, ctype
                return "INVALID", None, ctype
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return "MISSING", None, f"HTTP {exc.code}"
            last = f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        if attempt < RETRIES:
            time.sleep(0.8 * attempt)
    return "ERROR", None, last


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    with CORPUS.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            fid = (row.get("fragrantica_id") or "").strip()
            if (row.get("status") or "").strip() != "FOUND" or not fid.isdigit():
                continue
            rows.append(row)

    by_id: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_id.setdefault(row["fragrantica_id"].strip(), []).append(row)

    manifest_rows: list[dict[str, str]] = []
    counts = {"EXISTS": 0, "DOWNLOADED": 0, "MISSING": 0, "INVALID": 0, "ERROR": 0}

    total = len(by_id)
    for index, fid in enumerate(sorted(by_id, key=int), 1):
        target = OUT_DIR / f"{fid}.avif"
        url = BASE.format(fid=fid)

        if target.exists() and target.stat().st_size >= 1000:
            status, detail = "EXISTS", ""
        else:
            status, data, detail = fetch(url)
            if data is not None:
                target.write_bytes(data)
            time.sleep(DELAY)

        counts[status] = counts.get(status, 0) + 1
        linked = by_id[fid]
        for row in linked:
            manifest_rows.append(
                {
                    "prestashop_product_id": row.get("prestashop_product_id", ""),
                    "shobi_code": row.get("shobi_code", ""),
                    "inspired_by": row.get("inspired_by", ""),
                    "fragrantica_id": fid,
                    "fragrantica_url": row.get("fragrantica_url", ""),
                    "image_url": url,
                    "local_path": f"perfume-images/{fid}.avif" if status in {"EXISTS", "DOWNLOADED"} else "",
                    "status": status,
                    "detail": detail,
                }
            )

        if index % 100 == 0 or index == total:
            print(f"progress={index}/{total} counts={counts}", flush=True)

    fields = [
        "prestashop_product_id",
        "shobi_code",
        "inspired_by",
        "fragrantica_id",
        "fragrantica_url",
        "image_url",
        "local_path",
        "status",
        "detail",
    ]
    with MANIFEST.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest_rows)

    ok = counts.get("EXISTS", 0) + counts.get("DOWNLOADED", 0)
    print(
        f"source_rows={len(rows)} unique_ids={total} images_available={ok} "
        f"missing={counts.get('MISSING', 0)} invalid={counts.get('INVALID', 0)} errors={counts.get('ERROR', 0)}"
    )


if __name__ == "__main__":
    main()
