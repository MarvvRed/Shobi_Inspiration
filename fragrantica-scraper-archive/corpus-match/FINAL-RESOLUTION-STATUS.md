# Final Shobi ↔ Fragrantica residual resolution status

Updated: 2026-09-05

## Corpus status

- Total Shobi rows: **2343**
- FOUND with legitimate Fragrantica mapping: **2307**
- Technical residual rows in matcher output: **36**
- Technical residual rows manually reviewed/classified: **36 / 36**
- Unreviewed residual rows: **0**
- FOUND coverage: **98.46%**

The remaining 36 rows must **not** be treated as 36 missing perfume matches. Every one has been manually investigated. Most are candles/home fragrance, body/hair products, layered Shobi products, invalid/counterfeit brand references, Shobi-original generic products, or genuine fragrances for which Fragrantica has no page/brand.

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

Detailed evidence is stored in:

- `resolution-audit-batch69.csv`
- `resolution-audit-batch72.csv`

## Only intrinsically unresolved identity

`334-SHI — SHIRLEY MAY - SHIRLEY MAY` is the only row for which the original product identity itself cannot currently be reconstructed. Shobi retains only the brand-level label plus `Tobacco, Woody`; its product image is a generic Shobi bottle. Fragrantica lists 91 Shirley May fragrances and no self-titled `Shirley May`, while several candidates have woody/tobacco profiles. Assigning one of them would therefore be fabricated rather than verified.

## Rule

Do not increase the FOUND count by coercing terminal/non-applicable rows into unrelated Fragrantica IDs. A row moves to FOUND only when an exact original identity and legitimate Fragrantica page can be supported by evidence.
