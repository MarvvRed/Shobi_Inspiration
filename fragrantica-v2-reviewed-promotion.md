# Reviewed v2 local-corpus promotion

- Approved code mappings: **14**
- Approved code-less name mappings: **1**
- Promoted this run: **2**
- Already verified / untouched: **13**
- `database_v2_clean.json`: matched **15**, changed **2**
- `database_complete.json`: matched **14**, changed **1**

No web verification. Every ID must exist in repository-local `perfume_urls.txt`.

## Approved by code

- `1649-GIV` -> Givenchy / L Interdit Eau de Parfum Intense — ID 62491 — same brand; full meaningful-name coverage
- `1996-LTN` -> Louis Vuitton / Heures d Absence — ID 59485 — 2020 row; local candidate clearly beats 1927 variant
- `2278-BLG` -> Bvlgari / Eau Parfumee au The Blanc — ID 145 — same brand; Eau de Cologne is generic qualifier
- `204-CRD` -> Creed / Aventus — ID 9828 — same brand; clear truncated spelling Avent -> Aventus
- `2142-PARF` -> Parfums de Marly / Pegasus Exclusif — ID 63100 — same brand; Exclusive -> Exclusif spelling variant
- `2313-DRC` -> Dior / Sauvage Parfum — ID 56324 — same brand; Shobi explicitly says Sauvage Parfum 2019
- `404-BAL` -> Balenciaga / Balenciaga Paris — ID 7247 — same brand; Shobi BALE PARIS is a clear truncated Balenciaga Paris label
- `1037-BLG` -> Bvlgari / Bvlgari Man — ID 9403 — same brand; BVL MAN is an unambiguous abbreviated label for Bvlgari Man
- `1141-GIV` -> Givenchy / Pi — ID 39 — same brand; Shobi P is a one-character truncation and local alternatives are Pi variants
- `1502-CHA` -> Chanel / Coco Mademoiselle L Eau Privee — ID 62194 — same brand; noisy Shobi prefix plus COCON MADEM typo preserves the full distinctive L EAU PRIVEE identity
- `1978-ARM` -> Giorgio Armani / Emporio Armani Stronger With You Intensely — ID 52802 — same brand; exact distinctive STRONGER WITH YOU INTENSENLY target; correct local candidate is cand3, not Limited Edition
- `2122-GUR` -> Guerlain / Rosa Rossa Harvest — ID 79472 — same brand; Shobi explicitly contains HARVEST ROSA ROSSA; correct local candidate is Rosa Rossa Harvest, not base/Forte variants
- `2344-LEL` -> Le Labo / Mousse de Chene 30 Amsterdam — ID 46295 — same brand; exact distinctive Mousse de Chene 30 identity with corpus city qualifier
- `2173-ANFAD` -> Anfasic / Sukar — ID 23000 — corrected suffix-brand review: exact SUKAR under Anfasic; previous code-signature brand hint was false

## Approved code-less row

- `danat al duniya eau de parfum` -> Ajmal / Danat Al Duniya — ID 45398 — code-less row; exact normalized local name, score 1.0000, clear margin over Daanat spelling variant
