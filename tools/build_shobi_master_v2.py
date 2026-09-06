import csv
import json
from pathlib import Path

DB = Path('database_complete.json')
OUT = Path('perfume-database/catalog/shobi-master-v2-2369.csv')
REPORT = Path('perfume-database/catalog/SHOBI-MASTER-V2-STATUS.md')

CODE_KEYS = ('Code','code','Shobi Code','shobi_code')

def walk(x):
    if isinstance(x, list):
        for v in x:
            yield from walk(v)
    elif isinstance(x, dict):
        if any(k in x for k in CODE_KEYS) or any(k in x for k in ('prestashopProductId','prestashop_product_id','shobiUrl','shobi_url')):
            yield x
        else:
            for v in x.values():
                yield from walk(v)

def pick(r, *keys):
    for k in keys:
        v = r.get(k)
        if v not in (None, ''):
            return str(v).strip()
    return ''

data = json.loads(DB.read_text(encoding='utf-8-sig'))
rows = list(walk(data))
if len(rows) != 2369:
    raise SystemExit(f'ABORT: expected 2369 operational rows, found {len(rows)}')

fields = [
    'prestashop_product_id','shobi_code','brand','perfume','inspired_by','reference',
    'shobi_url','fragrantica_id','gender','season','main_notes','status','source'
]

out_rows = []
for r in rows:
    notes = r.get('Main Notes', r.get('mainNotes', r.get('main_notes', '')))
    if isinstance(notes, list):
        notes = ' | '.join(str(x) for x in notes)
    out_rows.append({
        'prestashop_product_id': pick(r,'prestashopProductId','prestashop_product_id','Prestashop ID','prestashop_id'),
        'shobi_code': pick(r,*CODE_KEYS),
        'brand': pick(r,'Brand','brand','Designer','designer'),
        'perfume': pick(r,'Perfume','perfume','Name','name'),
        'inspired_by': pick(r,'inspiredBy','Inspired By','inspired_by'),
        'reference': pick(r,'reference','Reference','shobiReference','shobi_reference'),
        'shobi_url': pick(r,'shobiUrl','shobi_url','Shobi URL','url'),
        'fragrantica_id': pick(r,'fragranticaId','fragrantica_id','Fragrantica ID'),
        'gender': pick(r,'Gender','gender'),
        'season': pick(r,'Season','season'),
        'main_notes': str(notes).strip() if notes not in (None,'') else '',
        'status': 'ACTIVE_MASTER_V2',
        'source': 'VERIFIED_OPERATIONAL_DB_2026-09-06',
    })

# Deterministic order: coded rows numerically-ish first, then uncoded.
def sort_key(x):
    code = x['shobi_code']
    head = code.split('-',1)[0]
    try:
        n = int(head)
        return (0,n,code)
    except Exception:
        return (1,10**9,code or x['perfume'])

out_rows.sort(key=sort_key)
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out_rows)

codes = [r['shobi_code'] for r in out_rows if r['shobi_code']]
empty = [r for r in out_rows if not r['shobi_code']]
if len(set(codes)) != 2368:
    raise SystemExit(f'ABORT: expected 2368 unique non-empty codes, found {len(set(codes))}')
if len(empty) != 1:
    raise SystemExit(f'ABORT: expected 1 empty-code row, found {len(empty)}')

REPORT.write_text(f'''# Shobi Master v2 status\n\nDate: 2026-09-06\n\n- Official project master: `shobi-master-v2-2369.csv`\n- Rows: **{len(out_rows)}**\n- Unique non-empty Shobi codes: **{len(set(codes))}**\n- Legitimate empty-code rows: **{len(empty)}**\n- Source: verified operational `database_complete.json`\n- Previous `shobi-master-v1.csv` is retained unchanged as historical/source evidence.\n- Backup branch `temporanea` is untouched.\n\n## Governance\n\nThis v2 file is the canonical Shobi perfume universe for the project. Future additions, removals, code changes or identity changes require explicit Shobi evidence (official Shobi page/catalog, Prestashop/Shobi identifier, or documented historical Shobi source). Non-perfume merchandise such as physical candles, home diffusers, room sprays, accessories and body-care products must not be added to this master.\n''', encoding='utf-8')

print('rows', len(out_rows))
print('unique_nonempty_codes', len(set(codes)))
print('empty_code_rows', len(empty))
print('wrote', OUT)
