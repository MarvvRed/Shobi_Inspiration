#!/usr/bin/env python3
"""Build the official Shobi perfume-only best-seller ranking.

The official Best sales page includes more than wearable perfumes.  This
generator deliberately does no name/category guessing: it retains a product
only when its PrestaShop product id occurs in the already certified,
perfume-only public database.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


OFFICIAL_URL = "https://leparfum.com.gr/en/best-sales"
USER_AGENT = (
    "Mozilla/5.0 (compatible; ShobiInspirationCatalog/1.0; "
    "+https://marvvred.github.io/Shobi_Inspiration/)"
)


def fetch(session: requests.Session, url: str) -> str:
    last_error: requests.RequestException | None = None
    for attempt in range(5):
        try:
            response = session.get(url, timeout=45)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 4:
                break
            time.sleep(min(2 ** attempt, 20))
    assert last_error is not None
    raise last_error


def page_count(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    pages = [1]
    for link in soup.select(".pagination a[href], nav.pagination a[href]"):
        href = link.get("href", "")
        query = parse_qs(urlparse(href).query)
        for value in query.get("page", []):
            if value.isdigit():
                pages.append(int(value))
        text = link.get_text(" ", strip=True)
        if text.isdigit():
            pages.append(int(text))
    return max(pages)


def products(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[dict[str, str]] = []
    for article in soup.select("article.product-miniature"):
        product_id = str(article.get("data-id-product") or "").strip()
        if not product_id:
            continue
        title = article.select_one("h2.product-title a")
        found.append({
            "prestashopProductId": product_id,
            "officialTitle": title.get_text(" ", strip=True) if title else "",
        })
    return found


def certified_products(path: Path) -> dict[str, dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("The certified database must be a JSON array.")
    indexed: dict[str, dict] = {}
    for row in rows:
        product_id = str(row.get("prestashopProductId") or "").strip()
        code = str(row.get("code") or "").strip()
        if not product_id or not code:
            raise ValueError("Certified database contains a row without product id or code.")
        if product_id in indexed:
            raise ValueError(f"Duplicate certified PrestaShop product id: {product_id}")
        indexed[product_id] = row
    if not indexed:
        raise ValueError("Certified database is empty.")
    return indexed


def build(database: Path, output: Path, delay: float) -> None:
    eligible = certified_products(database)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})

    first_html = fetch(session, OFFICIAL_URL)
    total_pages = page_count(first_html)
    if total_pages < 1:
        raise RuntimeError("Could not determine official Best sales pagination.")

    seen_ids: set[str] = set()
    ranking: list[dict] = []
    official_position = 0
    for page in range(1, total_pages + 1):
        html = first_html if page == 1 else fetch(session, f"{OFFICIAL_URL}?page={page}")
        page_products = products(html)
        if not page_products:
            raise RuntimeError(f"Official Best sales page {page} had no product cards.")
        for product in page_products:
            product_id = product["prestashopProductId"]
            if product_id in seen_ids:
                continue
            seen_ids.add(product_id)
            official_position += 1
            certified = eligible.get(product_id)
            if not certified:
                continue
            ranking.append({
                "perfumeSalesRank": len(ranking) + 1,
                "officialSalesRank": official_position,
                "code": certified["code"],
                "prestashopProductId": product_id,
                "reference": certified.get("reference"),
                "brand": certified.get("brand"),
                "inspiredBy": certified.get("inspiredBy"),
                "shobiUrl": certified.get("shobiUrl"),
                "officialTitle": product["officialTitle"],
            })
        print(f"Best sales page {page}/{total_pages}: {len(page_products)} products", flush=True)
        if page < total_pages and delay:
            time.sleep(delay)

    if not ranking:
        raise RuntimeError("No official Best sales product matched the certified perfume database.")

    payload = {
        "schema": "shobi-official-bestsellers/v1",
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": {
            "url": OFFICIAL_URL,
            "sort": "Sales, highest to lowest",
            "method": "Exact PrestaShop product-id intersection with the certified wearable-perfume catalog",
        },
        "summary": {
            "officialBestSalesProducts": official_position,
            "eligibleCertifiedWearablePerfumes": len(eligible),
            "rankedCertifiedWearablePerfumes": len(ranking),
        },
        "ranking": ranking,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(ranking)} certified wearable perfumes to {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("database/catalog/database_final_perfume_only.json"))
    parser.add_argument("--output", type=Path, default=Path("database/catalog/shobi-bestsellers.json"))
    parser.add_argument("--delay", type=float, default=0.2, help="Seconds between official page requests")
    args = parser.parse_args()
    try:
        build(args.database, args.output, args.delay)
    except (OSError, ValueError, requests.RequestException, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
