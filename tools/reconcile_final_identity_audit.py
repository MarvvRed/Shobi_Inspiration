#!/usr/bin/env python3
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_v2_clean.json'
TERM=ROOT/'fragrantica-scraper-archive/corpus-match/resolved-terminal.csv'
PEND=ROOT/'fragrantica-scraper-archive/corpus-match/pending-review.csv'
OUT=ROOT/'fragrantica-final-identity-status.csv'
SUM=ROOT/'fragrantica-final-identity-summary.txt'
def rows_from_db(data):
 r=data if isinstance(data,list) else (data.get('perfumes') or data.get('records') or data.get('data') or [])
 if r and isinstance(r[0],dict) and isinstance(r[0].get('perfumes'),list):r=[p for b in r for p in b.get('perfumes',[])]
 return r
def code(p):return str(p.get('id') or p.get('code') or p.get('shobiCode') or p.get('shobi_code') or '').strip()
def fid(p):return p.get('fragranticaId') or p.get('fragrantica_id') or p.get('fid')
data=json.loads(DB.read_text(encoding='utf-8')); db=rows_from_db(data)
terminal={r['shobi_code'].strip():r for r in csv.DictReader(TERM.open(encoding='utf-8-sig',newline='')) if r.get('shobi_code','').strip()}
pending={r['shobi_code'].strip():r for r in csv.DictReader(PEND.open(encoding='utf-8-sig',newline='')) if r.get('shobi_code','').strip()}
out=[]; c={'FID_MAPPED':0,'TERMINAL_NO_FID':0,'PENDING_IDENTITY':0,'UNCLASSIFIED_NO_FID':0}
for p in db:
 k=code(p); f=fid(p)
 if f: st='FID_MAPPED'; reason=''
 elif k in terminal: st='TERMINAL_NO_FID';reason=terminal[k].get('resolution','')
 elif k in pending: st='PENDING_IDENTITY';reason=pending[k].get('resolution','UNRESOLVED_SOURCE_IDENTITY')
 else: st='UNCLASSIFIED_NO_FID';reason='NO_FID_AND_NOT_IN_TERMINAL_AUDIT'
 c[st]+=1
 out.append({'shobi_code':k,'name':p.get('name') or p.get('shobiInspiredBy') or p.get('inspired_by') or '','fragrantica_id':f or '','final_status':st,'reason':reason})
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=out[0].keys());w.writeheader();w.writerows(out)
SUM.write_text('\n'.join([f'TOTAL={len(out)}']+[f'{k}={v}' for k,v in c.items()])+'\n',encoding='utf-8')
print(SUM.read_text())