from __future__ import annotations

import csv, json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MAP=ROOT/'data/shobi-fragrantica-mapping.csv'
REPORT=ROOT/'fragrantica-scraper-archive/corpus-match/shobi-fragrantica-corpus-match.csv'
OUT=ROOT/'fragrantica-scraper-archive/corpus-match/unresolved-diagnostics.json'
SAMPLE=ROOT/'fragrantica-scraper-archive/corpus-match/unresolved-diagnostics.csv'

def read(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

mapping={r.get('shobi_code','').strip():r for r in read(MAP) if r.get('shobi_code','').strip()}
report=read(REPORT)
rows=[]; identities=Counter(); fstatuses=Counter(); combos=Counter(); ids=0; urls=0; evidence=0
for r in report:
    if r.get('status')=='FOUND':continue
    code=r.get('shobi_code','').strip(); m=mapping.get(code,{})
    ident=(m.get('identity_status') or '').strip().upper() or 'EMPTY'
    fs=(m.get('fragrantica_status') or '').strip().upper() or 'EMPTY'
    identities[ident]+=1;fstatuses[fs]+=1;combos[(ident,fs)]+=1
    if (m.get('fragrantica_id') or '').strip():ids+=1
    if (m.get('fragrantica_url') or '').strip():urls+=1
    if (m.get('evidence_note') or '').strip():evidence+=1
    rows.append({
      'shobi_code':code,'inspired_by':r.get('inspired_by',''),'current_status':r.get('status',''),
      'identity_status':ident,'fragrantica_status':fs,'original_brand':m.get('original_brand',''),
      'original_perfume':m.get('original_perfume',''),'fragrantica_id':m.get('fragrantica_id',''),
      'fragrantica_url':m.get('fragrantica_url',''),'evidence_note':m.get('evidence_note','')
    })
summary={
 'unresolved_total':len(rows),'identity_status_counts':dict(identities),'fragrantica_status_counts':dict(fstatuses),
 'identity_fragrantica_combinations':{f'{a}|{b}':n for (a,b),n in combos.items()},
 'unresolved_with_fragrantica_id':ids,'unresolved_with_fragrantica_url':urls,'unresolved_with_evidence_note':evidence
}
OUT.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
fields=list(rows[0].keys()) if rows else []
with SAMPLE.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print(json.dumps(summary,indent=2,ensure_ascii=False))
