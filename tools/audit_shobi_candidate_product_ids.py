"""Recover real PrestaShop IDs for four pending Shobi candidates; never edit catalog files."""
import json, re, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

AUDIT = Path('database/audits/pending-shobi-additions-2026-10-19.json')
OUT = Path('database/audits/recovered-shobi-product-ids-2026-10-19.json')
BASE = 'https://leparfum.com.gr/en/perfumes'
CODES = {'2879-KAY', '2878-MAN', '2877-VIC', '2854-RIH'}
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; ShobiCatalogAudit/1.0)'}

def main():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    found = {}
    errors = []
    s = requests.Session(); s.headers.update(HEADERS)
    # Browse paginated official listing and capture data-id-product, URL, reference and image.
    first = s.get(BASE, timeout=30); first.raise_for_status()
    soup = BeautifulSoup(first.text, 'html.parser')
    pages = [int(a.get_text(strip=True)) for a in soup.select('.pagination a, nav a') if a.get_text(strip=True).isdigit()]
    total = max(pages, default=107)
    for n in range(1, total + 1):
        url = BASE if n == 1 else f'{BASE}?page={n}'
        try:
            res = first if n == 1 else s.get(url, timeout=30)
            res.raise_for_status()
            page = BeautifulSoup(res.text, 'html.parser')
            for art in page.select('article.product-miniature'):
                text = art.get_text(' ', strip=True)
                title = art.select_one('h2.product-title a')
                ref = art.select_one('.product-reference a')
                code = (title.get_text(' ', strip=True) if title else '')
                reference = ref.get_text(' ', strip=True) if ref else ''
                normalized = (code + ' ' + reference + ' ' + text[:180]).upper()
                match = next((c for c in CODES if re.search(r'(?<![A-Z0-9])' + re.escape(c) + r'(?![A-Z0-9])', normalized)), None)
                if not match: continue
                image = art.select_one('img.product-thumbnail-first')
                link = art.select_one('a.product-thumbnail') or (title if title else None)
                found[match] = {
                    'code': match,
                    'prestashop_product_id': art.get('data-id-product'),
                    'reference': reference or None,
                    'title': code or None,
                    'product_url': link.get('href') if link else None,
                    'image_url': (image.get('data-src') or image.get('src')) if image else None,
                    'listing_page': url,
                    'evidence': 'official listing article.product-miniature[data-id-product]',
                }
            if len(found) == len(CODES): break
            time.sleep(0.25)
        except Exception as exc:
            errors.append({'page': n, 'error': str(exc)})
    result = {
      'audit_date': '2026-10-19',
      'source': BASE,
      'method': 'Read data-id-product directly from official PrestaShop product-miniature HTML; not inferred from image URL numbers.',
      'found_count': len(found),
      'expected_count': len(CODES),
      'candidates': [found[c] if c in found else {'code': c, 'prestashop_product_id': None, 'status': 'NOT_FOUND_IN_LISTING'} for c in sorted(CODES)],
      'errors': errors,
      'catalog_changed': False,
      'next_step': 'Verify product ID against social-card manifest and inspect each social card before changing any certified catalog.'
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if len(found) != len(CODES) or any(not found[c].get('prestashop_product_id') for c in found):
      raise SystemExit(2)
if __name__ == '__main__': main()
