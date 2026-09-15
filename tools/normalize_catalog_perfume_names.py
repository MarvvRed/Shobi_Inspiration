#!/usr/bin/env python3
"""Normalize catalog perfume names without heuristically stripping brand text.

The displayed perfume name comes from the explicit Fragrantica mapping when
available. For canonical Fragrantica URLs, the URL slug is an additional safe
fallback because the brand and perfume name are separate URL path components.
This deliberately never does name.replace(brand, ...), which can corrupt valid
perfume names that legitimately contain brand words.
"""

import csv
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "database/source/shobi-fragrantica-mapping.csv"
FULL_DB = ROOT / "database/catalog/database_complete.json"
SITE_DB = ROOT / "database/catalog/catalog_site.json"


def canonical_name_from_url(url):
    match = re.search(r"/perfume/[^/]+/(.+?)-(\d+)\.html(?:$|[?#])", str(url or ""), re.I)
    if not match:
        return ""
    return unquote(match.group(1)).replace("-", " ").strip()


def load_mapping():
    with MAPPING.open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return {str(r.get("prestashop_product_id") or "").strip(): r for r in rows}


def normalize(rows, mapping):
    changed = 0
    unresolved = 0
    for row in rows:
        pid = str(row.get("prestashopProductId") or "").strip()
        source = mapping.get(pid, {})
        mapped_name = str(source.get("original_perfume") or "").strip()
        canonical_url_name = canonical_name_from_url(
            source.get("fragrantica_url") or row.get("fragranticaUrl")
        )
        # Explicit mapped identity is primary; canonical URL name is the safe fallback.
        canonical_name = mapped_name or canonical_url_name
        if canonical_name:
            if row.get("inspiredBy") != canonical_name:
                row["inspiredBy"] = canonical_name
                changed += 1
        else:
            unresolved += 1
    return changed, unresolved


def main():
    mapping = load_mapping()
    totals = []
    for path in (FULL_DB, SITE_DB):
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        changed, unresolved = normalize(rows, mapping)
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        totals.append((path.name, len(rows), changed, unresolved))
    for name, count, changed, unresolved in totals:
        print(f"{name}: rows={count} names_changed={changed} unresolved={unresolved}")


if __name__ == "__main__":
    main()
