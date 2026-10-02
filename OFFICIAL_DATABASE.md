# Official Shobi perfume-only database

The current production **public** database contains **2,249** unique Shobi perfumes. It is generated from **2,274** clean operational Shobi records, after collapsing 25 independently certified same-original duplicate listings. It excludes 67 entries whose original is non-wearable, a home/car/body/hair/laundry product, an accessory, or cannot be demonstrated as a genuine original perfume.

- `database/catalog/database_final_perfume_only.json` — full final public database: **2,249** unique certified Shobi perfumes, including product IDs and Shobi URLs.
- `database/catalog/catalog_final_perfume_only.json` — lightweight public projection of the same **2,249** unique perfumes, loaded by the website.
- `database/catalog/database_complete.json` and `database/catalog/catalog_site.json` — canonical operational catalog: **2,274** clean in-scope Shobi records before the public same-original duplicate collapse.
- `database/catalog/catalog-scope-exclusions.json` — the 67 excluded Shobi codes.
- `database/catalog/final-perfume-catalog-certification.json` — machine-readable certification, duplicate-collapse evidence, and source exceptions.

Every final record has a live Shobi product ID and URL. **2,246** have direct Fragrantica identity proof; the three remaining records have specific documented evidence of a real wearable perfume. Rebuild the final files with `tools/build_final_perfume_catalog.py`; do not add a record unless it satisfies the same scope rule.
