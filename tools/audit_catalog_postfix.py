import json, re, unicodedata
from collections import Counter, defaultdict

P='database_complete.json'
with open(P,encoding='utf-8') as f: data=json.load(f)

# database_complete.json is a list of brand groups; perfume rows live in group['perfumes'].
R=[]
for group in data:
    if not isinstance(group,dict):
        continue
    b=(group.get('brandInfo') or {}).get('name','')
    for p in group.get('perfumes',[]):
        if isinstance(p,dict): R.append({'brand':b,**p})

def g(r,*ks):
    for k in ks:
        v=r.get(k)
        if v is not None and str(v).strip(): return str(v).strip()
    return ''
def norm(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()
def code(r): return g(r,'code','Code','Shobi Code','shobi_code')
def brand(r): return g(r,'brand','Brand')
def name(r): return g(r,'inspiredBy','Perfume','perfume','Name','name')
def url(r): return g(r,'shobiUrl','Shobi URL','shobi_url','URL','url')
def pid(r): return g(r,'prestashopProductId','Prestashop ID','prestashop_id','product_id')
def fid(r): return g(r,'fragranticaId','Fragrantica ID','fragrantica_id')
def dups(vals):
    c=Counter(v for v in vals if v); return {k:n for k,n in c.items() if n>1}
ident=defaultdict(list)
for r in R: ident[(norm(brand(r)),norm(name(r)))].append(code(r))
ident={k:v for k,v in ident.items() if k[0] and k[1] and len(v)>1}
empty=[r for r in R if not code(r)]
conf=[]
for r in R:
    c=code(r); u=url(r)
    m=re.search(r'/(\d{2,4}-[a-z0-9 ]+?)(?:-[a-z]+)?(?:$|[/?#])',u,re.I)
    if c and m:
        uc=m.group(1).replace('_','-').upper().strip()
        if uc!=c.upper(): conf.append((brand(r),name(r),c,uc,u))
checks=['2514-DRC','2282-DRC','2133-FRE','2313-DRC','1644-DRC','1702-KUR','2604-JILS','2773-RIT','2783-LTN','2786-LTN','2791-LTN','846-NRO']
by=defaultdict(list)
for r in R: by[code(r).upper()].append(r)
lines=['# Post-fix catalog audit','',f'- Rows: **{len(R)}**',f'- Unique non-empty codes: **{len(set(code(r).upper() for r in R if code(r)))}**',f'- Duplicate code groups: **{len(dups([code(r).upper() for r in R]))}**',f'- Duplicate Prestashop ID groups: **{len(dups([pid(r) for r in R]))}**',f'- Duplicate Shobi URL groups: **{len(dups([url(r).lower().rstrip('/') for r in R]))}**',f'- Duplicate Fragrantica ID groups: **{len(dups([fid(r) for r in R]))}**',f'- Same normalized brand+name groups: **{len(ident)}**',f'- Empty-code rows: **{len(empty)}**',f'- Code-vs-URL conflicts: **{len(conf)}**','','## Key codes']
for c in checks:
    rr=by.get(c,[]); lines.append(f'- `{c}`: {len(rr)} row(s)' + (f' — {brand(rr[0])} — {name(rr[0])} — pid={pid(rr[0])}' if rr else ''))
lines += ['','## Empty-code rows']
for r in empty: lines.append(f'- {brand(r)} — {name(r)} | pid={pid(r)} | {url(r)}')
lines += ['','## Code-vs-URL conflicts']
for x in conf: lines.append(f'- {x[0]} — {x[1]} | code=`{x[2]}` url_code=`{x[3]}` | {x[4]}')
lines += ['','## Same-name groups']
for (b,n),cs in sorted(ident.items()): lines.append(f'- {b} — {n}: {", ".join(cs)}')
open('catalog-postfix-audit.md','w',encoding='utf-8').write('\n'.join(lines)+'\n')
print('\n'.join(lines[:12]))