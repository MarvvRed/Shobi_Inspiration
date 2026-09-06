import csv,json,re,unicodedata
from collections import defaultdict
from pathlib import Path
DB=Path('database_complete.json'); MASTER=Path('perfume-database/catalog/shobi-master-v1.csv'); OUT=Path('catalog-integrity-full-audit.md')
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower(); return re.sub(r'[^a-z0-9]+','',s)
def urlcode(u):
 m=re.search(r'/(\d{2,4}-[a-z0-9 ]+)(?:-[a-z]+)?(?:$|[/?#])',str(u or '').lower()); return m.group(1).upper() if m else ''
data=json.loads(DB.read_text(encoding='utf-8')); D=[]
for g in data:
 b=(g.get('brandInfo') or {}).get('name','')
 for p in g.get('perfumes',[]): D.append({'brand':b,**p})
M=list(csv.DictReader(MASTER.open(encoding='utf-8-sig',newline='')))
by_code=defaultdict(list); by_pid=defaultdict(list); by_url=defaultdict(list); by_identity=defaultdict(list); by_fid=defaultdict(list)
for r in D:
 c=str(r.get('code') or '').strip().upper(); pid=str(r.get('prestashopProductId') or '').strip(); u=str(r.get('shobiUrl') or '').strip().lower().rstrip('/'); ident=(norm(r.get('brand')),norm(r.get('inspiredBy'))); fid=str(r.get('fragranticaId') or '').strip()
 if c: by_code[c].append(r)
 if pid: by_pid[pid].append(r)
 if u: by_url[u].append(r)
 if all(ident): by_identity[ident].append(r)
 if fid: by_fid[fid].append(r)
mcodes={str(r.get('shobi_code') or '').strip().upper() for r in M if str(r.get('shobi_code') or '').strip()}
lines=['# Full catalog integrity audit','',f'- DB rows: **{len(D)}**',f'- Master rows: **{len(M)}**']
def groups(title,d):
 bad={k:v for k,v in d.items() if len(v)>1}; lines.extend(['',f'## {title}: {len(bad)} groups',''])
 for k,rs in sorted(bad.items(),key=lambda x:str(x[0])):
  lines.append(f'- `{k}`: '+ ' || '.join(f"{r.get('code','-')} / {r.get('brand','')} / {r.get('inspiredBy','')} / pid={r.get('prestashopProductId','-')}" for r in rs))
groups('Repeated code',by_code); groups('Repeated Prestashop ID',by_pid); groups('Repeated Shobi URL',by_url); groups('Repeated normalized brand+identity',by_identity); groups('Repeated Fragrantica ID',by_fid)
empty=[r for r in D if not str(r.get('code') or '').strip()]
lines.extend(['','## Empty code rows and URL-derived candidates',''])
for r in empty: lines.append(f"- {r.get('brand','')} — {r.get('inspiredBy','')} | pid={r.get('prestashopProductId','-')} | url_code={urlcode(r.get('shobiUrl','')) or '-'} | url={r.get('shobiUrl','')}")
lines.extend(['','## Code vs URL-code conflicts',''])
conf=[]
for r in D:
 c=str(r.get('code') or '').strip().upper(); uc=urlcode(r.get('shobiUrl',''))
 if c and uc and c!=uc: conf.append((c,uc,r))
for c,uc,r in conf: lines.append(f"- `{c}` vs URL `{uc}` — {r.get('brand','')} — {r.get('inspiredBy','')} | {r.get('shobiUrl','')}")
lines.extend(['','## DB codes absent from master',''])
for c in sorted(set(by_code)-mcodes):
 for r in by_code[c]: lines.append(f"- `{c}` — {r.get('brand','')} — {r.get('inspiredBy','')} | pid={r.get('prestashopProductId','-')} | url={r.get('shobiUrl','')}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('rows',len(D),'code_dup',sum(len(v)>1 for v in by_code.values()),'pid_dup',sum(len(v)>1 for v in by_pid.values()),'url_dup',sum(len(v)>1 for v in by_url.values()),'identity_dup',sum(len(v)>1 for v in by_identity.values()),'fid_dup',sum(len(v)>1 for v in by_fid.values()),'empty',len(empty),'code_url_conflicts',len(conf))