import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

DB = Path('database_complete.json')
OUT = Path('catalog-duplicate-audit.md')

def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii','ignore').decode().lower()
    s = re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def relaxed_name(name, brand=''):
    n=norm(name); b=norm(brand)
    if b and n.endswith(' '+b): n=n[:-(len(b)+1)].strip()
    if b and n.startswith(b+' '): n=n[len(b)+1:].strip()
    n=re.sub(r'\s+eau de (parfum|toilette)$','',n).strip()
    n=re.sub(r'\s+(edp|edt|parfum|perfume)$','',n).strip()
    return n

def get_fid(r):
    v=r.get('fragranticaId')
    if v not in (None,''): return str(v).strip()
    u=str(r.get('fragranticaUrl') or '')
    m=re.search(r'(?:-|/p/)(\d+)(?:\.html)?(?:$|[?#])',u)
    return m.group(1) if m else ''

data=json.loads(DB.read_text(encoding='utf-8'))
# Current DB is a flat list. Retain compatibility with the old grouped shape.
if data and isinstance(data[0],dict) and 'perfumes' in data[0]:
    rows=[]
    for group in data:
        brand=(group.get('brandInfo') or {}).get('name','')
        for p in group.get('perfumes',[]): rows.append({'brand':brand,**p})
else:
    rows=data

by_code=defaultdict(list); by_identity=defaultdict(list); by_relaxed=defaultdict(list)
by_pid=defaultdict(list); by_url=defaultdict(list); by_fid=defaultdict(list)
for r in rows:
    code=str(r.get('code') or '').strip().upper()
    if code: by_code[code].append(r)
    brand=norm(r.get('brand')); name=norm(r.get('inspiredBy')); relaxed=relaxed_name(r.get('inspiredBy'),r.get('brand'))
    if brand and name: by_identity[(brand,name)].append(r)
    if brand and relaxed: by_relaxed[(brand,relaxed)].append(r)
    pid=str(r.get('prestashopProductId') or '').strip()
    if pid: by_pid[pid].append(r)
    url=str(r.get('shobiUrl') or '').strip().lower().rstrip('/')
    if url: by_url[url].append(r)
    fid=get_fid(r)
    if fid: by_fid[fid].append(r)

def groups(d): return {k:v for k,v in d.items() if len(v)>1}
code_dups=groups(by_code); identity_dups=groups(by_identity); relaxed_dups=groups(by_relaxed)
pid_dups=groups(by_pid); url_dups=groups(by_url); fid_dups=groups(by_fid)

lines=['# Full catalog duplicate audit','',f'- Total rows: **{len(rows)}**',f'- Unique non-empty codes: **{len(by_code)}**',f'- Duplicate-code groups: **{len(code_dups)}**',f'- Extra rows caused by duplicate codes: **{sum(len(v)-1 for v in code_dups.values())}**',f'- Duplicate exact Brand + Perfume groups: **{len(identity_dups)}**',f'- Duplicate relaxed Brand + Perfume groups: **{len(relaxed_dups)}**',f'- Duplicate Fragrantica ID groups: **{len(fid_dups)}**',f'- Duplicate Prestashop product ID groups: **{len(pid_dups)}**',f'- Duplicate Shobi URL groups: **{len(url_dups)}**','', '## Same Fragrantica ID','']
for fid,rs in sorted(fid_dups.items(),key=lambda x:int(x[0]) if x[0].isdigit() else 0):
    lines.append(f"- **FID {fid}**: " + ' | '.join(f"{r.get('code')} {r.get('brand')} — {r.get('inspiredBy')}" for r in rs))
lines += ['','## Same relaxed Brand + Perfume name','']
for ident,rs in sorted(relaxed_dups.items()):
    lines.append(f"- **{rs[0].get('brand')} — {ident[1]}**: " + ' | '.join(f"{r.get('code')} [{r.get('inspiredBy')}] FID={get_fid(r)}" for r in rs))
lines += ['','## Duplicate codes','']
for code,rs in sorted(code_dups.items()):
    lines.append(f"- **{code}**: " + ' | '.join(f"{r.get('brand')} — {r.get('inspiredBy')} prestashop={r.get('prestashopProductId')}" for r in rs))
lines += ['','## Exact Brand + Perfume','']
for ident,rs in sorted(identity_dups.items()):
    lines.append(f"- **{rs[0].get('brand')} — {rs[0].get('inspiredBy')}**: " + ', '.join(str(r.get('code')) for r in rs))
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'rows={len(rows)} duplicate_code_groups={len(code_dups)} exact_identity_groups={len(identity_dups)} relaxed_identity_groups={len(relaxed_dups)} fid_groups={len(fid_dups)} pid_groups={len(pid_dups)} url_groups={len(url_dups)}')
for fid,rs in sorted(fid_dups.items()): print('FID_DUP',fid,[(r.get('code'),r.get('brand'),r.get('inspiredBy')) for r in rs])
for ident,rs in sorted(relaxed_dups.items()): print('NAME_DUP',ident,[(r.get('code'),r.get('inspiredBy'),get_fid(r)) for r in rs])
