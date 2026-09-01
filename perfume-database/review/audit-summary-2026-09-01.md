# Full perfume identity audit — 2026-09-01

Full pass across the 2,343 Shobi catalog entries using the corrected validator and the candidate evidence already collected.

## Result

- CONFIRMED: 710
- AMBIGUOUS: 18
- UNRESOLVED: 1,366
- INTERNAL_CODE: 249
- TOTAL: 2,343

The 710 confirmed identities include 540 newly confirmed records from the second verification pass. The 18 ambiguous records are deliberately not promoted because multiple same-name releases/Fragrantica records remain plausible.

## Validation rules applied

- Agreement is counted across independent source/domain families, not search pipelines.
- Multiple sources must support the same normalized perfume identity.
- Generic/reference domains do not create HIGH_AGREEMENT status.
- Flanker/version conflicts are not auto-promoted.
- Same-name releases with no year/version in Shobi are marked AMBIGUOUS.
- Prefer unresolved/ambiguous over a forced incorrect mapping.

## Important corrected edge cases

- Shalimar Philtre de Parfum -> Guerlain, Fragrantica 62811.
- Santal 26 -> Le Labo Santal 26 (home fragrance identity), not Santal 33.
- 212 MEN -> Carolina Herrera 212 Men, Fragrantica 297.
- BAD BOY -> Carolina Herrera Bad Boy, Fragrantica 55449.
- Devotion Intense -> Dolce&Gabbana Devotion Intense, Fragrantica 96028.
- Dolce Garden -> Dolce&Gabbana, Fragrantica 48151.
- Dolce Floral Drops -> Dolce&Gabbana, Fragrantica 29524.
- Candy Gloss -> Prada Candy Gloss, Fragrantica 44534.
- Green Orange & Coriander -> Jo Loves; Jo Malone is the perfumer.
- Mango Thai Lime -> Jo Loves; Jo Malone is the perfumer.
- Fucking Fabulous -> Tom Ford, Fragrantica 46513.
- Soleil Blanc -> Tom Ford original, Fragrantica 34893.

The second ambiguous batch is stored separately in `perfume-database/confirmed/ambiguous-batch-2026-09-01-2.csv`.
