#!/usr/bin/env python3
"""Resumable collector for Fragrantica designer-directory images."""
from __future__ import annotations
import argparse, hashlib, json, re, sys, time, unicodedata
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError

ROOT = "https://www.fragrantica.com/designers/"
OUT_JSON = Path("database/brands/brands_logos.json")
OUT_IMAGES = Path("database/assets/brand-logos")
UA = "Mozilla/5.0 (compatible; ShobiBrandArchive/1.0; +https://github.com/MarvvRed/Shobi_Inspiration)"
PAGE_RE = re.compile(r"/designers-(\d+)/?")

def slugify(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "brand"

def norm(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", value)

def absolute(base, value):
    if not value:
        return None
    value = value.strip()
    if value.startswith(("data:", "blob:")):
        return None
    return urljoin(base, value)

def get(session, url, timeout=40):
    last = None
    for attempt in range(5):
        try:
            response = session.get(url, timeout=timeout)
            if response.status_code in (429, 500, 502, 503, 504):
                last = RuntimeError(f"HTTP {response.status_code}: {url}")
                time.sleep(min(30, 2 ** attempt * 2))
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last = exc
            time.sleep(min(20, 2 ** attempt))
    raise RuntimeError(str(last))

def discover_pages(session):
    soup = BeautifulSoup(get(session, ROOT).text, "html.parser")
    queue = [ROOT]
    for a in soup.find_all("a", href=True):
        href = absolute(ROOT, a["href"])
        if href and PAGE_RE.search(urlparse(href).path):
            queue.append(href.split("#")[0])
    visited = set()
    while queue and len(visited) < 60:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            page = BeautifulSoup(get(session, url).text, "html.parser")
        except Exception as exc:
            print(f"[WARN] Pagination {url}: {exc}", file=sys.stderr)
            continue
        for a in page.find_all("a", href=True):
            href = absolute(url, a["href"])
            if href and PAGE_RE.search(urlparse(href).path):
                href = href.split("#")[0]
                if href not in visited and href not in queue:
                    queue.append(href)
        time.sleep(0.35)
    return sorted(visited, key=lambda u: (u.rstrip("/") != ROOT.rstrip("/"), u))

def get_img_url(img, base):
    for key in ("data-src", "data-original", "data-lazy-src", "src"):
        value = absolute(base, img.get(key))
        if value:
            return value
    srcset = img.get("srcset") or img.get("data-srcset")
    if srcset:
        return absolute(base, srcset.split(",")[-1].strip().split()[0])
    return None

def get_brand_name(img, anchor):
    values = []
    if anchor:
        values += [anchor.get("title"), anchor.get("aria-label"), anchor.get_text(" ", strip=True)]
    values += [img.get("alt"), img.get("title")]
    for raw in values:
        if not raw:
            continue
        name = re.sub(r"^\s*Image:\s*", "", str(raw), flags=re.I).strip()
        name = re.sub(r"\s+\d+\s*$", "", name).strip(" -|:")
        if name and len(name) < 120 and norm(name) not in {"image", "logo", "fragrantica"}:
            return name
    return None

def read_old():
    try:
        data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        return {x["source_page_url"]: x for x in data.get("brands", []) if x.get("source_page_url")}
    except Exception:
        return {}

def save_image(session, url, target):
    try:
        response = get(session, url, timeout=50)
        if len(response.content) > 12 * 1024 * 1024:
            return False, "IMAGE_TOO_LARGE", {}
        with Image.open(BytesIO(response.content)) as im:
            im.verify()
        with Image.open(BytesIO(response.content)) as im:
            im.seek(0)
            im.load()
            width, height = im.size
            if width < 32 or height < 16:
                return False, "IMAGE_TOO_SMALL", {"width": width, "height": height}
            im.thumbnail((640, 640), Image.Resampling.LANCZOS)
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if "transparency" in im.info else "RGB")
            target.parent.mkdir(parents=True, exist_ok=True)
            im.save(target, "WEBP", quality=88, method=6)
        return True, None, {"width": width, "height": height, "stored_format": "webp"}
    except (requests.RequestException, RuntimeError) as exc:
        return False, "DOWNLOAD_FAILED: " + str(exc)[:220], {}
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return False, "INVALID_IMAGE: " + str(exc)[:180], {}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-pages", type=int, default=0)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--delay", type=float, default=0.25)
    p.add_argument("--retry-failed", action="store_true")
    args = p.parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
    old = read_old()
    pages = discover_pages(session)
    if args.max_pages:
        pages = pages[:args.max_pages]
    print(f"[INFO] Discovered {len(pages)} directory pages")
    found = {}
    for i, page_url in enumerate(pages, 1):
        print(f"[PAGE {i}/{len(pages)}] {page_url}")
        try:
            soup = BeautifulSoup(get(session, page_url).text, "html.parser")
        except Exception as exc:
            print(f"[WARN] Page failed: {exc}", file=sys.stderr)
            continue
        count = 0
        for img in soup.find_all("img"):
            a = img.find_parent("a", href=True)
            name, src = get_brand_name(img, a), get_img_url(img, page_url)
            if not name or not src:
                continue
            page_href = absolute(page_url, a.get("href")) if a else None
            if not page_href or "designer" not in urlparse(page_href).path.lower():
                continue
            key = norm(name)
            if not key:
                continue
            record = {
                "brand_id": slugify(name),
                "brand_name": name,
                "source_page_url": page_href,
                "source_image_url": src,
                "source_directory_url": page_url,
                "asset_type": "fragrantica_designer_directory_image",
            }
            if key in found and found[key]["source_page_url"] != page_href:
                found[key].setdefault("alternate_source_pages", []).append(page_href)
                continue
            found[key] = record
            count += 1
        print(f"[INFO] Candidate entries: {count}")
        time.sleep(0.4)
    merged = dict(old)
    for item in found.values():
        merged[item["source_page_url"]] = {**merged.get(item["source_page_url"], {}), **item}
    candidates = sorted(merged.values(), key=lambda x: (norm(x.get("brand_name", "")), x.get("source_page_url", "")))
    if args.limit:
        candidates = candidates[:args.limit]
    OUT_IMAGES.mkdir(parents=True, exist_ok=True)
    downloaded = skipped = failed = 0
    for i, item in enumerate(candidates, 1):
        digest = hashlib.sha1(item["source_page_url"].encode()).hexdigest()[:8]
        target = OUT_IMAGES / f"{slugify(item.get('brand_name', 'brand'))}-{digest}.webp"
        ok_existing = item.get("image_status") == "downloaded" and target.exists()
        if ok_existing and not args.retry_failed:
            skipped += 1
            continue
        ok, error, meta = save_image(session, item["source_image_url"], target)
        item["image_status"] = "downloaded" if ok else "failed"
        item["image_error"] = error
        item["image_metadata"] = meta
        item["local_path"] = target.as_posix() if ok else None
        if ok:
            item["image_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            downloaded += 1
        else:
            failed += 1
            if target.exists():
                target.unlink()
        if i % 100 == 0:
            print(f"[PROGRESS] {i}/{len(candidates)} downloaded={downloaded} skipped={skipped} failed={failed}")
        time.sleep(max(0.0, args.delay))
    output = {
        "schema_version": 1,
        "source": ROOT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "directory_pages_discovered": len(pages),
        "brand_count_in_manifest": len(candidates),
        "downloaded_count": sum(1 for x in candidates if x.get("image_status") == "downloaded" and x.get("local_path") and Path(x["local_path"]).exists()),
        "failed_count": sum(1 for x in candidates if x.get("image_status") == "failed"),
        "brands": candidates,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[DONE] {OUT_JSON}: brands={len(candidates)} downloaded={downloaded} skipped={skipped} failed={failed}")
    return 0 if candidates else 2

if __name__ == "__main__":
    raise SystemExit(main())
