# Shobi catalog verified status

Date: 2026-09-06

## Operational database

- Rows: 2369
- Unique non-empty Shobi codes: 2368
- Empty-code rows: 1
- Duplicate Shobi-code groups: 0
- Duplicate Prestashop-ID groups: 0
- Duplicate Shobi-URL groups: 0
- Duplicate Fragrantica-ID groups: 0
- Code-vs-URL conflicts: 0

## Perfume-only audit

The operational catalog has been audited specifically to exclude non-perfume Shobi merchandise.

- 0 rows use explicit non-perfume Shobi URL categories (home fragrance, physical candles, diffusers, air fresheners, perfume bottles, wax melts, body care, accessories, etc.).
- Broad keyword candidates were manually/source interpreted because words such as `incense`, `bamboo` and `candle` can be inspiration names. The Yankee Candle-inspired entries, Jo Malone Incense entries, Kilian Incense Oud and Gucci Bamboo are wearable Shobi fragrance inspirations, not the corresponding physical home/accessory products.
- The legacy/no-category residual set was isolated and cross-checked against Shobi master/source evidence and public Shobi/Wolt/historical perfume listings. No explicit non-perfume merchandise was identified.
- The database is therefore treated as a perfume/fragrance-inspiration catalog, not a dump of the whole Shobi store.

## Red African reconciliation — resolved

The previous identity conflict is closed.

- Historical Shobi/Wolt and the Shobi perfume list identify `185-AL HAR` as **RED AFRICAN — AL HARAMAIN**.
- Current official Shobi identifies **RED AFRICAN — AL HARAMAIN PERFUMES** as reference `AR049` and offers it as Eau de Parfum as well as other selectable formats.
- The operational database previously had two representations of this same fragrance: coded `185-AL HAR` mislabeled `AMBER OUD ROUGE`, and a separate no-normal-code Red African row (`pid 2111`, `AR049`).
- These were reconciled into one card: `185-AL HAR` = **Red African**, enriched with the current AR049/pid 2111 Shobi identifiers. The separate duplicate representation was removed.
- Amber Oud Rouge is a real Al Haramain perfume, but no evidence found in this audit supports assigning Shobi code `185-AL HAR` to Amber Oud Rouge.

## Legitimate same-name groups

These are not technical duplicates. They represent different Shobi products/sexes/brands despite sharing the normalized inspiration name.

- Calvin Klein — Eternity: 470-CAL (women) / 1044-CAL (men)
- Carolina Herrera — 212 VIP Wild Party: 483-CAR (women, WP080) / 1057-CAR (men, MP055)
- Clinique — Happy: 548-CLI (women, WP138) / 1086-CLI (men, MP082)
- Dolce & Gabbana — Light Blue Eau Intense: 1872-DOL (women, WP697) / 1096-DOL (men, MP088)
- Dolce & Gabbana — The One: 566-DOL (women, WP155) / 1099-DOL (men, MP091)
- Gucci — Guilty Intense: 1866-GUC (women, WP775) / 1146-GUC (men, MP136)
- Mugler — Angel: 920-TMU (women, WP455) / 1262-TMU (men, MP238)
- Rabanne — Million Gold: 2456-PAC (women, WP815) / 2513-PAC (Million Gold Man, MP370)
- Ralph Lauren — Safari: 2533-RAL (women, WP840) / 1250-RAL (men, MP227)
- Erba Pura: 174-SOS is Sospiro (AR039); 1887-XER is Xerjoff (AR214). Keep both because Shobi explicitly catalogs them under different houses/codes.

## Truncated Shobi identities

The following are real distinct Shobi products with distinct Prestashop IDs/codes, but the live/master inspiration text is truncated. Do not invent perfume identities until authoritative evidence is found.

- 2783-LTN — pid 5051 — AR578 — current text: `the fragrance notes`
- 2786-LTN — pid 5054 — AR580 — current text: `the fragrance notes`
- 2791-LTN — pid 5060 — AR585 — current text: `the fragrance notes of`

The normalized-name audit therefore reports one extra same-name group for 2783-LTN/2786-LTN; this is a data-label issue, not a duplicate-code/ID/URL issue.

## Legitimate row without normal Shobi numeric code

- Ajmal — Danat Al Duniya Eau de Parfum — pid 2688 — reference AR170

Do not manufacture a numeric Shobi code without authoritative evidence.

## Previously missing master rows restored

- 2604-JILS — Sun Men Jil Sander
- 2773-RIT — The Rituals of Mehr
- 2783-LTN
- 2786-LTN
- 2791-LTN
- 846-NRO — Narciso Rouge

Each is present exactly once in the operational database.

## Current certified structural state

Post-reconciliation audit:

- 2369 rows
- 2368 unique non-empty codes
- 1 legitimate empty-code row
- 0 duplicate code groups
- 0 duplicate Prestashop-ID groups
- 0 duplicate Shobi-URL groups
- 0 duplicate Fragrantica-ID groups
- 0 code-vs-URL conflicts

Under the evidence and audit rules used for this project, no accessory, physical candle, room diffuser, air freshener, cosmetic/body-care product, or other explicit non-perfume merchandise is known to remain in the operational database. Remaining documented uncertainties concern truncated perfume identity labels, not product type.