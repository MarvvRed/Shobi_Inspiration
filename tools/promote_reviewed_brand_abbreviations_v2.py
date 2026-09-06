#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DBS=[ROOT/'database_v2_clean.json',ROOT/'database_complete.json']
URLS=ROOT/'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
OUT=ROOT/'fragrantica-v2-reviewed-brand-abbreviations.md'
APPROVED={
 '720-GUL':('427','Jean Paul Gaultier','Classique','exact same-brand title CLASSIQUE'),
 '1629-AL HAR':('70385','Al Haramain Perfumes','Musk Maliki','exact same-brand title MUSK MALIKI'),
 '1869-DOL':('490','Dolce Gabbana','By','exact same-brand title BY'),
 '995-ZAR':('16586','Zara','Femme','same-brand POUR FEMME label maps directly to Femme'),
 '1172-ISS':('721','Issey Miyake','L Eau d Issey Pour Homme','same-brand EAU D ISSEY HOMME is direct abbreviated product identity'),
 '254-JOM':('2289','Jo Malone London','Vintage Gardenia','same-brand GARDENIA label; local historical/current candidate agrees on Vintage Gardenia'),
 '2692-SOL':('76319','Sol de Janeiro','Cheirosa Tan Lines','same-brand label explicitly preserves CHEIROSA and TAN LINES identity'),
}
def walk(o):
 if isinstance(o,list):
  for x in o: yield from walk(x)
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
  fid,b,nm,reason=APPROVED[c]
  if fid not in urls:continue
  p['fragranticaId']=fid;p['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2';p['fragranticaLocalUrl']=urls[fid];p['fragranticaVerificationSource']='brand-locked abbreviation review against local corpus';n+=1;promoted.add(c)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');changed[path.name]=n
lines=['# Reviewed brand-locked abbreviation promotion','',f'- Approved: **{len(APPROVED)}**',f'- Promoted this run: **{len(promoted)}**',f'- Already verified: **{len(skipped)}**']+[f'- {k}: **{v}** changed' for k,v in changed.items()]+['','## Mappings','']
for c,(fid,b,nm,r) in APPROVED.items():lines.append(f'- `{c}` -> {b} / {nm} — ID {fid} — {r}')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('approved',len(APPROVED),'promoted',len(promoted),'changed',changed,'skipped',len(skipped))
