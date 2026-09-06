# Fragrantica v2 match against local perfume_urls.txt

- URLs parsed: **55556**
- Residual rows scanned: **221**
- Residuals with local brand hint: **52**
- Suffix brand priors learned: **172**
- STRONG_EXACT_BRAND: **1**
- STRONG_UNIQUE: **1**
- GOOD_REVIEW: **0**
- EXACT_NAME_NO_BRAND: **7**
- WEAK_REVIEW: **158**
- NO_CANDIDATE: **54**

No Fragrantica web access is used. Matching uses only repository-local `perfume_urls.txt` plus local Shobi code/verified metadata. Exact-name matches without brand agreement are NOT classified strong. Brand hints come only from explicit metadata, VERIFIED suffix priors, or an exact/left-anchored brand name in the Shobi label tail. Generated code signatures are diagnostic-only and never trusted for brand selection. No mapping is promoted automatically.

## Strong candidates

- `621-EST` — BRONZE GODDESS EAU DE PARFUM (SUMMER LIMITED EDITION) -> Estee Lauder / Bronze Goddess Eau de Parfum — ID 43639 — STRONG_EXACT_BRAND — brand-source verified_suffix
- `1245-PRA` — PRADA AMBER -> Prada / Prada Amber Pour Homme Prada Man — ID 1044 — STRONG_UNIQUE — brand-source verified_suffix

## Good review candidates


## Exact local name but no brand agreement

- `728-JES` — IN BLACK -> Byblos / In Black — ID 11574 — NOT promoted
- `771-LAP` — Silver Rain -> Beard Monkey / Silver Rain — ID 126381 — NOT promoted
- `857-ONE` — You  I -> Dyad / You I — ID 98124 — NOT promoted
- `900-ROG` — FLEUR DE FIGUIER -> Chabaud Maison de Parfum / Fleur de Figuier — ID 23550 — NOT promoted
- `1205-LOL` — Au Masculin -> Adopt Parfums / Au Masculin — ID 110032 — NOT promoted
- `1550-YAN` — HOME SWEET HOME - YANKEE -> Butterfly Thai Perfume / Home Sweet Home — ID 120005 — NOT promoted
- `2438-KYLJE` — COSMIC -> Agent Provocateur / Cosmic — ID 55451 — NOT promoted
