#!/usr/bin/env python3
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'fragrantica-v2-local-id-reconciliation.csv'
MATCH=ROOT/'fragrantica-v2-local-url-match.csv'
DBS=[ROOT/'database_v2_clean.json',ROOT/'database_complete.json']
OUT=ROOT/'fragrantica-v2-historical-local-bulk-promotion.md'

def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def code_of(x): return str(x.get('code') or x.get('shobi_code') or x.get('sku') or x.get('id') or '').strip()
def verified(x):
    vals=[x.get('fragranticaStatus'),x.get('fragrantica_status'),x.get('verification_status'),x.get('status')]
    return any(str(v or '').startswith('VERIFIED_') for v in vals)
def items_shape(p):
    d=json.loads(p.read_text(encoding='utf-8-sig'))
    if isinstance(d,list):return d,lambda xs:xs
    for k in ('perfumes','items','products','data'):
        if isinstance(d.get(k),list):return d[k],lambda xs,dd=d,kk=k:{**dd,kk:xs}
    raise RuntimeError('unsupported DB shape')

# Critical: only codes in the matcher CURRENT residual queue are eligible.
residual={r.get('shobi_code','').strip() for r in rows(MATCH)}
selected={}
for r in rows(REC):
    code=r.get('shobi_code','').strip()
    if code not in residual or r.get('classification')!='HIST_ID_CONFIRMED_LOCAL':continue
    hid=(r.get('historical_id') or '').strip(); tid=(r.get('top_local_id') or '').strip()
    if not hid or r.get('historical_in_local')!='yes':continue
    try:score=float(r.get('historical_score') or 0); cov=float(r.get('historical_coverage') or 0)
    except:continue
    if cov<1.0 or score<0.66 or (tid and tid!=hid):continue
    selected[code]={'id':hid,'url':r.get('historical_local_url','').strip(),'brand':r.get('historical_local_brand','').strip(),'name':r.get('historical_local_name','').strip(),'score':score}

changed={}; cleaned={}
for p in DBS:
    items,wrap=items_shape(p); n=0; cl=0
    for x in items:
        # Remove redundant snake_case fields accidentally added to already canonical VERIFIED rows.
        if str(x.get('fragranticaStatus') or '').startswith('VERIFIED_'):
            for k in ('fragrantica_id','fragrantica_url','fragrantica_status','fragrantica_verification_source'):
                if k in x: del x[k]; cl+=1
        c=code_of(x)
        if c not in selected or verified(x):continue
        s=selected[c]
        x['fragranticaId']=s['id']; x['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2'; x['fragranticaLocalUrl']=s['url']; x['fragranticaVerificationSource']='local historical ID confirmed in perfume_urls corpus'
        n+=1
    p.write_text(json.dumps(wrap(items),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');changed[p.name]=n;cleaned[p.name]=cl
lines=['# Bulk high-confidence historical/local promotion','',f'- Current residual queue: **{len(residual)}**',f'- Eligible residual mappings: **{len(selected)}**']+[f'- {k}: **{v}** promoted; **{cleaned[k]}** redundant snake fields removed' for k,v in changed.items()]+['','## Eligible mappings','']
for c,s in sorted(selected.items()):lines.append(f"- `{c}` -> {s['brand']} / {s['name']} — ID {s['id']} — score {s['score']:.4f}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('residual',len(residual),'eligible',len(selected),'changed',changed,'cleaned_fields',cleaned)
