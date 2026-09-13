"""
Scraper per il catalogo Shobi (leparfum.com.gr).

Selettori verificati il 13/09/2026 contro l'HTML reale del sito
(struttura PrestaShop, tema iqit). Se il sito cambia tema in futuro,
questi selettori andranno riverificati.

Output: shobi-master-v1-refresh.csv, con le stesse colonne concettuali
di shobi-master-v1.csv (da confrontare/riconciliare manualmente,
i nomi esatti delle colonne del file originale non sono noti qui).
"""
import re
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE_URL = "https://leparfum.com.gr/en/perfumes"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
}

MAX_RETRIES = 5


def fetch_page(url: str) -> requests.Response:
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise
            wait_time = min(2 ** attempt, 30)
            print(f"Tentativo {attempt + 1} fallito: {e}. Riprovo tra {wait_time}s...")
            time.sleep(wait_time)


def parse_products(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for article in soup.find_all("article", class_="product-miniature"):
        title_el = article.select_one("h2.product-title a")
        code_full = title_el.text.strip() if title_el else None

        ref_el = article.select_one(".product-reference a")
        reference = ref_el.text.strip() if ref_el else None

        cat_el = article.select_one(".product-category-name")
        category = cat_el.text.strip() if cat_el else None

        price_el = article.select_one(".product-price")
        price = price_el.get("content") if price_el else None

        desc_el = article.select_one(".product-description-short a")
        description = desc_el.text.strip() if desc_el else None

        inspired_by = None
        if description:
            m = re.search(r"Inspired by the fragrance notes of ([^.]+)\.", description)
            if m:
                inspired_by = m.group(1).strip()

        link_el = article.select_one("a.product-thumbnail")
        product_url = link_el.get("href") if link_el else None

        img_el = article.select_one("img.product-thumbnail-first")
        image_url = None
        if img_el:
            image_url = img_el.get("data-src") or img_el.get("src")

        product_id = article.get("data-id-product")

        products.append({
            "product_id": product_id,
            "code": code_full,
            "reference": reference,
            "category": category,
            "price_eur": price,
            "inspired_by": inspired_by,
            "description_short": description,
            "url": product_url,
            "image_url": image_url,
        })

    return products


def get_total_pages(html: str, fallback: int = 107) -> int:
    """
    Cerca il numero totale di pagine nella paginazione.
    Se non trovato (selettore non verificato per casi limite), usa il
    valore fallback letto manualmente sul sito il 13/09/2026 (107 pagine,
    24 prodotti/pagina). Se il catalogo cresce ulteriormente, aggiorna
    'fallback' controllando di nuovo l'ultimo numero di pagina sul sito.
    """
    soup = BeautifulSoup(html, "html.parser")
    page_links = soup.select(".pagination a, nav a")
    max_page = 1
    for link in page_links:
        text = link.text.strip()
        if text.isdigit():
            max_page = max(max_page, int(text))
    return max_page if max_page > 1 else fallback


def main():
    print(f"Scarico la prima pagina: {BASE_URL}")
    first_response = fetch_page(BASE_URL)
    first_page_products = parse_products(first_response.text)
    total_pages = get_total_pages(first_response.text)

    print(f"Trovati {len(first_page_products)} prodotti nella prima pagina.")
    print(f"Pagine totali rilevate/usate: {total_pages}")

    all_products = list(first_page_products)

    for page_num in range(2, total_pages + 1):
        url = f"{BASE_URL}?page={page_num}"
        print(f"Scarico pagina {page_num}/{total_pages}: {url}")
        response = fetch_page(url)
        page_products = parse_products(response.text)
        print(f"  -> {len(page_products)} prodotti")
        all_products.extend(page_products)
        time.sleep(1)  # gentile col server

    print(f"\nTotale prodotti raccolti: {len(all_products)}")

    df = pd.DataFrame(all_products)
    df.to_csv("shobi-master-v1-refresh.csv", index=False)
    print("Salvato in shobi-master-v1-refresh.csv")


if __name__ == "__main__":
    main()
