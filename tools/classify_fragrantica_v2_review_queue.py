import csv,re
from pathlib import Path
from collections import Counter

SRC=Path('fragrantica-v2-identity-audit.csv')
MAP=Path('data/shobi-fragrantica-mapping.csv')
OUT=Path('fragrantica-v2-review-classification.csv')
REPORT=Path('fragrantica-v2-review-classification.md')

def val(r,*ks):
    for k in ks:
        if r.get(k): return str(r[k]).strip()
    return ''

def norm(s): return ' '.join(re.sub(r'[^a-z0-9]+',' ',(s or '').lower()).split())

with SRC.open(encoding='utf-8-sig',newline='') as f: src=list(csv.DictReader(f))
review=[r for r in src if r.get('identity_gate')=='REVIEW']
maprows=[]
if MAP.exists():
    with MAP.open(encoding='utf-8-sig',newline='') as f: maprows=list(csv.DictReader(f))

# Build secondary evidence indexes from the large historical mapping.
by_id={}; by_code={}
for r in maprows:
    fid=val(r,'fragrantica_id','fragranticaId','fragrantica_id_candidate')
    code=val(r,'shobi_code','code','shobiCode')
    if fid: by_id.setdefault(fid,[]).append(r)
    if code: by_code.setdefault(code,[]).append(r)

name_keys=['fragrantica_perfume','fragrantica_name','perfume','name','candidate_name','original_name','matched_name']
brand_keys=['fragrantica_brand','brand','candidate_brand','original_brand']
out=[]; c=Counter()
for r in review:
    fid=r.get('fragrantica_id','').strip(); code=r.get('shobi_code','').strip()
    evidence=(by_id.get(fid,[])+by_code.get(code,[]))
    names=[]; brands=[]
    for e in evidence:
        n=val(e,*name_keys); b=val(e,*brand_keys)
        if n and norm(n)!=norm(r.get('shobi_inspired_by','')): names.append(n)
        if b: brands.append(b)
    names=list(dict.fromkeys(names)); brands=list(dict.fromkeys(brands))
    oldname=r.get('fragrantica_perfume','').strip()
    if oldname:
        cls='NAME_PRESENT_LOW_SCORE'
    elif names:
        cls='SECONDARY_NAME_AVAILABLE'
    else:
        cls='ID_ONLY_NEEDS_LOOKUP'
    c[cls]+=1
    q=dict(r); q['review_class']=cls; q['secondary_names']=' | '.join(names[:5]); q['secondary_brands']=' | '.join(brands[:5]); out.append(q)

with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=out[0].keys()); w.writeheader(); w.writerows(out)
lines=['# Fragrantica v2 review queue classification','',f'- Review rows: **{len(review)}**']
for k,v in c.most_common(): lines.append(f'- {k}: **{v}**')
lines += ['',f'- Historical mapping rows inspected: **{len(maprows)}**','','## Name-present low-score cases','']
for r in out:
    if r['review_class']=='NAME_PRESENT_LOW_SCORE': lines.append(f"- `{r['shobi_code']}` — {r['shobi_inspired_by']} ↔ {r['fragrantica_perfume']} — ID {r['fragrantica_id']} — score {r['identity_score']}")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(dict(c), 'review',len(review),'mapping_rows',len(maprows))