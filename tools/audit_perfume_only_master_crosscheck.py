import json,csv,re
from collections import defaultdict
DB='database_complete.json'; MASTER='perfume-database/catalog/shobi-master-v1.csv'
d=json.load(open(DB,encoding='utf-8')); rows=[]
for g in d:
 b=(g.get('brandInfo') or {}).get('name','')
 for p in g.get('perfumes',[]): rows.append({'brand':b,**p})
master=list(csv.DictReader(open(MASTER,encoding='utf-8-sig')))
def val(r,*names):
 for n in names:
  if n in r and r[n]: return str(r[n]).strip()
 return ''
def norm(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())
# Master itself came from SHOBI_LIVE_SHOW_ALL. Cross-check by code, Prestashop/product id, URL, and normalized identity.
mcodes={val(r,'code','Code','shobi_code','Shobi Code') for r in master if val(r,'code','Code','shobi_code','Shobi Code')}
mpids={val(r,'prestashop_id','Prestashop ID','product_id','id') for r in master if val(r,'prestashop_id','Prestashop ID','product_id','id')}
identity=set()
for r in master:
 b=val(r,'brand','Brand'); p=val(r,'perfume','Perfume','name','Name')
 if b or p: identity.add((norm(b),norm(p)))
confirmed=[]; residual=[]
for r in rows:
 code=val(r,'code'); pid=val(r,'prestashopId','prestashop_id','productId','id'); key=(norm(r.get('brand','')),norm(val(r,'perfume','inspiredBy')))
 why=[]
 if code and code in mcodes: why.append('master_code')
 if pid and pid in mpids: why.append('master_pid')
 if key in identity and any(key): why.append('master_identity')
 u=val(r,'shobiUrl')
 if 'leparfum.com.gr' in u: why.append('shobi_url')
 (confirmed if why else residual).append((r,why))
out=['# Perfume-only master/source crosscheck','',f'- DB rows: **{len(rows)}**',f'- Rows with direct master/Shobi evidence: **{len(confirmed)}**',f'- Residual rows without direct evidence by these fields: **{len(residual)}**','', '## Residual rows']
for r,w in residual: out.append(f"- {val(r,'code')} | {r.get('brand','')} | {val(r,'perfume','inspiredBy')} | pid={val(r,'prestashopId','prestashop_id','productId','id')} | {val(r,'shobiUrl')}")
open('catalog-perfume-only-master-crosscheck.md','w',encoding='utf-8').write('\n'.join(out)+'\n')
print('rows',len(rows),'confirmed',len(confirmed),'residual',len(residual))