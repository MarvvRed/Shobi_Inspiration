# Fragrantica v2 match against local perfume_urls.txt

- URLs parsed: **55556**
- Residual rows scanned: **283**
- Residuals with local brand hint: **144**
- Suffix brand priors learned: **170**
- STRONG_EXACT_BRAND: **1**
- STRONG_UNIQUE: **4**
- GOOD_REVIEW: **5**
- EXACT_NAME_NO_BRAND: **5**
- WEAK_REVIEW: **178**
- NO_CANDIDATE: **90**

No Fragrantica web access is used. Matching uses only repository-local `perfume_urls.txt` plus local Shobi code/verified metadata. Exact-name matches without brand agreement are NOT classified strong. Code abbreviations are accepted as brand hints only when their generated signature maps to exactly one corpus brand. No mapping is promoted automatically.

## Strong candidates

- `621-EST` — BRONZE GODDESS EAU DE PARFUM (SUMMER LIMITED EDITION) -> Estee Lauder / Bronze Goddess Eau de Parfum — ID 43639 — STRONG_EXACT_BRAND — brand-source verified_suffix
- `1245-PRA` — PRADA AMBER -> Prada / Prada Amber Pour Homme Prada Man — ID 1044 — STRONG_UNIQUE — brand-source verified_suffix
- `1649-GIV` — L INTERDIT INTENSE -> Givenchy / L Interdit Eau de Parfum Intense — ID 62491 — STRONG_UNIQUE — brand-source verified_suffix
- `1996-LTN` — Heures d’Absence (2020) -> Louis Vuitton / Heures d Absence — ID 59485 — STRONG_UNIQUE — brand-source verified_suffix
- `2278-BLG` — Eau Parfumée au Thé Blanc Eau de Cologne -> Bvlgari / Eau Parfumee au The Blanc — ID 145 — STRONG_UNIQUE — brand-source verified_suffix

## Good review candidates

- `204-CRD` — Avent -> Creed / Aventus — ID 9828 — score 0.8700
- `1929-BLG` — Le-gemme-tygar-eau-de- -> Bvlgari / Le Gemme Tygar Extrait — ID 120377 — score 0.8886
- `1978-ARM` — STRONGER WITH YOU INTENSENLY -> Giorgio Armani / Stronger With You Limited Edition — ID 79166 — score 0.8886
- `2142-PARF` — PEGASUS EXCLUSIVE - PARFUMS DE MARLY -> Parfums de Marly / Pegasus Exclusif — ID 63100 — score 0.9291
- `2313-DRC` — SAUVAGE PARFUM 2019 -> Dior / Sauvage Parfum — ID 56324 — score 0.9688

## Exact local name but no brand agreement

- `771-LAP` — Silver Rain -> Beard Monkey / Silver Rain — ID 126381 — NOT promoted
- `857-ONE` — You  I -> Dyad / You I — ID 98124 — NOT promoted
- `900-ROG` — FLEUR DE FIGUIER -> Chabaud Maison de Parfum / Fleur de Figuier — ID 23550 — NOT promoted
- `1205-LOL` — Au Masculin -> Adopt Parfums / Au Masculin — ID 110032 — NOT promoted
- `2438-KYLJE` — COSMIC -> Agent Provocateur / Cosmic — ID 55451 — NOT promoted
