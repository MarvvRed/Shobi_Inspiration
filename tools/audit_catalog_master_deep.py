import csv,json,re,unicodedata
from collections import defaultdict
from pathlib import Path
DB=Path('database_complete.json'); MASTER=Path('perfume-database/catalog/shobi-master-v1.csv'); OUT=Path('catalog-master-deep-audit.md')
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower(); return re.sub(r'[^a-z0-9]+','',s)
def dbrows():
 data=json.loads(DB.read_text(encoding='utf-8')); out=[]
 for g in data:
  brand=(g.get('brandInfo') or {}).get('name','')
  for p in g.get('perfumes',[]): out.append({'brand':brand,**p})
 return out
D=dbrows(); M=list(csv.DictReader(MASTER.open(encoding='utf-8-sig',newline='')))
# indexes
mi_code=defaultdict(list); mi_pid=defaultdict(list); mi_url=defaultdict(list); mi_name=defaultdict(list)
for r in M:
 c=(r.get('shobi_code') or '').strip().upper(); pid=(r.get('prestashop_product_id') or '').strip(); u=(r.get('url') or '').strip().lower().rstrip('/'); n=norm(r.get('inspired_by'))
 if c: mi_code[c].append(r)
 if pid: mi_pid[pid].append(r)
 if u: mi_url[u].append(r)
 if n: mi_name[n].append(r)
di_code=defaultdict(list)
for r in D:
 c=str(r.get('code') or '').strip().upper()
 if c: di_code[c].append(r)
only_db=sorted(set(di_code)-set(mi_code)); only_m=sorted(set(mi_code)-set(di_code)); empty=[r for r in D if not str(r.get('code') or '').strip()]
lines=['# Deep catalog vs Shobi master audit','',f'- DB rows: **{len(D)}**',f'- Master rows: **{len(M)}**',f'- DB-only codes: **{len(only_db)}**',f'- Master-only codes: **{len(only_m)}**',f'- DB empty-code rows: **{len(empty)}**','']
lines+=['## DB-only code classification','']
counts=defaultdict(int)
for c in only_db:
 for r in di_code[c]:
  pid=str(r.get('prestashopProductId') or '').strip(); u=str(r.get('shobiUrl') or '').strip().lower().rstrip('/'); n=norm(r.get('inspiredBy'))
  hits=[]
  if pid and pid in mi_pid: hits.append('PRESTASHOP_ID')
  if u and u in mi_url: hits.append('URL')
  if n and n in mi_name: hits.append('NAME')
  cls='+'.join(hits) if hits else 'NO_MASTER_SIGNAL'; counts[cls]+=1
  matches=[]
  for source in (mi_pid.get(pid,[]) if pid else []),(mi_url.get(u,[]) if u else []),(mi_name.get(n,[]) if n else []):
   for x in source:
    z=(x.get('shobi_code') or '').strip().upper()
    if z and z not in matches: matches.append(z)
  lines.append(f"- `{c}` — {r.get('brand','')} — {r.get('inspiredBy','')} | pid={pid or '-'} | class={cls} | master_matches={','.join(matches) or '-'}")
lines+=['','### DB-only classification totals']
for k,v in sorted(counts.items()): lines.append(f'- {k}: **{v}**')
lines+=['','## Empty-code DB rows','']
for r in empty:
 pid=str(r.get('prestashopProductId') or '').strip(); u=str(r.get('shobiUrl') or '').strip().lower().rstrip('/'); n=norm(r.get('inspiredBy')); hits=[]
 for source,label in ((mi_pid.get(pid,[]) if pid else [],'PID'),(mi_url.get(u,[]) if u else [],'URL'),(mi_name.get(n,[]) if n else [],'NAME')):
  for x in source:
   z=(x.get('shobi_code') or '').strip().upper()
   if z: hits.append(f'{label}:{z}')
 lines.append(f"- {r.get('brand','')} — {r.get('inspiredBy','')} | pid={pid or '-'} | matches={','.join(dict.fromkeys(hits)) or '-'} | url={r.get('shobiUrl','')}")
lines+=['','## Master-only codes','']
for c in only_m:
 for r in mi_code[c]: lines.append(f"- `{c}` — {r.get('inspired_by','')} | pid={r.get('prestashop_product_id','')} | {r.get('url','')}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('db',len(D),'master',len(M),'db_only',len(only_db),'master_only',len(only_m),'empty',len(empty),'classes',dict(counts))