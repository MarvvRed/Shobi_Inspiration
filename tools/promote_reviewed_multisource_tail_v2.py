#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DBS=[ROOT/'database_v2_clean.json',ROOT/'database_complete.json']
URLS=ROOT/'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
OUT=ROOT/'fragrantica-v2-reviewed-multisource-tail.md'
APPROVED={
 '1042-CAC':('2036','Cacharel','Cacharel pour L Homme','3 local sources; same Cacharel brand; POUR HOMME is the direct product identity'),
 '923-TMU':('45639','Mugler','Aura Mugler','3 local sources; same Mugler brand; Shobi label explicitly preserves AURA'),
 '1874-LTN':('60388','Louis Vuitton','California Dream','3 local sources; same Louis Vuitton brand; CALIFORNIA plus catalog fragrance descriptor identifies California Dream'),
}
def walk(o):
 if isinstance(o,list):
  for x in o: yield from walk(x)
 elif isinstance(o,dict):
  if isinstance(o.get('perfumes'),list):
   for p in o['perfumes']:
    if isinstance(p,dict): yield p
  elif 'code' in o or 'inspiredBy' in o: yield o
need={v[0] for v in APPROVED.values()}; urls={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
 m=re.search(r'-(\d+)\.html(?:\?.*)?$',line.strip())
 if m and m.group(1) in need: urls[m.group(1)]=line.strip()
changed={};promoted=set();skipped=set()
for path in DBS:
 data=json.loads(path.read_text(encoding='utf-8-sig')); n=0
 for p in walk(data):
  c=str(p.get('code') or '').strip()
  if c not in APPROVED: continue
  if str(p.get('fragranticaStatus') or '').startswith('VERIFIED_'): skipped.add(c); continue
  fid,brand,name,reason=APPROVED[c]
  if fid not in urls: continue
  p['fragranticaId']=fid;p['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2';p['fragranticaLocalUrl']=urls[fid];p['fragranticaVerificationSource']='3-source local evidence + manual brand/name review';n+=1;promoted.add(c)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');changed[path.name]=n
lines=['# Reviewed multi-source tail promotion','',f'- Approved: **{len(APPROVED)}**',f'- Promoted this run: **{len(promoted)}**',f'- Already verified: **{len(skipped)}**']+[f'- {k}: **{v}** changed' for k,v in changed.items()]+['','## Mappings','']
for c,(fid,b,n,r) in APPROVED.items(): lines.append(f'- `{c}` -> {b} / {n} — ID {fid} — {r}')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('approved',len(APPROVED),'promoted',len(promoted),'changed',changed,'skipped',len(skipped))
