# Fragrantica v2 local-ID reconciliation

- Residual rows: **439**
- Local Fragrantica URLs indexed by ID: **55556**
- HIST_ID_CONFIRMED_LOCAL: **136**
- HIST_ID_CONFLICT_LOCAL_BETTER: **5**
- HIST_ID_PRESENT_NEEDS_REVIEW: **61**
- HIST_ID_ABSENT_FROM_LOCAL: **169**
- NEW_LOCAL_STRONG: **7**
- NEW_LOCAL_REVIEW: **52**
- NO_LOCAL_CANDIDATE: **9**

No web access. This reconciliation uses only perfume_urls.txt + repository audit files.

## Conflicts where local URL suggests a better ID

- `843-NRO` — FOR HER PINK EAU DE TOILETTE - RODRIGUEZ — old ID 209 => Narciso Rodriguez / Narciso Rodriguez For Her (score 0.5833); local candidate ID 72604 => Narciso Rodriguez / Narciso Rodriguez For Her Pink Edition (score 0.8750)
- `1034-BLG` — AQUA - BVLGARI — old ID 153 => Bvlgari / Aqva Pour Homme (score 0.5833); local candidate ID 2094 => Bvlgari / Aqua Pour Homme Edition Limitee (score 0.8333)
- `1172-ISS` — EAU D'ISSEY HOMME - ISSEY MIYAKE — old ID 79 => Kenzo / L Eau par Kenzo pour Homme (score 0.1212); local candidate ID 720 => Issey Miyake / L eau d Issey (score 1.0000)
- `1245-PRA` — PRADA AMBER — old ID 1045 => Prada / Prada (score 0.6364); local candidate ID 1044 => Prada / Prada Amber Pour Homme Prada Man (score 1.0000)
- `1929-BLG` — Le-gemme-tygar-eau-de- — old ID 41222 => Bvlgari / Tygar (score 0.5926); local candidate ID 120377 => Bvlgari / Le Gemme Tygar Extrait (score 0.8000)

## Newly strong local candidates without historical ID

- `728-JES` — IN BLACK -> Bvlgari / Bvlgari Man In Black — ID 26358 — score 0.8333
- `877-PRA` — INFUSION DE FLEUR D'ORANGER -> Prada / Infusion de Fleur d Oranger — ID 5533 — score 0.8800
- `1486-TRU` — TRUSSARDI UOMO -> Trussardi / Trussardi Uomo — ID 1039 — score 1.0000
- `1523-AFN` — DEHN AL OUDH ABIYAD -> Afnan / Dehn al Oudh Abiyad — ID 27357 — score 0.9000
- `1649-GIV` — L INTERDIT INTENSE -> Givenchy / L Interdit Eau de Parfum Intense — ID 62491 — score 0.8333
- `2256-GIV` — VERY IRRESISTIBLE -> Givenchy / Very Irresistible — ID 33 — score 0.8333
- `[no-code]` — Danat Al Duniya Eau de Parfum -> Ajmal / Danat Al Duniya — ID 45398 — score 0.8750
