# Shobi catalog verified status

Date: 2026-09-06

## Official project master

The canonical Shobi perfume universe for this project is now:

- `perfume-database/catalog/shobi-master-v2-2369.csv`
- Rows: **2369**
- Unique non-empty Shobi codes: **2368**
- Legitimate empty-code rows: **1**
- Source: verified operational `database_complete.json`

The previous `perfume-database/catalog/shobi-master-v1.csv` is retained unchanged as historical/source evidence. It is no longer the canonical current master. The backup branch `temporanea` remains untouched.

Future additions, removals, code changes or identity changes to the canonical master require explicit Shobi evidence: an official Shobi page/catalog, a Prestashop/Shobi identifier, or a documented historical Shobi source. Non-perfume merchandise such as physical candles, home diffusers, room sprays, accessories and body-care items must not be added.

## Operational database

- Rows: 2369
- Unique non-empty Shobi codes: 2368
- Empty-code rows: 1
- Duplicate Shobi-code groups: 0
- Duplicate Prestashop-ID groups: 0
- Duplicate Shobi-URL groups: 0
- Duplicate Fragrantica-ID groups: 0
- Code-vs-URL conflicts: 0
- Same normalized brand+name groups: 10, all verified legitimate distinct products

## Perfume-only audit

The operational catalog has been audited specifically to exclude non-perfume Shobi merchandise. No explicit accessory, physical candle, room diffuser, air freshener, cosmetic/body-care item or other non-perfume merchandise is known to remain. Broad words such as incense, bamboo and candle were interpreted in context because they can be perfume inspiration names.

## Red African reconciliation — resolved

`185-AL HAR` is Red African by Al Haramain. The former Amber Oud Rouge label was incorrect for this Shobi code. The coded row and the separate AR049/pid 2111 Red African representation were reconciled into one card, preserving the current Shobi identifiers.

## Previously truncated Louis Vuitton identities — resolved

- `2783-LTN` — pid 5051 — AR578 — **Ink Mark — Louis Vuitton**
- `2786-LTN` — pid 5054 — AR580 — **Rain Tea — Louis Vuitton**
- `2791-LTN` — pid 5060 — AR585 — **Moon Tale — Louis Vuitton**

The canonical `inspiredBy` fields in `database_complete.json` were corrected and the former false same-name group `2783-LTN` / `2786-LTN` disappeared from the structural audit.

## Legitimate same-name groups

These 10 remaining normalized-name groups are verified distinct Shobi products and must be retained:

- Calvin Klein — Eternity: 470-CAL (women) / 1044-CAL (men)
- Carolina Herrera — 212 VIP Wild Party: 483-CAR (women) / 1057-CAR (men)
- Clinique — Happy: 548-CLI (women) / 1086-CLI (men)
- Dolce & Gabbana — Light Blue Eau Intense: 1872-DOL (women) / 1096-DOL (men)
- Dolce & Gabbana — The One: 566-DOL (women) / 1099-DOL (men)
- Gucci — Guilty Intense: 1866-GUC (women) / 1146-GUC (men)
- Mugler — Angel: 920-TMU (women) / 1262-TMU (men)
- Rabanne — Million Gold: 2456-PAC (women) / 2513-PAC (men)
- Ralph Lauren — Safari: 2533-RAL (women) / 1250-RAL (men)
- Erba Pura: 174-SOS is Sospiro / 1887-XER is Xerjoff

## Legitimate row without normal Shobi numeric code

- Ajmal — Danat Al Duniya Eau de Parfum — pid 2688 — reference AR170

Do not manufacture a numeric Shobi code without authoritative evidence.

## Current certified structural state

Latest post-fix audit:

- 2369 rows
- 2368 unique non-empty codes
- 1 legitimate empty-code row
- 0 duplicate code groups
- 0 duplicate Prestashop-ID groups
- 0 duplicate Shobi-URL groups
- 0 duplicate Fragrantica-ID groups
- 0 code-vs-URL conflicts
- 10 same normalized brand+name groups, all verified legitimate

The previously documented Red African identity conflict and all three truncated LTN identity gaps are resolved. Under the evidence and audit rules used for this project, there is currently no known unresolved structural duplicate, code/URL conflict, or known non-perfume merchandise row in the operational database.
