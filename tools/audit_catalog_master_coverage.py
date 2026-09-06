import csv, json, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

DB=Path('database_complete.json')
MASTER=Path('perfume-database/catalog/shobi-master-v1.csv')
OUT=Path('catalog-master-coverage-audit.md')

def clean(v): return str(v or '').strip()
def code(v): return clean(v).upper()
def norm(v):
    s=unicodedata.normalize('NFKD',clean(v)).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','',s)

data=json.loads(DB.read_text(encoding='utf-8'))
db=[]
for group in data:
    brand=clean((group.get('brandInfo') or {}).get('name'))
    for p in group.get('perfumes',[]): db.append({'brand':brand,**p})
with MASTER.open(encoding='utf-8-sig',newline='') as f: master=list(csv.DictReader(f))

db_codes={code(r.get('code')) for r in db if code(r.get('code'))}
master_codes={code(r.get('shobi_code')) for r in master if code(r.get('shobi_code'))}
db_by_code=defaultdict(list); master_by_code=defaultdict(list)
for r in db:
    if code(r.get('code')): db_by_code[code(r.get('code'))].append(r)
for r in master:
    if code(r.get('shobi_code')): master_by_code[code(r.get('shobi_code'))].append(r)

only_db=sorted(db_codes-master_codes); only_master=sorted(master_codes-db_codes); common=sorted(db_codes&master_codes)
empty_db=[r for r in db if not code(r.get('code'))]
empty_master=[r for r in master if not code(r.get('shobi_code'))]
status=Counter(clean(r.get('status')) or '(empty)' for r in master)
source=Counter(clean(r.get('source')) or '(empty)' for r in master)

# Same code but materially different identity label between DB and master.
identity_mismatch=[]
for c in common:
    dn={norm(r.get('inspiredBy')) for r in db_by_code[c] if norm(r.get('inspiredBy'))}
    mn={norm(r.get('inspired_by')) for r in master_by_code[c] if norm(r.get('inspired_by'))}
    if dn and mn and dn.isdisjoint(mn):
        identity_mismatch.append((c, sorted({clean(r.get('inspiredBy')) for r in db_by_code[c]}), sorted({clean(r.get('inspired_by')) for r in master_by_code[c]})))

lines=['# Catalog vs Shobi master coverage audit','',
 f'- Operational database rows: **{len(db)}**',f'- Operational unique non-empty codes: **{len(db_codes)}**',f'- Operational rows with empty code: **{len(empty_db)}**',
 f'- Shobi master rows: **{len(master)}**',f'- Shobi master unique non-empty codes: **{len(master_codes)}**',f'- Shobi master rows with empty code: **{len(empty_master)}**',
 f'- Codes present in both: **{len(common)}**',f'- Codes only in operational database: **{len(only_db)}**',f'- Codes only in Shobi master: **{len(only_master)}**',f'- Same-code identity-label mismatches: **{len(identity_mismatch)}**','',
 '## Master status counts']
for k,v in status.most_common(): lines.append(f'- {k}: **{v}**')
lines+=['','## Master source counts']
for k,v in source.most_common(): lines.append(f'- {k}: **{v}**')
lines+=['','## Codes only in operational database']
for c in only_db:
    for r in db_by_code[c]: lines.append(f"- `{c}` — {clean(r.get('brand'))} — {clean(r.get('inspiredBy'))} | prestashop={clean(r.get('prestashopProductId'))} | {clean(r.get('shobiUrl'))}")
lines+=['','## Codes only in Shobi master']
for c in only_master:
    for r in master_by_code[c]: lines.append(f"- `{c}` — {clean(r.get('inspired_by'))} | status={clean(r.get('status'))} | prestashop={clean(r.get('prestashop_product_id'))} | {clean(r.get('url'))}")
lines+=['','## Operational rows with empty code']
for r in empty_db: lines.append(f"- {clean(r.get('brand'))} — {clean(r.get('inspiredBy'))} | prestashop={clean(r.get('prestashopProductId'))} | {clean(r.get('shobiUrl'))}")
lines+=['','## Same-code identity-label mismatches']
for c,dn,mn in identity_mismatch: lines.append(f"- `{c}` — DB: {' / '.join(dn)} | master: {' / '.join(mn)}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'db_rows={len(db)} db_codes={len(db_codes)} db_empty={len(empty_db)} master_rows={len(master)} master_codes={len(master_codes)} master_empty={len(empty_master)} common={len(common)} only_db={len(only_db)} only_master={len(only_master)} identity_mismatch={len(identity_mismatch)}')
