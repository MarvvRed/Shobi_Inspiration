# Fragrantica v2 match against local perfume_urls.txt

- URLs parsed: **55556**
- Residual rows scanned: **221**
- Residuals with local brand hint: **83**
- Suffix brand priors learned: **172**
- STRONG_EXACT_BRAND: **1**
- STRONG_UNIQUE: **1**
- GOOD_REVIEW: **0**
- EXACT_NAME_NO_BRAND: **5**
- WEAK_REVIEW: **132**
- NO_CANDIDATE: **82**

No Fragrantica web access is used. Matching uses only repository-local `perfume_urls.txt` plus local Shobi code/verified metadata. Exact-name matches without brand agreement are NOT classified strong. Code abbreviations are accepted as brand hints only when their generated signature maps to exactly one corpus brand. No mapping is promoted automatically.

## Strong candidates

- `621-EST` — BRONZE GODDESS EAU DE PARFUM (SUMMER LIMITED EDITION) -> Estee Lauder / Bronze Goddess Eau de Parfum — ID 43639 — STRONG_EXACT_BRAND — brand-source verified_suffix
- `1245-PRA` — PRADA AMBER -> Prada / Prada Amber Pour Homme Prada Man — ID 1044 — STRONG_UNIQUE — brand-source verified_suffix

## Good review candidates


## Exact local name but no brand agreement

- `771-LAP` — Silver Rain -> Beard Monkey / Silver Rain — ID 126381 — NOT promoted
- `857-ONE` — You  I -> Dyad / You I — ID 98124 — NOT promoted
- `900-ROG` — FLEUR DE FIGUIER -> Chabaud Maison de Parfum / Fleur de Figuier — ID 23550 — NOT promoted
- `1205-LOL` — Au Masculin -> Adopt Parfums / Au Masculin — ID 110032 — NOT promoted
- `2438-KYLJE` — COSMIC -> Agent Provocateur / Cosmic — ID 55451 — NOT promoted
