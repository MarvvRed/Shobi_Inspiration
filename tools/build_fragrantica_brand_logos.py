#!/usr/bin/env python3
"""Resumable collector for Fragrantica designer-directory images.

The directory endpoint may return HTTP 429 from hosted runners. This script
honors Retry-After, backs off conservatively, and stops the run cleanly when
the site keeps rate-limiting instead of hammering it with repeated requests.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys, time, unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError

ROOT = "https://www.fragrantica.com/designers/"
OUT_JSON = Path("database/brands/brands_logos.json")
OUT_IMAGES = Path("database/assets/brand-logos")
PAGE_RE = re.compile(r"/designers-(\d+)/?")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

class RateLimited(RuntimeError):
    pass

def slugify(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "brand"

def norm(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", value)

def absolute(base, value):
    if not value or value.startswith(("data:", "blob:")):
        return None
    return urljoin(base, value.strip())

def retry_delay(response, attempt):
    header = response.headers.get("Retry-After", "")
    if header:
        try:
            return max(1, min(900, int(header)))
        except ValueError:
            try:
                dt = parsedate_to_datetime(header)
                return max(1, min(900, int((dt - datetime.now(timezone.utc)).total_seconds())))
            except Exception:
                pass
    return min(900, 30 * (2 ** attempt))

def get(session, url, timeout=45):
    last = None
    for attempt in range(4):
        try:
            response = session.get(url, timeout=timeout)
            if response.status_code == 429:
                wait = retry_delay(response, attempt)
                if attempt == 3:
                    raise RateLimited(f"HTTP 429 from Fragrantica after retries: {url}")
                print(f"[RATE LIMIT] HTTP 429; respecting delay and retrying in {wait}s", file=sys.stderr, flush=True)
                time.sleep(wait)
                continue
            if response.status_code in (500, 502, 503, 504):
                last = RuntimeError(f"HTTP {response.status_code}: {url}")
                time.sleep(min(120, 10 * (2 ** attempt)))
                continue
            response.raise_for_status()
            return response
        except RateLimited:
            raise
        except requests.RequestException as exc:
            last = exc
            time.sleep(min(60, 5 * (2 ** attempt)))
    raise RuntimeError(str(last))

def discover_pages(session, max_pages=0):
    """Return Fragrantica's alphabetical designer pages.

    The /designers/ landing page is only a popular-brands showcase; the
    complete directory is split across /designers-1/ through /designers-11/.
    """
    pages = [f"https://www.fragrantica.com/designers-{n}/" for n in range(1, 12)]
    return pages[:max_pages] if max_pages else pages

def get_img_url(img, base):
    for key in ("data-src", "data-original", "data-lazy-src", "src"):
        value = absolute(base, img.get(key))
        if value:
            return value
    srcset = img.get("srcset") or img.get("data-srcset")
    return absolute(base, srcset.split(",")[-1].strip().split()[0]) if srcset else None

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
            im.seek(0); im.load()
            width, height = im.size
            if width < 32 or height < 16:
                return False, "IMAGE_TOO_SMALL", {"width": width, "height": height}
            im.thumbnail((640, 640), Image.Resampling.LANCZOS)
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if "transparency" in im.info else "RGB")
            target.parent.mkdir(parents=True, exist_ok=True)
            im.save(target, "WEBP", quality=88, method=6)
        return True, None, {"width": width, "height": height, "stored_format": "webp"}
    except RateLimited:
        raise
    except (requests.RequestException, RuntimeError) as exc:
        return False, "DOWNLOAD_FAILED: " + str(exc)[:220], {}
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return False, "INVALID_IMAGE: " + str(exc)[:180], {}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-pages", type=int, default=0)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--delay", type=float, default=3.0)
    p.add_argument("--retry-failed", action="store_true")
    args = p.parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
    old = read_old()
    try:
        pages = discover_pages(session, args.max_pages)
    except RateLimited as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        print("[INFO] No requests will be made until Fragrantica permits access again.", file=sys.stderr)
        return 3
    print(f"[INFO] Discovered {len(pages)} directory pages", flush=True)
    found = {}
    for i, page_url in enumerate(pages, 1):
        print(f"[PAGE {i}/{len(pages)}] {page_url}", flush=True)
        try:
            soup = BeautifulSoup(get(session, page_url).text, "html.parser")
        except RateLimited as exc:
            print(f"[BLOCKED] {exc}", file=sys.stderr)
            break
        except Exception as exc:
            print(f"[WARN] Page failed: {exc}", file=sys.stderr)
            continue
        count = 0
        image_count = len(soup.find_all("img"))
        designer_links = 0
        for a in soup.find_all("a", href=True):
            page_href = absolute(page_url, a.get("href"))
            path = urlparse(page_href or "").path
            if not re.search(r"/designers/[^/]+\.html$", path, re.I):
                continue
            designer_links += 1
            img = a.find("img")
            if img is None:
                continue
            name = get_brand_name(img, a)
            src = get_img_url(img, page_url)
            if not name or not src:
                continue
            key = norm(name)
            if not key:
                continue
            record = {"brand_id": slugify(name), "brand_name": name, "source_page_url": page_href,
                      "source_image_url": src, "source_directory_url": page_url,
                      "asset_type": "fragrantica_designer_directory_image"}
            if key in found and found[key]["source_page_url"] != page_href:
                found[key].setdefault("alternate_source_pages", []).append(page_href)
                continue
            found[key] = record
            count += 1
        title = soup.title.get_text(" ", strip=True) if soup.title else "(no title)"
        print(f"[DIAGNOSTIC] title={title!r} images={image_count} designer_links={designer_links}", flush=True)
        print(f"[INFO] Candidate entries: {count}", flush=True)
        time.sleep(3.0)
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
        if item.get("image_status") == "downloaded" and target.exists():
            skipped += 1; continue
        if item.get("image_status") == "failed" and not args.retry_failed:
            skipped += 1; continue
        try:
            ok, error, meta = save_image(session, item["source_image_url"], target)
        except RateLimited as exc:
            item["image_status"] = "failed"; item["image_error"] = "RATE_LIMITED: " + str(exc)[:180]
            failed += 1
            print(f"[BLOCKED] {exc}; stopping further downloads", file=sys.stderr)
            break
        item["image_status"] = "downloaded" if ok else "failed"
        item["image_error"] = error; item["image_metadata"] = meta
        item["local_path"] = target.as_posix() if ok else None
        if ok:
            item["image_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest(); downloaded += 1
        else:
            failed += 1
            if target.exists(): target.unlink()
        if i % 25 == 0:
            print(f"[PROGRESS] {i}/{len(candidates)} downloaded={downloaded} skipped={skipped} failed={failed}", flush=True)
        time.sleep(max(3.0, args.delay))
    output = {"schema_version": 1, "source": ROOT, "generated_at": datetime.now(timezone.utc).isoformat(),
              "directory_pages_discovered": len(pages), "brand_count_in_manifest": len(candidates),
              "downloaded_count": sum(1 for x in candidates if x.get("image_status") == "downloaded" and x.get("local_path") and Path(x["local_path"]).exists()),
              "failed_count": sum(1 for x in candidates if x.get("image_status") == "failed"), "brands": candidates}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[DONE] {OUT_JSON}: brands={len(candidates)} downloaded={downloaded} skipped={skipped} failed={failed}", flush=True)
    return 0 if candidates else 2

if __name__ == "__main__":
    raise SystemExit(main())
