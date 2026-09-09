# Fragrantica v2 identity consistency audit

- Total master rows: **2369**
- Existing code-level VERIFIED: **2277**
- Identity PASS: **2242**
- Identity REVIEW: **35**
- Not mapped: **92**

PASS requires conservative name identity similarity >= 0.78 after normalization, an existing WEB_VERIFIED_FRAGRANTICA mapping, or explicit manual identity verification against Shobi + exact Fragrantica FID. Nothing is promoted from NOT_MAPPED by this audit.

## Identity review queue

- `246-JOM` — Shobi `Bronze Wood & Leather by Jo Malone London` ↔ Fragrantica `Bronze Wood Leather` (ID 52803, score 0.6129)
- `268-JOM` — Shobi `MYRRH & TONKA - JO MALONE` ↔ Fragrantica `Myrrh Tonka` (ID 42027, score 0.6111)
- `276-JOM` — Shobi `Oud & Bergamot by Jo Malone London` ↔ Fragrantica `Oud Bergamot` (ID 12928, score 0.5000)
- `299-JOM` — Shobi `WHITE LILAC & RHUBARB - JO MALONE` ↔ Fragrantica `White Lilac Rhubarb` (ID 14134, score 0.7308)
- `315-MNT` — Shobi `Aoud Orange` ↔ Fragrantica `Orange Aoud` (ID 23365, score 0.7727)
- `407-BAT` — Shobi `PINK AMBER  & MOROCCO ORCHID  - BATH & BODY WORKS` ↔ Fragrantica `Morocco Orchid Pink Amber` (ID 25388, score 0.5135)
- `417-BOUR` — Shobi `SOIR DE PARIS - BOURJOIS` ↔ Fragrantica `Soir de Paris Evening in Paris` (ID 3604, score 0.6538)
- `438-BLG` — Shobi `CORAL OMNIA` ↔ Fragrantica `Omnia Coral` (ID 14297, score 0.7273)
- `580-DON` — Shobi `Golden-delicious-eau-de-` ↔ Fragrantica `DKNY Golden Delicious` (ID 10914, score 0.7273)
- `735-JIM` — Shobi `Stars` ↔ Fragrantica `Jimmy Choo` (ID 10573, score 0.0000)
- `834-MOS` — Shobi `Cheap  Chic  So Real` ↔ Fragrantica `So Real Cheap Chic` (ID 46867, score 0.7778)
- `848-NRO` — Shobi `PURE MUSK FOR HER - NARCISO RODRIGUEZ` ↔ Fragrantica `Narciso Rodriguez For Her` (ID 209, score 0.6167)
- `1031-BRB` — Shobi `RHYTHM BRIT - BURBERRY` ↔ Fragrantica `Burberry Brit Rhythm` (ID 18903, score 0.7000)
- `1043-CAL` — Shobi `Ck Be` ↔ Fragrantica `Calvin Klein` (ID 14606, score 0.3529)
- `1063-CER` — Shobi `pour Homme Eau de Toilette (Eau de Toilette)` ↔ Fragrantica `Cerruti Pour Homme` (ID 1441, score 0.0000)
- `1204-LOE` — Shobi `Solo Cedro` ↔ Fragrantica `Solo Loewe Cedro` (ID 30321, score 0.7692)
- `1495-BRB` — Shobi `Her-london-dream-eau-de-` ↔ Fragrantica `Burberry Her London Dream` (ID 60795, score 0.6667)
- `1542-JOM` — Shobi `English Oak & Redcurrant by Jo Malone London` ↔ Fragrantica `English Oak Redcurrant` (ID 46186, score 0.6471)
- `1754-HER` — Shobi `VANILLE GALANTE HERMESSENCE - HERMES` ↔ Fragrantica `Hermessence Vanille Galante` (ID 5213, score 0.6209)
- `1802-JOM` — Shobi `Midnight Musk & Amber by Jo Malone London` ↔ Fragrantica `Midnight Musk Amber` (ID 63920, score 0.6129)
- `1826-JOM` — Shobi `Iris & White Musk by Jo Malone London` ↔ Fragrantica `Iris White Musk` (ID 12926, score 0.5556)
- `1827-JOM` — Shobi `Tropical Cherimoya by Jo Malone London` ↔ Fragrantica `Tropical Cherimoya Cologne` (ID 49602, score 0.7500)
- `1919-PRA` — Shobi `Paradoxe-eau-de-` ↔ Fragrantica `Prada Paradoxe` (ID 75668, score 0.5517)
- `1942-LAN` — Shobi `Idole-l-eau-de-parfum-nectar` ↔ Fragrantica `Idole Nectar` (ID 74137, score 0.7273)
- `1978-ARM` — Shobi `STRONGER WITH YOU INTENSENLY` ↔ Fragrantica `Emporio Armani Stronger With You Intensely` (ID 52802, score 0.7714)
- `2095-VICT` — Shobi `Strawberries-champagne-eau-de-toilette` ↔ Fragrantica `Strawberries and Champagne` (ID 8000, score 0.6875)
- `2194-ORT` — Shobi `Cuoium` ↔ Fragrantica `ORTO` (ID 119473, score 0.2000)
- `2278-BLG` — Shobi `Eau Parfumée au Thé Blanc Eau de Cologne` ↔ Fragrantica `Eau Parfumee au The Blanc` (ID 145, score 0.7188)
- `2516-GUL` — Shobi `Scandal-pour-homme-absolu` ↔ Fragrantica `Scandal Pour Homme Absolu` (ID 91053, score 0.7179)
- `2543-HUG` — Shobi `The-scent-magnetic-for-him` ↔ Fragrantica `Boss The Scent For Him Magnetic` (ID 78424, score 0.7325)
- `2627-LTN` — Shobi `Météore` ↔ Fragrantica `Meteore` (ID 62251, score 0.7143)
- `2785-VAL` — Shobi `Valentino-donna-born-in-roma-extradose` ↔ Fragrantica `Born in Roma Extradose Donna` (ID 101384, score 0.7500)
- `2802-HER` — Shobi `Terre Intense for men` ↔ Fragrantica `Terre d Hermes Intense` (ID 102772, score 0.7429)
- `2829-PARF` — Shobi `Athénaïs` ↔ Fragrantica `Athenais` (ID 123716, score 0.7500)
- `2837-GUL` — Shobi `Scandal-pour-homme-elixir` ↔ Fragrantica `Scandal Pour Homme Elixir` (ID 121453, score 0.7179)
