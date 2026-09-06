# Fragrantica v2 match against local perfume_urls.txt

- URLs parsed: **55556**
- Residual rows scanned: **305**
- Residuals with local brand hint: **126**
- Suffix brand priors learned: **168**
- STRONG_GLOBAL_UNIQUE: **22**
- STRONG_UNIQUE: **10**
- GOOD_REVIEW: **5**
- WEAK_REVIEW: **205**
- NO_CANDIDATE: **63**

No Fragrantica web access is used. Matching uses only repository-local `perfume_urls.txt` plus already-verified rows for brand priors. Brand-known rows are searched inside that brand only. A globally exact name is strong only when exactly one local URL has that normalized perfume name. No mapping is promoted automatically.

## Strong candidates

- `153-PARF` — HEROD -> Parfums de Marly / Herod — ID 16939 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `185-AL HAR` — Red African -> Al Haramain Perfumes / Red African — ID 61372 — STRONG_GLOBAL_UNIQUE — brand-source none
- `553-DOL` — DOLCE -> Dolce Gabbana / Dolce — ID 22955 — STRONG_UNIQUE — brand-source verified_suffix
- `621-EST` — BRONZE GODDESS EAU DE PARFUM (SUMMER LIMITED EDITION) -> Estee Lauder / Bronze Goddess Eau de Parfum — ID 43639 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `728-JES` — IN BLACK -> Byblos / In Black — ID 11574 — STRONG_GLOBAL_UNIQUE — brand-source none
- `771-LAP` — Silver Rain -> Beard Monkey / Silver Rain — ID 126381 — STRONG_GLOBAL_UNIQUE — brand-source none
- `857-ONE` — You  I -> Dyad / You I — ID 98124 — STRONG_GLOBAL_UNIQUE — brand-source none
- `869-PIER` — EXTATIC - PIERRE BALMAIN -> Balmain Beauty / Extatic — ID 22817 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `877-PRA` — INFUSION DE FLEUR D'ORANGER -> Prada / Infusion de Fleur d Oranger — ID 5533 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `900-ROG` — FLEUR DE FIGUIER -> Chabaud Maison de Parfum / Fleur de Figuier — ID 23550 — STRONG_GLOBAL_UNIQUE — brand-source none
- `1044-CAL` — ETERNITY -> Calvin Klein / Eternity — ID 257 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `1076-DRC` — FAHRENEIT -> Dior / Fahrenheit — ID 228 — STRONG_UNIQUE — brand-source verified_suffix
- `1198-LAL` — ENCRE NOIR - LALIQUE -> Lalique / Encre Noire — ID 1834 — STRONG_UNIQUE — brand-source verified_suffix
- `1205-LOL` — Au Masculin -> Adopt Parfums / Au Masculin — ID 110032 — STRONG_GLOBAL_UNIQUE — brand-source none
- `1245-PRA` — PRADA AMBER -> Prada / Prada Amber Pour Homme Prada Man — ID 1044 — STRONG_UNIQUE — brand-source verified_suffix
- `1486-TRU` — TRUSSARDI UOMO -> Trussardi / Trussardi Uomo — ID 1039 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `1523-AFN` — DEHN AL OUDH ABIYAD -> Afnan / Dehn al Oudh Abiyad — ID 27357 — STRONG_GLOBAL_UNIQUE — brand-source none
- `1628-AL HAR` — WARDIA -> Al Haramain Perfumes / Wardia — ID 19945 — STRONG_GLOBAL_UNIQUE — brand-source none
- `1649-GIV` — L INTERDIT INTENSE -> Givenchy / L Interdit Eau de Parfum Intense — ID 62491 — STRONG_UNIQUE — brand-source verified_suffix
- `1860-NAS` — ABSINT - NASOMATTO -> Nasomatto / Absinth — ID 4293 — STRONG_UNIQUE — brand-source verified_suffix
- `1886-PARF` — DELINA LA ROSE - PDM -> Parfums de Marly / Delina La Rosee — ID 64667 — STRONG_UNIQUE — brand-source verified_suffix
- `1950-SWISA` — AL AMAKEN -> Swiss Arabian / Al Amaken — ID 22928 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `1996-LTN` — Heures d’Absence (2020) -> Louis Vuitton / Heures d Absence — ID 59485 — STRONG_UNIQUE — brand-source verified_suffix
- `2172-SWISA` — KASHKHA -> Swiss Arabian / Kashkha — ID 19456 — STRONG_UNIQUE — brand-source verified_suffix
- `2173-ANFAD` — SUKAR -> Anfasic / Sukar — ID 23000 — STRONG_GLOBAL_UNIQUE — brand-source none
- `2256-GIV` — VERY IRRESISTIBLE -> Givenchy / Very Irresistible — ID 33 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `2278-BLG` — Eau Parfumée au Thé Blanc Eau de Cologne -> Bvlgari / Eau Parfumee au The Blanc — ID 145 — STRONG_UNIQUE — brand-source verified_suffix
- `2438-KYLJE` — COSMIC -> Agent Provocateur / Cosmic — ID 55451 — STRONG_GLOBAL_UNIQUE — brand-source none
- `-HUG` — HUGO MAN -> Hugo Boss / Hugo Man — ID 64606 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `-VICT` — ANGELS ONLY -> Victoria s Secret / Angels Only — ID 24876 — STRONG_GLOBAL_UNIQUE — brand-source verified_suffix
- `ALH004` — Dhahab -> Al Haramain Perfumes / Dhahab — ID 53174 — STRONG_GLOBAL_UNIQUE — brand-source none
- `ALH078` — Amber Oud Gold Edition -> Al Haramain Perfumes / Amber Oud Gold Edition — ID 51816 — STRONG_GLOBAL_UNIQUE — brand-source none

## Good review candidates

- `204-CRD` — Avent -> Creed / Aventus — ID 9828 — score 0.8700
- `1929-BLG` — Le-gemme-tygar-eau-de- -> Bvlgari / Le Gemme Tygar Extrait — ID 120377 — score 0.8886
- `1978-ARM` — STRONGER WITH YOU INTENSENLY -> Giorgio Armani / Stronger With You Limited Edition — ID 79166 — score 0.8886
- `2142-PARF` — PEGASUS EXCLUSIVE - PARFUMS DE MARLY -> Parfums de Marly / Pegasus Exclusif — ID 63100 — score 0.9291
- `2313-DRC` — SAUVAGE PARFUM 2019 -> Dior / Sauvage Parfum — ID 56324 — score 0.9688
