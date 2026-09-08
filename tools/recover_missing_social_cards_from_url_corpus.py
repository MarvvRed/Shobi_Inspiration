#!/usr/bin/env python3
from __future__ import annotations
import json,re,unicodedata,urllib.request,urllib.error
from pathlib import Path
from difflib import SequenceMatcher
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'; CORPUS=ROOT/'fragrantica-scraper-archive/perfume_urls.txt'; IMG=ROOT/'fragrantica-scraper-archive/social-cards/images'; OUT=ROOT/'social-card-corpus-recovery-report.json'
BASE='https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{id}.jpeg'
ID_RE=re.compile(r'-(\d+)\.html(?:[?#].*)?$',re.I)
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower(); return re.sub(r'[^a-z0-9]+',' ',s).strip()
def parse_url(u):
 m=ID_RE.search(u); parts=u.split('/perfume/',1)[-1].split('/')
 if not m or len(parts)<2:return None
 brand=parts[0].replace('-',' '); slug=parts[1].rsplit('-',1)[0].replace('-',' ')
 return {'url':u.strip(),'id':int(m.group(1)),'brand':brand,'name':slug}
def fid(p):
 for k in ('fragranticaId','fragrantica_id'):
  v=p.get(k)
  if str(v or '').isdigit():return int(v)
 u=str(p.get('fragranticaUrl') or p.get('fragrantica_url') or '')
 m=ID_RE.search(u); return int(m.group(1)) if m else None
def official(p): return str(p.get('status','')).upper().startswith('VERIFIED')
def brand(p): return p.get('brand') or p.get('originalBrand') or p.get('original_brand') or ''
def name(p): return p.get('inspiredBy') or p.get('originalPerfume') or p.get('original_perfume') or p.get('name') or ''
def code(p): return str(p.get('code') or p.get('shobiCode') or p.get('shobi_code') or '')
def fetch_card(i):
 req=urllib.request.Request(BASE.format(id=i),headers={'User-Agent':'Mozilla/5.0','Accept':'image/*'})
 try:
  with urllib.request.urlopen(req,timeout=20) as r:d=r.read(5_000_000)
  return d if d.startswith(b'\xff\xd8') and d.endswith(b'\xff\xd9') else None
 except Exception:return None
def main():
 db=json.loads(DB.read_text(encoding='utf-8')); rows=db if isinstance(db,list) else db.get('perfumes',[])
 urls=[parse_url(x) for x in CORPUS.read_text(encoding='utf-8',errors='ignore').splitlines()]; urls=[x for x in urls if x]
 archive={int(m.group(1)) for p in IMG.glob('*') if (m:=re.search(r'_(\d+)$',p.stem))}
 targets=[p for p in rows if official(p) and fid(p) and fid(p) not in archive]
 results=[]; recovered=0
 for p in targets:
  b,n=norm(brand(p)),norm(name(p)); candidates=[]
  for x in urls:
   if b and norm(x['brand'])!=b: continue
   ns=SequenceMatcher(None,n,norm(x['name'])).ratio() if n else 0
   if ns>=.72:candidates.append((ns,x))
  candidates.sort(key=lambda z:z[0],reverse=True)
  tested=[]; chosen=None
  for score,x in candidates[:8]:
   if x['id']==fid(p):continue
   d=fetch_card(x['id']); tested.append({'id':x['id'],'url':x['url'],'nameScore':round(score,4),'card':bool(d)})
   if d:
    # Only auto-accept very strong same-brand/name candidates; otherwise report for review.
    if score>=.94:
     fn=f"corpus_{re.sub(r'[^A-Za-z0-9._-]+','_',code(p))}_{x['id']}.jpeg"; (IMG/fn).write_bytes(d); chosen=x; recovered+=1
    break
  results.append({'code':code(p),'brand':brand(p),'name':name(p),'currentId':fid(p),'candidateCount':len(candidates),'tested':tested,'recoveredId':chosen['id'] if chosen else None,'recoveredUrl':chosen['url'] if chosen else None})
 OUT.write_text(json.dumps({'rule':'Local perfume_urls corpus identity cross-check; exact normalized brand required; no note-pyramid use; alternate card auto-saved only at name similarity >= 0.94.','targets':len(targets),'recovered':recovered,'stillUnresolved':len(targets)-recovered,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'targets={len(targets)} recovered={recovered} unresolved={len(targets)-recovered}')
if __name__=='__main__':main()
