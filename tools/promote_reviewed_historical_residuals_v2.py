#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DBS=[ROOT/'database_v2_clean.json',ROOT/'database_complete.json'];URLS=ROOT/'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt';OUT=ROOT/'fragrantica-v2-reviewed-historical-residuals.md'
APPROVED={
 '2600-TMU':('714','Mugler','Angel Garden Of Stars Le Lys','historical local ID; Angel Lily clearly corresponds to Le Lys within Angel Garden of Stars'),
 '734-JIM':('10573','Jimmy Choo','Jimmy Choo','historical local ID; Shobi row only carries Eau de Parfum concentration for base Jimmy Choo'),
 '843-NRO':('72604','Narciso Rodriguez','Narciso Rodriguez For Her Pink Edition','reconciliation local-better candidate has full Pink identity and same brand'),
 '1034-BLG':('153','Bvlgari','Aqva Pour Homme','historical local base Aqva ID; Shobi says generic AQUA, not Edition Limitee'),
 '1080-DRC':('230','Dior','Dior Homme 2005','historical local ID for generic HOMME row; same Dior brand and base Homme identity'),
 '1092-DOL':('490','Dolce Gabbana','By','historical local ID; By Man Eau de Toilette maps to original By entry rather than The One'),
}
def walk(o):
 if isinstance(o,list):
  for x in o:yield from walk(x)
 elif isinstance(o,dict):
  if isinstance(o.get('perfumes'),list):
   for p in o['perfumes']:
    if isinstance(p,dict):yield p
  elif 'code' in o or 'inspiredBy' in o:yield o
need={v[0] for v in APPROVED.values()};urls={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
 m=re.search(r'-(\d+)\.html(?:\?.*)?$',line.strip())
 if m and m.group(1) in need:urls[m.group(1)]=line.strip()
changed={};promoted=set();skipped=set()
for path in DBS:
 data=json.loads(path.read_text(encoding='utf-8-sig'));n=0
 for p in walk(data):
  c=str(p.get('code') or '').strip()
  if c not in APPROVED:continue
  if str(p.get('fragranticaStatus') or '').startswith('VERIFIED_'):skipped.add(c);continue
  fid,b,nm,r=APPROVED[c]
  if fid not in urls:continue
  p['fragranticaId']=fid;p['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2';p['fragranticaLocalUrl']=urls[fid];p['fragranticaVerificationSource']='reviewed historical/local residual mapping';n+=1;promoted.add(c)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');changed[path.name]=n
lines=['# Reviewed historical residual promotion','',f'- Approved: **{len(APPROVED)}**',f'- Promoted this run: **{len(promoted)}**',f'- Already verified: **{len(skipped)}**']+[f'- {k}: **{v}** changed' for k,v in changed.items()]+['','## Mappings','']
for c,(fid,b,nm,r) in APPROVED.items():lines.append(f'- `{c}` -> {b} / {nm} — ID {fid} — {r}')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('approved',len(APPROVED),'promoted',len(promoted),'changed',changed,'skipped',len(skipped))
