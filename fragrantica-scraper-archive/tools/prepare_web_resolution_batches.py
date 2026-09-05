from __future__ import annotations

import csv, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MAP=ROOT/'data/shobi-fragrantica-mapping.csv'
REPORT=ROOT/'fragrantica-scraper-archive/corpus-match/shobi-fragrantica-corpus-match.csv'
OUT=ROOT/'fragrantica-scraper-archive/corpus-match/web-batches'

def read(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

mapping={r.get('shobi_code','').strip():r for r in read(MAP) if r.get('shobi_code','').strip()}
rows=[]
for r in read(REPORT):
    if r.get('status')=='FOUND':continue
    code=(r.get('shobi_code') or '').strip();m=mapping.get(code,{})
    if (m.get('identity_status') or '').strip().upper()!='CONFIRMED':continue
    rows.append({
      'shobi_code':code,
      'brand':(m.get('original_brand') or '').strip(),
      'perfume':(m.get('original_perfume') or m.get('inspired_by') or '').strip(),
      'current_status':r.get('status',''),
      'fragrantica_status':m.get('fragrantica_status',''),
    })
OUT.mkdir(parents=True,exist_ok=True)
for old in OUT.glob('batch-*.csv'):old.unlink()
size=50
fields=['shobi_code','brand','perfume','current_status','fragrantica_status']
for i in range(0,len(rows),size):
    p=OUT/f'batch-{i//size+1:02d}.csv'
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows[i:i+size])
print(f'prepared {len(rows)} confirmed unresolved rows in {math.ceil(len(rows)/size)} batches')
