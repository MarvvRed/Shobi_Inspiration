import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

DB = Path('database_complete.json')
OUT = Path('catalog-duplicate-audit.md')

def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','',s)

data=json.loads(DB.read_text(encoding='utf-8'))
rows=[]
for group in data:
    brand=(group.get('brandInfo') or {}).get('name','')
    for p in group.get('perfumes',[]):
        rows.append({'brand':brand, **p})

by_code=defaultdict(list)
by_identity=defaultdict(list)
by_pid=defaultdict(list)
by_url=defaultdict(list)
for r in rows:
    code=str(r.get('code') or '').strip().upper()
    if code: by_code[code].append(r)
    ident=(norm(r.get('brand')),norm(r.get('inspiredBy')))
    if all(ident): by_identity[ident].append(r)
    pid=str(r.get('prestashopProductId') or '').strip()
    if pid: by_pid[pid].append(r)
    url=str(r.get('shobiUrl') or '').strip().lower().rstrip('/')
    if url: by_url[url].append(r)

def groups(d): return {k:v for k,v in d.items() if len(v)>1}
code_dups=groups(by_code); identity_dups=groups(by_identity); pid_dups=groups(by_pid); url_dups=groups(by_url)

lines=['# Full catalog duplicate audit','',f'- Total rows: **{len(rows)}**',f'- Unique non-empty codes: **{len(by_code)}**',f'- Duplicate-code groups: **{len(code_dups)}**',f'- Extra rows caused by duplicate codes: **{sum(len(v)-1 for v in code_dups.values())}**',f'- Duplicate normalized Brand + Perfume groups: **{len(identity_dups)}**',f'- Duplicate Prestashop product ID groups: **{len(pid_dups)}**',f'- Duplicate Shobi URL groups: **{len(url_dups)}**','', '## Duplicate codes','']
for code, rs in sorted(code_dups.items()):
    lines.append(f'### {code} — {len(rs)} rows')
    for i,r in enumerate(rs,1):
        notes=r.get('notes') or {}; accords=r.get('mainAccords') or []
        lines.append(f"{i}. **{r.get('brand','')} — {r.get('inspiredBy','')}** | category=`{r.get('category','')}` | prestashop=`{r.get('prestashopProductId','')}` | notes={sum(len(notes.get(x) or []) for x in ('top','heart','base'))} | accords={len(accords)} | shobi=`{r.get('shobiUrl','')}`")
    lines.append('')
lines += ['## Same Brand + Perfume name but different codes','']
for ident,rs in sorted(identity_dups.items()):
    codes=sorted({str(r.get('code') or '').strip().upper() for r in rs})
    if len(codes)>1:
        lines.append(f"- **{rs[0].get('brand')} — {rs[0].get('inspiredBy')}**: {', '.join(codes)}")
lines += ['','## Duplicate Prestashop IDs','']
for pid,rs in sorted(pid_dups.items()):
    lines.append(f"- `{pid}`: " + ' | '.join(f"{r.get('code')} {r.get('brand')} — {r.get('inspiredBy')}" for r in rs))
lines += ['','## Duplicate Shobi URLs','']
for url,rs in sorted(url_dups.items()):
    lines.append(f"- `{url}`: " + ' | '.join(f"{r.get('code')} {r.get('brand')} — {r.get('inspiredBy')}" for r in rs))
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'rows={len(rows)} unique_codes={len(by_code)} duplicate_code_groups={len(code_dups)} extra_code_rows={sum(len(v)-1 for v in code_dups.values())} identity_groups={len(identity_dups)} pid_groups={len(pid_dups)} url_groups={len(url_dups)}')
for code,rs in sorted(code_dups.items()): print('DUP',code,len(rs),[(r.get('brand'),r.get('inspiredBy'),r.get('category'),r.get('prestashopProductId')) for r in rs])
