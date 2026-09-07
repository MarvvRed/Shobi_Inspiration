# Fragrantica v2 match against local perfume_urls.txt

- URLs parsed: **55556**
- Residual rows scanned: **55**
- Residuals with local brand hint: **16**
- Suffix brand priors learned: **132**
- STRONG_EXACT_BRAND: **0**
- STRONG_UNIQUE: **0**
- GOOD_REVIEW: **0**
- EXACT_NAME_NO_BRAND: **1**
- WEAK_REVIEW: **40**
- NO_CANDIDATE: **14**

No Fragrantica web access is used. Matching uses only repository-local `perfume_urls.txt` plus local Shobi code/verified metadata. Exact-name matches without brand agreement are NOT classified strong. Brand hints come only from explicit metadata, an exact/left-anchored brand in the Shobi label tail, or VERIFIED suffix priors with at least two supporting verified rows, in that priority order. Generated code signatures and singleton VERIFIED suffixes are never trusted for brand selection. No mapping is promoted automatically.

## Strong candidates


## Good review candidates


## Exact local name but no brand agreement

- `1550-YAN` — HOME SWEET HOME - YANKEE -> Butterfly Thai Perfume / Home Sweet Home — ID 120005 — NOT promoted
