import json, sys

PATH='database_complete.json'
with open(PATH,encoding='utf-8') as f:
    data=json.load(f)

rows=[]
for gi,g in enumerate(data):
    for pi,p in enumerate(g.get('perfumes',[])):
        rows.append((gi,pi,g,p))

coded=[]; ar049=[]
for gi,pi,g,p in rows:
    code=str(p.get('code','') or '').strip()
    ref=str(p.get('reference','') or '').strip().upper()
    pid=str(p.get('prestashopProductId',p.get('prestashop_product_id','')) or '').strip()
    if code=='185-AL HAR': coded.append((gi,pi,g,p))
    if ref=='AR049' or pid=='2111': ar049.append((gi,pi,g,p))

print('coded_185',len(coded),'ar049_or_pid2111',len(ar049))
if len(coded)!=1 or len(ar049)!=1:
    raise SystemExit('Guard failed: expected exactly one coded 185 and one AR049/pid2111 row')

cgi,cpi,cg,c=coded[0]
agi,api,ag,a=ar049[0]
if (cgi,cpi)==(agi,api):
    raise SystemExit('Already reconciled into one row; no change needed')

# Guard identity of current official row.
atext=' '.join(str(a.get(k,'') or '') for k in ['perfume','inspiredBy','name']).lower()
if 'red african' not in atext:
    raise SystemExit('Guard failed: AR049/pid2111 row is not labelled Red African')

# Correct historical Shobi code identity and enrich it with authoritative current Shobi identifiers.
c['perfume']='Red African'
if 'inspiredBy' in c: c['inspiredBy']='Red African'
if 'name' in c and c.get('name'): c['name']='Red African'
for k in ['reference','prestashopProductId','prestashop_product_id','shobiUrl','url']:
    if a.get(k): c[k]=a[k]
# Preserve current row's useful source metadata where coded row lacks it.
for k,v in a.items():
    if k not in c or c.get(k) in (None,'',[],{}):
        c[k]=v
c['code']='185-AL HAR'

# Remove the separate duplicate representation, preserving one card for the real perfume.
ag['perfumes'].pop(api)

with open(PATH,'w',encoding='utf-8') as f:
    json.dump(data,f,ensure_ascii=False,indent=2)
    f.write('\n')
print('reconciled 185-AL HAR -> Red African; removed duplicate AR049/pid2111 representation')