# Shobi ↔ Fragrantica URL corpus match

This report compares the Shobi master catalog with the archived Fragrantica URL corpus.
It favors precision: exact matches first; fuzzy matching is restricted to an inferred brand and preserves qualifier words such as Intense/Extrait/Parfum.

## Corpus
- Shobi catalog rows: **2343**
- Fragrantica file lines: **55964**
- Valid Fragrantica URL rows: **55963**
- Invalid URL rows: **1**
- Unique Fragrantica URLs: **55963**
- Unique Fragrantica IDs: **55556**

## Matching result
- FOUND: **791**
- AMBIGUOUS: **62**
- NOT_FOUND: **1463**
- MAPPED_NOT_IN_CORPUS: **27**

## Brand inference
- Existing confirmed mappings: **155**
- Unanimous code-suffix → brand mappings learned: **84**
- Shobi catalog rows covered by those brand mappings: **1324**

## Outputs
- `shobi-fragrantica-corpus-match.csv`: all Shobi rows
- `ambiguous.csv`: rows needing review
- `unmatched.csv`: rows not found in the corpus
- `summary.json`: machine-readable totals

## Invalid URL examples
- line 5338: `https://www.fragrantica.com/perfume/DS-Durga/-8801.html`
