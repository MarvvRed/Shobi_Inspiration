# Fragrantica v2 match against local perfume_urls.txt

- URLs parsed: **55556**
- Residual rows scanned: **305**
- Residuals with local brand hint: **121**
- Suffix brand priors learned: **168**
- STRONG_UNIQUE: **15**
- GOOD_REVIEW: **5**
- WEAK_REVIEW: **227**
- NO_CANDIDATE: **58**

No Fragrantica web access is used. Matching uses only repository-local `perfume_urls.txt` plus already-verified rows for brand priors. Brand-known rows are searched inside that brand only. Spaced-dash brand suffixes are removed from the query before name scoring. `STRONG_UNIQUE` requires coherent local brand evidence. No mapping is promoted automatically.

## Strong unique candidates

- `153-PARF` — HEROD -> Parfums de Marly / Herod — ID 16939 — score 1.0000 — brand Parfums de Marly
- `553-DOL` — DOLCE -> Dolce Gabbana / Dolce — ID 22955 — score 1.0000 — brand Dolce Gabbana
- `621-EST` — BRONZE GODDESS EAU DE PARFUM (SUMMER LIMITED EDITION) -> Estee Lauder / Bronze Goddess Eau de Parfum — ID 43639 — score 1.0000 — brand Estee Lauder
- `877-PRA` — INFUSION DE FLEUR D'ORANGER -> Prada / Infusion de Fleur d Oranger — ID 5533 — score 1.0000 — brand Prada
- `1076-DRC` — FAHRENEIT -> Dior / Fahrenheit — ID 228 — score 0.9589 — brand Dior
- `1198-LAL` — ENCRE NOIR - LALIQUE -> Lalique / Encre Noire — ID 1834 — score 0.9688 — brand Lalique
- `1245-PRA` — PRADA AMBER -> Prada / Prada Amber Pour Homme Prada Man — ID 1044 — score 1.0000 — brand Prada
- `1649-GIV` — L INTERDIT INTENSE -> Givenchy / L Interdit Eau de Parfum Intense — ID 62491 — score 1.0000 — brand Givenchy
- `1860-NAS` — ABSINT - NASOMATTO -> Nasomatto / Absinth — ID 4293 — score 0.9688 — brand Nasomatto
- `1886-PARF` — DELINA LA ROSE - PDM -> Parfums de Marly / Delina La Rosee — ID 64667 — score 0.9731 — brand Parfums de Marly
- `1950-SWISA` — AL AMAKEN -> Swiss Arabian / Al Amaken — ID 22928 — score 1.0000 — brand Swiss Arabian
- `1996-LTN` — Heures d’Absence (2020) -> Louis Vuitton / Heures d Absence — ID 59485 — score 0.9748 — brand Louis Vuitton
- `2172-SWISA` — KASHKHA -> Swiss Arabian / Kashkha — ID 19456 — score 1.0000 — brand Swiss Arabian
- `2278-BLG` — Eau Parfumée au Thé Blanc Eau de Cologne -> Bvlgari / Eau Parfumee au The Blanc — ID 145 — score 1.0000 — brand Bvlgari
- `-VICT` — ANGELS ONLY -> Victoria s Secret / Angels Only — ID 24876 — score 1.0000 — brand Victoria s Secret

## Good review candidates

- `204-CRD` — Avent -> Creed / Aventus — ID 9828 — score 0.8700 — brand Creed
- `1929-BLG` — Le-gemme-tygar-eau-de- -> Bvlgari / Le Gemme Tygar Extrait — ID 120377 — score 0.8886 — brand Bvlgari
- `1978-ARM` — STRONGER WITH YOU INTENSENLY -> Giorgio Armani / Stronger With You Limited Edition — ID 79166 — score 0.8886 — brand Giorgio Armani
- `2142-PARF` — PEGASUS EXCLUSIVE - PARFUMS DE MARLY -> Parfums de Marly / Pegasus Exclusif — ID 63100 — score 0.9291 — brand Parfums de Marly
- `2313-DRC` — SAUVAGE PARFUM 2019 -> Dior / Sauvage Parfum — ID 56324 — score 0.9688 — brand Dior
