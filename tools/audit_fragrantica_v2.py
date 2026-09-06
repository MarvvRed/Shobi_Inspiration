import csv,json,re
from pathlib import Path

MASTER=Path('perfume-database/catalog/shobi-master-v2-2369.csv')
CORPUS=Path('fragrantica-scraper-archive/corpus-match/shobi-fragrantica-corpus-match.csv')
OUT=Path('fragrantica-v2-audit.csv')
REPORT=Path('fragrantica-v2-audit.md')

def norm(s):
    s=(s or '').lower()
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

with MASTER.open(encoding='utf-8-sig',newline='') as f:
    master=list(csv.DictReader(f))
with CORPUS.open(encoding='utf-8-sig',newline='') as f:
    corpus=list(csv.DictReader(f))

by_code={}
for r in corpus:
    c=(r.get('shobi_code') or '').strip()
    if c: by_code.setdefault(c,[]).append(r)

rows=[]
counts={'VERIFIED':0,'AMBIGUOUS':0,'NOT_FOUND':0}
for m in master:
    code=(m.get('shobi_code') or '').strip()
    name=m.get('inspired_by') or m.get('perfume') or ''
    cands=by_code.get(code,[]) if code else []
    found=[]
    for c in cands:
        status=(c.get('status') or '').upper()
        fid=(c.get('fragrantica_id') or '').strip()
        if status=='FOUND' and fid:
            found.append(c)
    uniq={c.get('fragrantica_id'):c for c in found if c.get('fragrantica_id')}
    if len(uniq)==1:
        c=next(iter(uniq.values()))
        cls='VERIFIED'
        reason=(c.get('match_type') or 'FOUND')
    elif len(uniq)>1:
        c=sorted(uniq.values(),key=lambda x: float(x.get('score') or 0),reverse=True)[0]
        cls='AMBIGUOUS'; reason=f"MULTIPLE_FOUND_IDS:{','.join(sorted(uniq))}"
    else:
        c=cands[0] if cands else {}
        cls='NOT_FOUND'; reason='NO_FOUND_ID_FOR_CODE' if cands else 'NO_CORPUS_CODE_MATCH'
    counts[cls]+=1
    rows.append({
        'shobi_code':code,
        'prestashop_product_id':m.get('prestashop_product_id',''),
        'shobi_inspired_by':name,
        'classification':cls,
        'reason':reason,
        'fragrantica_id':c.get('fragrantica_id',''),
        'fragrantica_brand':c.get('fragrantica_brand',''),
        'fragrantica_perfume':c.get('fragrantica_perfume',''),
        'fragrantica_url':c.get('fragrantica_url',''),
        'match_type':c.get('match_type',''),
        'score':c.get('score',''),
    })

with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
REPORT.write_text(f"# Fragrantica v2 verification audit\n\n- Master rows: **{len(master)}**\n- VERIFIED: **{counts['VERIFIED']}**\n- AMBIGUOUS: **{counts['AMBIGUOUS']}**\n- NOT_FOUND: **{counts['NOT_FOUND']}**\n\nRules: exact Shobi-code crosswalk into the archived corpus; only FOUND rows with exactly one Fragrantica ID are classed VERIFIED. No mapping is promoted by this audit.\n",encoding='utf-8')
print(len(master),counts)
