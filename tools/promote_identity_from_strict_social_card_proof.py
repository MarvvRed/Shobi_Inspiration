#!/usr/bin/env python3
"""Attach identity provenance only when the exact Social Card visibly proves brand + perfume name.
Targets yellow rows whose only failed check is identity.
"""
import csv, json, re, unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; SITE=ROOT/'database/catalog/catalog_site.json'
GS=ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv'
rows=json.loads(DB.read_text(encoding='utf-8-sig'))
site=json.loads(SITE.read_text(encoding='utf-8-sig'))

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower().replace('&',' and ')
    return ' '.join(re.findall(r'[a-z0-9]+',s))
STOP={'eau','de','du','des','la','le','les','the','by','for','pour','parfum','perfume','edp','edt','fragrance','fragrances','intense','spray'}
def toks(s): return [x for x in norm(s).split() if x not in STOP and len(x)>1]
def covered(need,hay): return bool(need) and all(t in hay for t in need)

def accepted(v): return str(v or '').strip().upper() in {'VERIFIED','VALIDATED','CONFIRMED','OK','MATCH_CORRETTO','MATCH CORRETTO'}

with GS.open(encoding='utf-8-sig',newline='') as f:
    gs={str(x.get('shobi_code') or '').strip().upper():x for x in csv.DictReader(f)}

changed=[]
for r,s in zip(rows,site):
    if str(s.get('validationStatus') or '').lower()!='yellow': continue
    checks=s.get('validationChecks') or {}; failed=[k for k,v in checks.items() if not v]
    if failed!=['identity']: continue
    if not accepted(r.get('identityStatus')): continue
    c=str(r.get('code') or '').strip().upper(); fid=str(r.get('fragranticaId') or '').strip()
    e=gs.get(c) or {}
    if not fid or str(e.get('fragrantica_id') or '').strip()!=fid: continue
    card=str(e.get('local_path') or '').strip()
    if not card or not (ROOT/card).is_file(): continue
    ocr=norm(e.get('gender_ocr_text'))
    bt=toks(r.get('brand')); nt=toks(r.get('inspiredBy'))
    if not (covered(bt,ocr) and covered(nt,ocr)): continue
    r['fragranticaVerificationSource']=card
    r['fragranticaVerificationReason']='SOCIAL_CARD_EXACT_IDENTITY_TEXT'
    r['fragranticaVerificationFragranticaId']=fid
    r['fragranticaVerificationIdentityText']=str(e.get('gender_ocr_text') or '').strip()
    changed.append({'code':c,'brand':r.get('brand'),'inspiredBy':r.get('inspiredBy'),'fragranticaId':fid,'source':card})

DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'database/audits/strict-social-card-identity-promotions.json').write_text(json.dumps({'changed':len(changed),'rows':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('strict_social_card_identity_promotions',len(changed))
