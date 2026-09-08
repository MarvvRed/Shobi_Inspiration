#!/usr/bin/env python3
from __future__ import annotations
import json,re,unicodedata,urllib.request
from pathlib import Path
from difflib import SequenceMatcher
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'; CORPUS=ROOT/'fragrantica-scraper-archive/perfume_urls.txt'; MISSING=ROOT/'missing-social-card-recovery-report.json'; IMG=ROOT/'fragrantica-scraper-archive/social-cards/images'; OUT=ROOT/'social-card-corpus-recovery-report.json'
BASE='https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{id}.jpeg'; ID_RE=re.compile(r'-(\d+)\.html(?:[?#].*)?$',re.I)
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower(); return re.sub(r'[^a-z0-9]+',' ',s).strip()
def parse_url(u):
 m=ID_RE.search(u); parts=u.split('/perfume/',1)[-1].split('/')
 if not m or len(parts)<2:return None
 return {'url':u.strip(),'id':int(m.group(1)),'brand':parts[0].replace('-',' '),'name':parts[1].rsplit('-',1)[0].replace('-',' ')}
def fid(p):
 for k in ('fragranticaId','fragrantica_id'):
  v=p.get(k)
  if str(v or '').isdigit():return int(v)
 u=str(p.get('fragranticaUrl') or p.get('fragrantica_url') or ''); m=ID_RE.search(u); return int(m.group(1)) if m else None
def brand(p): return p.get('brand') or p.get('originalBrand') or p.get('original_brand') or ''
def name(p): return p.get('inspiredBy') or p.get('originalPerfume') or p.get('original_perfume') or p.get('name') or ''
def code(p): return str(p.get('code') or p.get('shobiCode') or p.get('shobi_code') or '')
def fetch_card(i):
 try:
  req=urllib.request.Request(BASE.format(id=i),headers={'User-Agent':'Mozilla/5.0','Accept':'image/*'})
  with urllib.request.urlopen(req,timeout=20) as r:d=r.read(5_000_000)
  return d if d.startswith(b'\xff\xd8') and d.endswith(b'\xff\xd9') else None
 except Exception:return None
def main():
 db=json.loads(DB.read_text(encoding='utf-8')); rows=db if isinstance(db,list) else db.get('perfumes',[])
 report=json.loads(MISSING.read_text(encoding='utf-8'))
 missing=[x for x in report['results'] if x.get('status')=='MISSING']
 byfid={fid(p):p for p in rows if fid(p)}
 urls=[parse_url(x) for x in CORPUS.read_text(encoding='utf-8',errors='ignore').splitlines()]; urls=[x for x in urls if x]
 results=[]; recovered=0
 for miss in missing:
  old=int(miss['fragranticaId']); p=byfid.get(old,{})
  b,n=norm(brand(p)),norm(name(p)); candidates=[]
  for x in urls:
   if b and norm(x['brand'])!=b:continue
   score=SequenceMatcher(None,n,norm(x['name'])).ratio() if n else 0
   if score>=.65:candidates.append((score,x))
  candidates.sort(key=lambda z:z[0],reverse=True); tested=[]; chosen=None
  for score,x in candidates[:15]:
   if x['id']==old:continue
   d=fetch_card(x['id']); tested.append({'id':x['id'],'url':x['url'],'nameScore':round(score,4),'card':bool(d)})
   if d and score>=.94:
    fn=f"corpus_{re.sub(r'[^A-Za-z0-9._-]+','_',code(p) or miss.get('code',''))}_{x['id']}.jpeg"; (IMG/fn).write_bytes(d); chosen=x; recovered+=1; break
  results.append({'code':code(p) or miss.get('code'),'brand':brand(p),'name':name(p),'currentId':old,'candidateCount':len(candidates),'tested':tested,'recoveredId':chosen['id'] if chosen else None,'recoveredUrl':chosen['url'] if chosen else None})
 OUT.write_text(json.dumps({'rule':'Exactly the 18 MISSING entries from missing-social-card-recovery-report.json; local URL corpus only; same normalized brand; no pyramid.','targets':len(missing),'recovered':recovered,'stillUnresolved':len(missing)-recovered,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'targets={len(missing)} recovered={recovered} unresolved={len(missing)-recovered}')
if __name__=='__main__':main()
