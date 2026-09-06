#!/usr/bin/env python3
import csv, json
from pathlib import Path

MASTER=Path('perfume-database/catalog/shobi-master-v2-2369.csv')
OUT=Path('database_v2_clean.json')
REPORT=Path('database-v2-migration-status.md')

rows=list(csv.DictReader(MASTER.open(encoding='utf-8-sig', newline='')))
if len(rows)!=2369:
    raise SystemExit(f'Expected 2369 master rows, got {len(rows)}')

out=[]
for i,r in enumerate(rows,1):
    code=(r.get('shobi_code') or '').strip()
    pid=(r.get('prestashop_product_id') or '').strip()
    stable_id=code or (f'pid:{pid}' if pid else f'master-v2:{i}')
    out.append({
        'id': stable_id,
        'code': code,
        'prestashopProductId': pid,
        'reference': (r.get('reference') or '').strip(),
        'shobiUrl': (r.get('shobi_url') or '').strip(),
        'brand': (r.get('brand') or '').strip(),
        'inspiredBy': (r.get('inspired_by') or r.get('perfume') or '').strip(),
        'fragranticaId': None,
        'fragranticaStatus': 'NEEDS_REVERIFICATION',
        'image': None,
        'genderAffinity': '',
        'seasons': [],
        'mainAccords': [],
        'notes': {'top': [], 'heart': [], 'base': []},
        'enrichmentStatus': 'PENDING',
        'masterVersion': 'shobi-master-v2-2369',
    })

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
unique_codes={x['code'] for x in out if x['code']}
empty=sum(not x['code'] for x in out)
if len(unique_codes)!=2368 or empty!=1:
    raise SystemExit(f'Integrity failure: unique_codes={len(unique_codes)} empty={empty}')
REPORT.write_text(f'''# Clean site database v2 migration\n\n- Master source: `perfume-database/catalog/shobi-master-v2-2369.csv`\n- Clean rows created: **{len(out)}**\n- Unique non-empty Shobi codes: **{len(unique_codes)}**\n- Legitimate empty-code rows: **{empty}**\n- Fragrantica mappings automatically trusted from old DB: **0**\n- Gender automatically trusted from old DB: **0**\n- Season automatically trusted from old DB: **0**\n- Notes automatically trusted from old DB: **0**\n- Status: **ENRICHMENT IN PROGRESS**\n\n`database_v2_clean.json` is intentionally rebuilt from the canonical Shobi master. Old enrichment is not copied into the clean database. Existing historical/corpus data may be used only as candidate evidence and must be reverified before promotion. The live site remains on `database_complete.json` until the clean database passes the 2369-row enrichment/quality gate.\n''', encoding='utf-8')
print('rows',len(out),'unique_codes',len(unique_codes),'empty',empty)
