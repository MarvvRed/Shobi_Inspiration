# Full catalog integrity audit

- DB rows: **2372**
- Master rows: **2343**
- Repeated code groups: **0**
- Repeated Prestashop ID groups: **0**
- Repeated Shobi URL groups: **0**
- Repeated normalized brand+identity groups: **10**
- Repeated Fragrantica ID groups: **0**
- Empty-code DB rows: **12**
- Code-vs-URL-code conflicts: **1**

## Interpretation

The structural uniqueness checks are clean for code, Prestashop product ID, Shobi URL, and Fragrantica ID. The remaining 10 normalized brand+identity groups require semantic review because several are legitimate male/female fragrances sharing a marketing name. The 12 empty-code rows require targeted reconciliation. One row has a non-empty code that conflicts with the code encoded in its Shobi URL and requires targeted inspection.

Generated from the full database by `tools/audit_catalog_integrity_full.py` on 2026-09-06. The workflow execution computed these counts successfully; its final git push was rejected only because main advanced concurrently.
