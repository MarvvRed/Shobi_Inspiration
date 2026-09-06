# Shobi catalog verified status

Date: 2026-09-06

## Operational database

- Rows: 2370
- Unique non-empty Shobi codes: 2368
- Empty-code rows: 2
- Duplicate Shobi-code groups: 0
- Duplicate Prestashop-ID groups: 0
- Duplicate Shobi-URL groups: 0
- Duplicate Fragrantica-ID groups: 0
- Code-vs-URL conflicts: 0

## Perfume-only audit

The operational catalog has been audited specifically to exclude non-perfume Shobi merchandise.

- 2370 total operational rows.
- 0 rows use explicit non-perfume Shobi URL categories (home fragrance, candles, diffusers, air fresheners, perfume bottles, wax melts, body care, etc.).
- 2173 rows use directly recognized perfume-category URLs.
- The remaining legacy/no-category rows were cross-checked against the Shobi master/source evidence: 2315/2370 total rows have direct master/Shobi evidence through the automated crosscheck.
- The 55 residual records were isolated for manual/source review. Searches of Shobi/Wolt and the historical Shobi perfume list confirm that the sampled/residual codes are fragrance inspirations, not accessories/home products. Examples include 2438-KYLJE Cosmic, 2331-DOL The One Mysterious Night, 1869-DOL By Zebra, 553-DOL Dolce, 362-TMFO Orchid Soleil, 310-MIL Feuilles de Tabac, 876-PRA Infusion d'Amande, 877-PRA Infusion de Fleur d'Oranger, 1950-SWISA Al Amaken, 2172-SWISA Kashkha, 2173-ANFAD Sukar, 1783-AL HAR Sultan, 2220-AL HAR Hayati, 1526-AL HAR Mukhallat Al Emirates, 1628-AL HAR Wardia, 2256-GIV Very Irresistible, 1649-GIV L'Interdit Intense, 1000-ADO Agua Fresca, 1001-ANT King of Seduction, 1044-CAL Eternity Men, 1076-DRC Fahrenheit, 1081-DRC Homme Eau, 1196-LAC L.12.12 Magnetic, 1491-CAL Obsessed for Men, 1955-LAP Cellular Energizing, 491-CRT Must de Cartier Gold, 900-ROG Fleur de Figuier, 995-ZAR Pour Femme and others.
- Broad keyword hits such as `incense`, `bamboo`, and `candle` are not sufficient to classify a row as non-perfume. Examples: Jo Malone Incense & Cedrat, Kilian Incense Oud, Gucci Bamboo, and the Yankee Candle-inspired entries are catalogued by Shobi as wearable fragrance inspirations.

No accessory, physical candle, room diffuser, air freshener, cosmetics item, or other explicit non-perfume merchandise has been identified in the operational 2370-row database by these audits.

## Important identity conflict discovered during perfume-only verification

`185-AL HAR` is a real Shobi perfume code, but its operational identity needs correction/reconciliation: current Shobi/Wolt and the historical Shobi perfume list identify `185-AL HAR` as **RED AFRICAN - AL HARAMAIN**, whereas an operational audit previously reported the label **AMBER OUD ROUGE** for this code.

This is not evidence of non-perfume merchandise: both names are perfumes. It is an identity-label conflict and must not be used to delete the code blindly. The separate no-normal-code Red African row (pid 2111, reference AR049) must also be reconciled before changing/deleting either representation.

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

## Legitimate rows without normal Shobi numeric code

- Ajmal — Danat Al Duniya Eau de Parfum — pid 2688 — reference AR170
- Al Haramain — Red African Perfume Oil — pid 2111 — reference AR049

Do not manufacture numeric Shobi codes for these rows without authoritative evidence.

## Previously missing master rows restored

- 2604-JILS — Sun Men Jil Sander
- 2773-RIT — The Rituals of Mehr
- 2783-LTN
- 2786-LTN
- 2791-LTN
- 846-NRO — Narciso Rouge

Each is present exactly once in the operational database.

## Status

The catalog is structurally clean and the perfume-only audit has found no non-perfume merchandise in the operational database. The remaining known data-quality issue is the `185-AL HAR` Red African / Amber Oud Rouge identity conflict plus the explicitly documented truncated/nocode source-data gaps. These are perfume identity/coding issues, not evidence of accessories or home-fragrance merchandise in the catalog.
