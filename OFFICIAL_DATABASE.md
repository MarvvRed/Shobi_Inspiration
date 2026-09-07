# Shobi Official Perfume Database

Official catalog baseline frozen on 2026-09-07 after completion of the Fragrantica/Shobi identity review.

- Total Shobi records: **2369**
- Identified/resolved perfumes: **2330**
- Deliberately excluded / NO_FORCE: **39**
- Remaining matcher residuals: **0**

## Canonical data files

- `database_v2_clean.json` — canonical clean database
- `database_complete.json` — complete database used by the site

The **2330 identified/resolved records** are the official Shobi perfume database baseline.
The **39 `RESOLVED_NO_FORCE` records** are not part of the official identified-perfume set and remain separately classified because an exact perfume identity / Fragrantica target could not be established safely.

The website filters `database_complete.json` at load time so `RESOLVED_NO_FORCE` rows are not displayed.

Do not promote a `RESOLVED_NO_FORCE` record into the official identified set without a new explicit identity verification.
