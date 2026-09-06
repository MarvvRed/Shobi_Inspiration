import csv, json, re
from pathlib import Path

AUDIT=Path('fragrantica-v2-audit.csv')
OLDDB=Path('perfume-database/archive/database_complete_pre_v2.json')
FILES=[
 Path('data/shobi-fragrantica-mapping.csv'),
 Path('fragrantica-scraper-archive/corpus-match/source-recovery.csv'),
 Path('fragrantica-scraper-archive/corpus-match/online-resolution-v8.csv'),
 Path('fragrantica-scraper-archive/corpus-match/resolution-audit-batch69.csv'),
 Path('fragrantica-scraper-archive/corpus-match/resolution-audit-batch72.csv'),
]
OUT=Path('fragrantica-v2-residual-recovery.csv')
REPORT=Path('fragrantica-v2-residual-recovery.md')

def s(v): return str(v or '').strip()
def norm(v): return re.sub(r'[^a-z0-9]+',' ',s(v).lower()).strip()

def get_code(row):
    for k in ('shobi_code','code','shobiCode','product_code'):
        if k in row and s(row.get(k)): return s(row.get(k))
    return ''

def get_fid(row):
    for k in ('fragrantica_id','fragranticaId','fragranticaID','fid'):
        if k in row and s(row.get(k)): return s(row.get(k))
    # fallback parse URL
    for k,v in row.items():
        if 'fragrantica' in k.lower() and 'url' in k.lower() and s(v):
            m=re.search(r'(?:-|/)(\d{3,})(?:\.html)?(?:$|[?#])',s(v))
            if m: return m.group(1)
    return ''

def get_brand(row):
    for k in ('fragrantica_brand','brand','candidate_brand','matched_brand'):
        if k in row and s(row.get(k)): return s(row.get(k))
    return ''

def get_perfume(row):
    for k in ('fragrantica_perfume','perfume','candidate_perfume','matched_perfume','fragrance'):
        if k in row and s(row.get(k)): return s(row.get(k))
    return ''

def flatten_old(obj):
    out=[]
    if isinstance(obj,list):
        for x in obj: out.extend(flatten_old(x))
    elif isinstance(obj,dict):
        if 'perfumes' in obj and isinstance(obj['perfumes'],list):
            brand=(obj.get('brandInfo') or {}).get('name','') if isinstance(obj.get('brandInfo'),dict) else ''
            for p in obj['perfumes']:
                if isinstance(p,dict):
                    q=dict(p); q['_brand']=brand; out.append(q)
        elif any(k in obj for k in ('code','id','fragranticaId')):
            out.append(obj)
    return out

with AUDIT.open(encoding='utf-8-sig',newline='') as f:
    residual=[r for r in csv.DictReader(f) if r.get('classification')=='NOT_FOUND']
res_codes={s(r.get('shobi_code')) for r in residual if s(r.get('shobi_code'))}

cands={c:[] for c in res_codes}
source_headers={}
for path in FILES:
    if not path.exists(): continue
    with path.open(encoding='utf-8-sig',newline='',errors='replace') as f:
        reader=csv.DictReader(f)
        source_headers[str(path)]=reader.fieldnames or []
        for row in reader:
            c=get_code(row)
            if c in cands:
                fid=get_fid(row)
                if fid:
                    cands[c].append((fid,str(path),get_brand(row),get_perfume(row),s(row.get('status') or row.get('match_type') or row.get('resolution') or '')))

# Old database as candidate evidence
if OLDDB.exists():
    old=json.loads(OLDDB.read_text(encoding='utf-8-sig'))
    for p in flatten_old(old):
        c=s(p.get('code'))
        if c in cands:
            fid=s(p.get('fragranticaId') or p.get('fragrantica_id'))
            if fid:
                cands[c].append((fid,str(OLDDB),s(p.get('brand') or p.get('_brand')),s(p.get('inspiredBy') or p.get('perfume')), 'OLD_DB_CANDIDATE'))

rows=[]
recovered=conflict=no_candidate=0
for r in residual:
    code=s(r.get('shobi_code'))
    vals=cands.get(code,[])
    byid={}
    for x in vals: byid.setdefault(x[0],[]).append(x)
    ids=sorted(byid)
    if len(ids)==1:
        cls='RECOVERABLE_UNIQUE'; recovered+=1
    elif len(ids)>1:
        cls='CONFLICTING_CANDIDATES'; conflict+=1
    else:
        cls='NO_CANDIDATE'; no_candidate+=1
    details=[]
    for fid in ids:
        srcs=sorted({x[1] for x in byid[fid]})
        brands=sorted({x[2] for x in byid[fid] if x[2]})
        names=sorted({x[3] for x in byid[fid] if x[3]})
        details.append(f"{fid}|src={';'.join(srcs)}|brand={';'.join(brands)}|name={';'.join(names)}")
    rows.append({
      'shobi_code':code,
      'prestashop_product_id':r.get('prestashop_product_id',''),
      'shobi_inspired_by':r.get('shobi_inspired_by',''),
      'recovery_class':cls,
      'candidate_ids':';'.join(ids),
      'candidate_evidence':' || '.join(details),
    })

with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

lines=[
 '# Fragrantica v2 residual recovery audit','',
 f'- Residual NOT_FOUND input: **{len(residual)}**',
 f'- RECOVERABLE_UNIQUE candidate ID: **{recovered}**',
 f'- CONFLICTING_CANDIDATES: **{conflict}**',
 f'- NO_CANDIDATE in archived sources: **{no_candidate}**','',
 'This is candidate recovery only. No Fragrantica ID is promoted by this step.','',
 '## Residuals',''
]
for x in rows:
    lines.append(f"- `{x['shobi_code'] or '[no-code]'}` — {x['shobi_inspired_by']} — **{x['recovery_class']}** — {x['candidate_ids'] or '-'}")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('residual',len(residual),'recoverable',recovered,'conflict',conflict,'none',no_candidate)
print('headers')
for p,h in source_headers.items(): print(p, h)
