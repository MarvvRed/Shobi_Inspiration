# Final Shobi ↔ Fragrantica residual resolution status

Updated: 2026-09-05

## Corpus status

- Total Shobi rows: **2343**
- FOUND with legitimate Fragrantica mapping: **2307**
- Technical residual rows in matcher output: **36**
- Terminal residuals already reviewed/classified: **35**
- True pending identity cases: **1**
- Unreviewed residual rows: **0**
- FOUND coverage: **98.46%**

The remaining 36 technical rows must **not** be treated as 36 missing perfume matches. Every one has been manually investigated. **35 are terminal/non-applicable cases**: candles/home fragrance, body/hair products, layered Shobi products, invalid/counterfeit references, Shobi-original generic products, or genuine fragrances for which Fragrantica has no exact page/brand. Only **1 row** still has an intrinsically unresolved source identity.

Operational files:

- `resolved-terminal.csv` — **35 closed residuals** that must not be searched repeatedly or coerced into unrelated Fragrantica IDs.
- `pending-review.csv` — **1 true pending case**, currently `334-SHI`.
- `resolution-audit-batch69.csv` and `resolution-audit-batch72.csv` — detailed evidence trail.

## Manual residual classifications

- NON_PERSONAL_FRAGRANCE: **18**
- NON_PERSONAL_PRODUCT: **5**
- INVALID_BRAND_REFERENCE: **2**
- LAYERED_SHOBI_PRODUCT: **2**
- REAL_FRAGRANCE_MISSING_FRAGRANTICA_PAGE: **2**
- SHOBI_ORIGINAL_GENERIC: **2**
- LEGACY_REFERENCE_NO_EXACT_FRAGRANTICA_ENTRY: **2**
- REAL_FRAGRANCE_MISSING_FRAGRANTICA_BRAND: **1**
- HOUSEHOLD_FRAGRANCE_BRAND_MISMATCH: **1**
- UNRESOLVED_SOURCE_IDENTITY: **1**

## Only true pending identity

`334-SHI — SHIRLEY MAY - SHIRLEY MAY` is the only row for which the original product identity itself cannot currently be reconstructed. Shobi retains only the brand-level label plus `Tobacco, Woody`; its product image is a generic Shobi bottle. Fragrantica lists many Shirley May fragrances and no verified self-titled entry matching the Shobi source, while several candidates have woody/tobacco profiles. Assigning one of them would therefore be fabricated rather than verified.

## Rule

Do not increase the FOUND count by coercing terminal/non-applicable rows into unrelated Fragrantica IDs. A row moves to FOUND only when an exact original identity and legitimate Fragrantica page can be supported by evidence.
