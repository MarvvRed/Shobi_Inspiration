#!/usr/bin/env python3
"""Small local-only test: open Fragrantica through a real Firefox profile copy.

This does not modify the user's Firefox profile. It copies the selected profile
to a temporary directory, launches visible Firefox through Selenium, opens one
Fragrantica search, and prints any perfume links found.
"""
from __future__ import annotations

import configparser
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote_plus


def find_firefox_profile() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA not set")
    root = Path(appdata) / "Mozilla" / "Firefox"
    ini = root / "profiles.ini"
    if not ini.exists():
        raise RuntimeError(f"Firefox profiles.ini not found: {ini}")

    cfg = configparser.RawConfigParser()
    cfg.read(ini, encoding="utf-8")
    candidates: list[tuple[int, Path]] = []
    for section in cfg.sections():
        if not section.startswith("Profile"):
            continue
        p = cfg.get(section, "Path", fallback="").strip()
        if not p:
            continue
        is_relative = cfg.getboolean(section, "IsRelative", fallback=True)
        path = (root / p) if is_relative else Path(p)
        if not path.exists():
            continue
        default = cfg.getint(section, "Default", fallback=0)
        score = 10 if default else 0
        name = cfg.get(section, "Name", fallback="").lower()
        if "default-release" in name or "default-release" in path.name.lower():
            score += 5
        candidates.append((score, path))
    if not candidates:
        raise RuntimeError("No usable Firefox profile found")
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def main() -> int:
    term = " ".join(sys.argv[1:]).strip() or "Cheirosa 40 Sol de Janeiro"
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
    except ImportError:
        print("SELENIUM_MISSING")
        return 2

    source = find_firefox_profile()
    print(f"Firefox profile found: {source}")

    with tempfile.TemporaryDirectory(prefix="shobi_firefox_") as td:
        profile_copy = Path(td) / "profile"
        print("Copying Firefox profile to a temporary folder...")
        shutil.copytree(
            source,
            profile_copy,
            ignore=shutil.ignore_patterns("parent.lock", "lock", ".parentlock", "cache2", "startupCache"),
        )

        options = Options()
        options.profile = str(profile_copy)
        options.add_argument("-foreground")

        print("Launching visible Firefox...")
        driver = webdriver.Firefox(options=options)
        try:
            url = "https://www.fragrantica.com/search/?query=" + quote_plus(term)
            print(f"Opening: {url}")
            driver.get(url)
            time.sleep(8)
            print(f"Title: {driver.title}")
            print(f"Current URL: {driver.current_url}")

            html = driver.page_source
            links = []
            for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I):
                if re.search(r"/perfume/[^/]+/[^/]+-\d+\.html", href, flags=re.I):
                    if href.startswith("/"):
                        href = "https://www.fragrantica.com" + href
                    if href not in links:
                        links.append(href)

            print(f"Perfume links found: {len(links)}")
            for link in links[:10]:
                print(link)

            lowered = (driver.title + "\n" + html[:20000]).lower()
            if "403 forbidden" in lowered or "access denied" in lowered:
                print("RESULT: BLOCKED")
                return 3
            if links:
                print("RESULT: OK")
                return 0
            print("RESULT: PAGE_OPENED_BUT_NO_PERFUME_LINKS")
            return 4
        finally:
            print("Closing test Firefox...")
            driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
