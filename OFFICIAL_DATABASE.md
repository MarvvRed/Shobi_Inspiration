# Official Shobi perfume-only database

The current production database is built from the live 2,324-row Shobi source and excludes 67 entries whose original is non-wearable, a home/car/body/hair/laundry product, an accessory, or cannot be demonstrated as a genuine original perfume.

- `database_final_perfume_only.json` — full final database: **2,257** certified Shobi perfume records, including product IDs and Shobi URLs.
- `catalog_final_perfume_only.json` — lightweight public projection of the same **2,257** records, loaded by the website.
- `database_complete.json` and `catalog_site.json` — canonical audit sources: **2,324** rows, retaining excluded records only for traceability.
- `catalog-scope-exclusions.json` — the 67 excluded Shobi codes.
- `final-perfume-catalog-certification.json` — machine-readable certification and source exceptions.

Every final record has a live Shobi product ID and URL. 2,254 have direct Fragrantica identity proof; the three remaining records have specific documented evidence of a real wearable perfume. Rebuild the final files with `tools/build_final_perfume_catalog.py`; do not add a record unless it satisfies the same scope rule.
