#!/usr/bin/env python3
import csv,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'fragrantica-v2-local-id-reconciliation.csv'
DBS=[ROOT/'database_v2_clean.json',ROOT/'database_complete.json']
OUT=ROOT/'fragrantica-v2-historical-local-bulk-promotion.md'

def load_rows():
    with REC.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def code_of(x):
    for k in ('shobi_code','code','sku','id'):
        if x.get(k): return str(x[k]).strip()
    return ''

def items_and_save_shape(p):
    data=json.loads(p.read_text(encoding='utf-8'))
    if isinstance(data,list): return data,lambda xs:xs
    for k in ('perfumes','items','products','data'):
        if isinstance(data.get(k),list): return data[k],lambda xs,d=data,key=k:{**d,key:xs}
    raise RuntimeError(f'unsupported DB shape {p}')

# Only the reconciliation class that explicitly says the historical ID is present in the local corpus.
# Require strong textual coverage and score, and exact agreement between historical and top-local ID when top-local exists.
selected={}
for r in load_rows():
    if r.get('classification')!='HIST_ID_CONFIRMED_LOCAL': continue
    hid=(r.get('historical_id') or '').strip(); tid=(r.get('top_local_id') or '').strip()
    if not hid or r.get('historical_in_local')!='yes': continue
    try: score=float(r.get('historical_score') or 0); cov=float(r.get('historical_coverage') or 0)
    except: continue
    if cov < 1.0 or score < 0.66: continue
    if tid and tid != hid: continue
    selected[r['shobi_code'].strip()]={
      'id':hid,'brand':r.get('historical_local_brand','').strip(),'name':r.get('historical_local_name','').strip(),
      'url':r.get('historical_local_url','').strip(),'score':score,'coverage':cov}

changed={}
for p in DBS:
    items,wrap=items_and_save_shape(p); n=0
    for x in items:
        c=code_of(x)
        if c not in selected: continue
        status=str(x.get('fragrantica_status') or x.get('verification_status') or x.get('status') or '')
        if status.startswith('VERIFIED_'): continue
        s=selected[c]
        x['fragrantica_id']=int(s['id']); x['fragrantica_url']=s['url']; x['fragrantica_status']='VERIFIED_LOCAL_CORPUS_V2'
        x['fragrantica_verification_source']='local historical ID confirmed in perfume_urls corpus'
        n+=1
    p.write_text(json.dumps(wrap(items),ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); changed[p.name]=n
lines=['# Bulk high-confidence historical/local promotion','',f'- Eligible mappings: **{len(selected)}**']+[f'- {k}: **{v}** changed' for k,v in changed.items()]+['','## Eligible mappings','']
for c,s in sorted(selected.items()): lines.append(f"- `{c}` -> {s['brand']} / {s['name']} — ID {s['id']} — score {s['score']:.4f}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('eligible',len(selected),'changed',changed)
