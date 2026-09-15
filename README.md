# Shobi Perfume Inspiration

A single-page catalog for exploring Shobi perfume inspirations and their verified original wearable perfumes.

The public site currently loads the certified perfume-only projection from:

- `database/catalog/catalog_final_perfume_only.json`

The full operational/audit data is kept separately so the public page can remain lightweight while every published perfume can still be traced through the validation pipeline.

## Current catalog model

The production catalog contains only clean, unique Shobi perfumes whose original is demonstrated to be a real wearable perfume. Home fragrance, candles, room/car fragrance, body or hair products, laundry scents, accessories and non-demonstrable originals are excluded from the public catalog.

Authoritative project status and certification files:

- `OFFICIAL_DATABASE.md`
- `database/catalog/final-perfume-catalog-certification.json`
- `database/audits/FINAL-PERFUME-CATALOG.md`

## Validation

Each site record carries a validation status:

- **VERIFIED / green** — every required check passes. For Main Notes, green requires an independent exact Social Card match for note count, identity and displayed order.
- **CHECK / yellow** — evidence is incomplete or not strict enough; this is not treated as a contradiction.
- **ERROR / red** — a real contradiction has been detected, such as an identity or Fragrantica URL/ID mismatch.

Supporting OCR or metadata can help investigate a record but does not by itself certify Main Notes as green.

## Site features

- Search by perfume name, brand or Shobi code.
- Filters for gender, brand, season and accords.
- Sort by brand, name or rating/best-seller signal where available.
- Responsive perfume cards with bottle images and Main Notes.
- Favorites stored locally in the browser.
- Validation counters and per-card audit details.
- Lazy/batched rendering for a faster initial load.
- Light, dark, sepia and blue themes.

## Data flow

The live Shobi source and Fragrantica evidence are rebuilt through GitHub Actions. The pipeline regenerates the operational database, strict ordered Social Card audit, validation state and certified public catalog before publication.

The website entry point is `index.html`; `script.js` loads `database/catalog/catalog_final_perfume_only.json`, while `validation-tracker.js` reads the audit projection used for the validation badges.

## Credits

This repository originated from the **Shobi Inspiration** project by [smellyCat-deep](https://github.com/smellyCat-deep/shobi_inspiration) and is independently maintained and substantially modified by **MarvvRed**.

## Disclaimer

This project is independent and is not affiliated with, authorized by, endorsed by or otherwise officially connected with Shobi, Fragrantica, or the original perfume brands. Product and company names belong to their respective owners.

Catalog evidence is maintained for identification and research purposes; a yellow validation status explicitly means that the available proof is not yet sufficient for strict certification.

## License

GPL-3.0. See `LICENSE`.
