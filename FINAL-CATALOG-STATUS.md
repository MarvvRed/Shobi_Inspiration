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

The catalog is structurally clean under the current rules: one row per verified Shobi representation, no technical duplicate identifiers, and no code/URL conflicts. Remaining uncertainty is limited to source-data naming/coding gaps explicitly documented above; these should not be guessed away.
