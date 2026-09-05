# Legacy local Fragrantica scraper

Historical reconstruction of the old local scraper environment used before the current repository structure.

## Known local path

`C:\fragrance_scraper`

## Known files

- `fragrantica_url_scraper.py`
- `perfume_urls.txt`

## Known run state

- Existing URL corpus loaded: about **21,158 Fragrantica perfume URLs**.
- Scraper configuration used limits around `max-brands 120` and `max-perfumes 22000`.
- The scraper iterated Fragrantica designer pages and extracted perfume/designer links.
- The URL corpus was intended to act as a local search/index source instead of querying Fragrantica from scratch for every Shobi product.

## Important

On 2026-09-05, the original `perfume_urls.txt` was recovered from `C:\fragrance_scraper` and copied unchanged into the repository, with 55,964 lines. See [snapshot details](original-local-scraper/README.md). The original `fragrantica_url_scraper.py` has not been imported. The recovery destination is:

`fragrantica-scraper-archive/legacy/original-local-scraper/`

Do not synthesize a replacement URL list and label it as the original corpus.

## Related historical Fragrantica work

The wider project also used targeted Fragrantica indexes, Firefox/Selenium search collection, direct Fragrantica search, Social Card capture, Main Notes capture, note-icon mapping and Fragrantica ID validation. The reusable pieces that remain in the current repository are copied into the parent archive folder.
