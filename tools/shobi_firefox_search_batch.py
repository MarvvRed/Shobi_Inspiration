#!/usr/bin/env python3
"""Search-only Fragrantica batch collector using a real local Firefox session.

This is intentionally NOT an identity resolver:
- reads Shobi Master rows;
- opens Fragrantica search pages only;
- never opens individual perfume pages;
- collects candidate URLs/IDs in search-result order;
- writes a separate intermediate CSV;
- never modifies shobi-fragrantica-mapping.csv.

Default test size: 10 rows not already present in the intermediate CSV.
"""
from __future__ import annotations

import configparser
import csv
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "shobi-master-v1.csv"
OUTPUT = ROOT / "data" / "fragrantica-search-candidates.csv"
DEFAULT_LIMIT = 10
DELAY_SECONDS = 7
MAX_CANDIDATES = 10

PERFUME_RE = re.compile(r"https?://(?:www\.)?fragrantica\.com/perfume/[^/]+/[^/]+-(\d+)\.html", re.I)
BROKEN_INSPIRED = {"the fragrance notes", "the fragrance notes of"}


def firefox_profile() -> Path:
    appdata = Path(os.environ["APPDATA"])
    base = appdata / "Mozilla" / "Firefox"
    ini = configparser.ConfigParser()
    ini.read(base / "profiles.ini", encoding="utf-8")
    choices: list[Path] = []
    for section in ini.sections():
        if not section.startswith("Profile"):
            continue
        raw = ini.get(section, "Path", fallback="")
        if not raw:
            continue
        p = Path(raw)
        if ini.getint(section, "IsRelative", fallback=1):
            p = base / p
        if p.exists():
            choices.append(p)
            if ini.getint(section, "Default", fallback=0) == 1:
                return p
    if not choices:
        raise RuntimeError("No Firefox profile found")
    return choices[0]


def copy_profile(src: Path, dst: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        skip = {"parent.lock", "lock", ".parentlock"}
        return {n for n in names if n in skip or n.lower().startswith("cache")}
    shutil.copytree(src, dst, ignore=ignore)


def query_for(row: dict[str, str]) -> str:
    inspired = (row.get("inspired_by") or "").strip()
    if inspired and inspired.lower() not in BROKEN_INSPIRED:
        return inspired
    name = (row.get("shobi_name") or "").strip()
    return name


def existing_ids() -> set[str]:
    if not OUTPUT.exists():
        return set()
    with OUTPUT.open("r", encoding="utf-8-sig", newline="") as f:
        return {r.get("prestashop_product_id", "") for r in csv.DictReader(f)}


def append_row(data: dict[str, str]) -> None:
    fields = [
        "prestashop_product_id", "shobi_code", "shobi_name", "inspired_by",
        "search_query", "search_status", "candidate_rank", "fragrantica_id",
        "candidate_url",
    ]
    new = not OUTPUT.exists()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow(data)
        f.flush()
        os.fsync(f.fileno())


def challenge(driver) -> bool:
    title = (driver.title or "").lower()
    body = (driver.page_source or "")[:100000].lower()
    markers = ("verify you are human", "checking your browser", "access denied", "ci siamo quasi", "captcha")
    return any(x in title or x in body for x in markers)


def collect_links(driver) -> list[tuple[str, str]]:
    from selenium.webdriver.common.by import By
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in driver.find_elements(By.CSS_SELECTOR, 'a[href*="/perfume/"]'):
        href = (a.get_attribute("href") or "").split("#", 1)[0].split("?", 1)[0]
        m = PERFUME_RE.fullmatch(href)
        if not m or href in seen:
            continue
        seen.add(href)
        links.append((m.group(1), href))
        if len(links) >= MAX_CANDIDATES:
            break
    return links


def main() -> int:
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
    except ImportError:
        print("SELENIUM_MISSING")
        print("Run: python -m pip install selenium")
        return 2

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LIMIT
    done = existing_ids()
    with MASTER.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("prestashop_product_id", "") not in done]
    rows = rows[:limit]
    if not rows:
        print("Nothing to search.")
        return 0

    profile = firefox_profile()
    print(f"Firefox profile found: {profile}")
    print(f"Rows to search: {len(rows)}")
    print(f"Output: {OUTPUT}")

    temp_root = Path(tempfile.mkdtemp(prefix="shobi-fragrantica-"))
    temp_profile = temp_root / "profile"
    print("Copying Firefox profile to temporary directory...")
    copy_profile(profile, temp_profile)

    options = Options()
    options.profile = str(temp_profile)
    driver = None
    try:
        print("Launching Firefox...")
        driver = webdriver.Firefox(options=options)
        for n, row in enumerate(rows, 1):
            pid = row.get("prestashop_product_id", "")
            query = query_for(row)
            print(f"\n[{n}/{len(rows)}] {pid} | {row.get('shobi_code','')} | {query}")
            if not query:
                append_row({
                    "prestashop_product_id": pid, "shobi_code": row.get("shobi_code", ""),
                    "shobi_name": row.get("shobi_name", ""), "inspired_by": row.get("inspired_by", ""),
                    "search_query": "", "search_status": "NO_QUERY", "candidate_rank": "",
                    "fragrantica_id": "", "candidate_url": "",
                })
                print("NO_QUERY")
                continue

            url = "https://www.fragrantica.com/search/?query=" + quote_plus(query)
            driver.get(url)
            time.sleep(5)
            if challenge(driver):
                print("CHALLENGE_DETECTED - stopping batch")
                return 3

            links = collect_links(driver)
            print(f"Candidates found: {len(links)}")
            if not links:
                append_row({
                    "prestashop_product_id": pid, "shobi_code": row.get("shobi_code", ""),
                    "shobi_name": row.get("shobi_name", ""), "inspired_by": row.get("inspired_by", ""),
                    "search_query": query, "search_status": "NO_RESULTS", "candidate_rank": "",
                    "fragrantica_id": "", "candidate_url": "",
                })
            else:
                for rank, (fid, href) in enumerate(links, 1):
                    print(f" {rank:2}. {fid} | {href}")
                    append_row({
                        "prestashop_product_id": pid, "shobi_code": row.get("shobi_code", ""),
                        "shobi_name": row.get("shobi_name", ""), "inspired_by": row.get("inspired_by", ""),
                        "search_query": query, "search_status": "FOUND", "candidate_rank": str(rank),
                        "fragrantica_id": fid, "candidate_url": href,
                    })
            if n < len(rows):
                print(f"Waiting {DELAY_SECONDS}s before next search...")
                time.sleep(DELAY_SECONDS)

        print("\nRESULT: BATCH_COMPLETE")
        return 0
    finally:
        if driver is not None:
            print("Closing Firefox...")
            driver.quit()
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
