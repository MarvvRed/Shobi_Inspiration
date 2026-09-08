#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'
CARD_DIR=ROOT/'fragrantica-scraper-archive'/'social-cards'/'images'
REPORT=ROOT/'missing-gender-card-recovery.json'

def flatten(d):
    if isinstance(d,list) and d and isinstance(d[0],dict) and isinstance(d[0].get('perfumes'),list): return [p for b in d for p in b.get('perfumes',[])]
    return d if isinstance(d,list) else []
def official(p): return not str(p.get('fragrantica_status') or p.get('fragranticaStatus') or '').upper().startswith('RESOLVED_NO_FORCE')
def fid(p):
    for k in ('fragranticaId','fragrantica_id','fragranticaID'):
        try:
            if p.get(k) not in (None,''): return int(p[k])
        except: pass
    for k in ('fragranticaUrl','fragranticaLocalUrl','fragrantica_url'):
        m=re.search(r'-(\d+)\.html',str(p.get(k) or ''))
        if m:return int(m.group(1))
def code(p): return str(p.get('code') or p.get('shobiCode') or '').strip()

def main():
    data=json.loads(DB.read_text(encoding='utf-8')); recs=[p for p in flatten(data) if official(p)]
    have=set()
    for f in CARD_DIR.glob('*'):
        m=re.search(r'_(\d+)$',f.stem)
        if m: have.add(int(m.group(1)))
    missing=[p for p in recs if fid(p) and fid(p) not in have]
    out=[]
    for n,p in enumerate(missing,1):
        i=fid(p); c=code(p); url=f'https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{i}.jpeg'
        row={'code':c,'fragranticaId':i,'fragranticaUrl':p.get('fragranticaUrl') or p.get('fragrantica_url'),'socialCardUrl':url}
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req,timeout=25) as r:
                body=r.read(); ct=r.headers.get('Content-Type','')
            if len(body)>5000 and ('image' in ct.lower() or body[:2]==b'\xff\xd8'):
                safe=re.sub(r'[^A-Za-z0-9_.-]+','_',c) or 'no-code'; path=CARD_DIR/f'recovered_{safe}_{i}.jpeg'; path.write_bytes(body)
                row.update(status='RECOVERED',bytes=len(body),localPath=str(path.relative_to(ROOT)))
            else: row.update(status='INVALID_RESPONSE',bytes=len(body),contentType=ct)
        except urllib.error.HTTPError as e: row.update(status=f'HTTP_{e.code}')
        except Exception as e: row.update(status='ERROR',error=str(e))
        out.append(row); print(n,len(missing),c,i,row['status'])
    REPORT.write_text(json.dumps({'missingBefore':len(missing),'recovered':sum(x['status']=='RECOVERED' for x in out),'items':out},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(REPORT.read_text())
if __name__=='__main__':main()
