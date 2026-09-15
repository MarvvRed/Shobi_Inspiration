# Fragrantica v2 identity consistency audit

- Total master rows: **2369**
- Existing code-level VERIFIED: **2277**
- Identity PASS: **2273**
- Identity REVIEW: **4**
- Not mapped: **92**

PASS requires conservative name identity similarity >= 0.78 after normalization, an existing WEB_VERIFIED_FRAGRANTICA mapping, or explicit manual identity verification against Shobi + exact Fragrantica FID. Nothing is promoted from NOT_MAPPED by this audit.

## Identity review queue

- `735-JIM` — Shobi `Stars` ↔ Fragrantica `Jimmy Choo` (ID 10573, score 0.0000)
- `848-NRO` — Shobi `PURE MUSK FOR HER - NARCISO RODRIGUEZ` ↔ Fragrantica `Narciso Rodriguez For Her` (ID 209, score 0.6167)
- `1043-CAL` — Shobi `Ck Be` ↔ Fragrantica `Calvin Klein` (ID 14606, score 0.3529)
- `2194-ORT` — Shobi `Cuoium` ↔ Fragrantica `ORTO` (ID 119473, score 0.2000)
