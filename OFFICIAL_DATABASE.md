# Official Shobi perfume-only database

The current production database is built from the live 2,324-row Shobi source and excludes 67 entries whose original is non-wearable, a home/car/body/hair/laundry product, an accessory, or cannot be demonstrated as a genuine original perfume.

- `database/catalog/database_final_perfume_only.json` — full final database: **2,253** unique certified Shobi perfumes, including product IDs and Shobi URLs.
- `database/catalog/catalog_final_perfume_only.json` — lightweight public projection of the same **2,253** unique perfumes, loaded by the website.
- `database/catalog/database_complete.json` and `database/catalog/catalog_site.json` — canonical audit sources: **2,324** rows, retaining excluded records only for traceability.
- `database/catalog/catalog-scope-exclusions.json` — the 67 excluded Shobi codes.
- `database/catalog/final-perfume-catalog-certification.json` — machine-readable certification and source exceptions.

Every final record has a live Shobi product ID and URL. 2,254 have direct Fragrantica identity proof; the three remaining records have specific documented evidence of a real wearable perfume. Rebuild the final files with `tools/build_final_perfume_catalog.py`; do not add a record unless it satisfies the same scope rule.
