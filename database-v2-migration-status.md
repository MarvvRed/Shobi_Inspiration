# Clean site database v2 migration

- Master source: `perfume-database/catalog/shobi-master-v2-2369.csv`
- Clean rows created: **2369**
- Unique non-empty Shobi codes: **2368**
- Legitimate empty-code rows: **1**
- Fragrantica mappings automatically trusted from old DB: **0**
- Gender automatically trusted from old DB: **0**
- Season automatically trusted from old DB: **0**
- Notes automatically trusted from old DB: **0**
- Status: **ENRICHMENT IN PROGRESS**

`database_v2_clean.json` is intentionally rebuilt from the canonical Shobi master. Old enrichment is not copied into the clean database. Existing historical/corpus data may be used only as candidate evidence and must be reverified before promotion. The live site remains on `database_complete.json` until the clean database passes the 2369-row enrichment/quality gate.
