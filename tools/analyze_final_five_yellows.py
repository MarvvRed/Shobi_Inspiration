#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps
import pytesseract

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {'1037-BLG','118-HAM','325-PECK','235-HOLL','1251-ROM'}
DB = json.loads((ROOT/'database/catalog/database_complete.json').read_text(encoding='utf-8-sig'))
SITE = json.loads((ROOT/'database/catalog/catalog_site.json').read_text(encoding='utf-8-sig'))
VALID = json.loads((ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json').read_text(encoding='utf-8'))
RAW = json.loads((ROOT/'database/fragrantica/social-cards/records/social-card-main-notes.json').read_text(encoding='utf-8'))
IMGDIR = ROOT/'database/fragrantica'/'social-cards'/'images'
GS_PATH = ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv'
OUT = ROOT/'database/audits/final-five-yellow-analysis.json'

def code(v): return str(v or '').strip().upper()
def norm(t): return re.sub(r'\s+',' ',re.sub(r'[^a-z ]+',' ',str(t or '').lower().replace('\n',' '))).strip()
def parse_gender(t):
    t=norm(t)
    if re.search(r'for women and men|for men and women',t): return 'unisex'
    if re.search(r'for women',t): return 'female'
    if re.search(r'for men',t): return 'male'
    return ''

def best_card(c,fid,valid,raw):
    v=valid.get(c) or {}; r=raw.get(c) or {}
    candidates=[]
    for p in [v.get('card'), r.get('card'), f'database/fragrantica/social-cards/images/current_{c}_{fid}.jpeg']:
        if p and str(p) not in candidates and (ROOT/str(p)).is_file(): candidates.append(str(p))
    # Prefer an exact-FID validated card, then any exact-FID filename/current card.
    if v and v.get('validated') is True and str(v.get('fragranticaId') or '')==fid and v.get('card') and (ROOT/str(v.get('card'))).is_file():
        return str(v.get('card')), 'validated'
    exact=[p for p in candidates if f'_{fid}.' in p or p.endswith(f'_{fid}.jpeg')]
    return (exact[-1] if exact else (candidates[-1] if candidates else '')), 'fallback'

def ocr(im):
    w,h=im.size
    top=im.crop((0,0,w,int(h*.25))).convert('L')
    top=ImageEnhance.Contrast(ImageOps.autocontrast(top)).enhance(2.7).resize((top.width*3,top.height*3),Image.Resampling.LANCZOS)
    top_text=pytesseract.image_to_string(top,config='--psm 11',lang='eng')
    full=ImageEnhance.Contrast(ImageOps.autocontrast(im.convert('L'))).enhance(2.0)
    full=full.resize((w*2,h*2),Image.Resampling.LANCZOS)
    full_text=pytesseract.image_to_string(full,config='--psm 11',lang='eng')
    return norm(top_text), norm(full_text)

valid={code(x.get('code')):x for x in VALID}
raw={code(x.get('code')):x for x in RAW}
with GS_PATH.open(encoding='utf-8-sig', newline='') as fh:
    gs={code(x.get('shobi_code')):x for x in csv.DictReader(fh)}
site_by={code(x.get('code')):x for x in SITE}
rows=[]
for d in DB:
    c=code(d.get('code'))
    if c not in TARGETS: continue
    fid=str(d.get('fragranticaId') or '').strip(); s=site_by.get(c) or {}; checks=s.get('validationChecks') or {}
    card, card_kind=best_card(c,fid,valid,raw)
    top_text=full_text=gender=''
    size=None
    if card:
        with Image.open(ROOT/card) as im:
            size=list(im.size); top_text,full_text=ocr(im)
        gender=parse_gender(top_text or full_text[:500])
    v=valid.get(c) or {}; g=gs.get(c) or {}
    rows.append({
        'code':c,'brand':d.get('brand'),'inspiredBy':d.get('inspiredBy'),'fid':fid,'url':d.get('fragranticaUrl'),
        'failed':[k for k,vv in checks.items() if not vv],
        'identityStatus':d.get('identityStatus'),'verificationSource':d.get('fragranticaVerificationSource'),
        'dbGender':d.get('gender'),'dbGenderAffinity':d.get('genderAffinity'),'dbGenderStatus':d.get('genderStatus'),
        'dbSeasons':d.get('seasons') or [],'dbNotes':d.get('fragranticaSocialCardNotes') or [],
        'validatedCard':v.get('card'),'validatedCardFid':str(v.get('fragranticaId') or ''),'validated':v.get('validated'),
        'validatedNotes':v.get('mainNotes') or [],'card':card,'cardKind':card_kind,'cardSize':size,
        'ocrGender':gender,'ocrTopText':top_text,'ocrFullText':full_text,
        'genderSeasonCsv':{k:g.get(k) for k in ['fragrantica_id','gender','winter','spring','summer','fall','main_season','season_confidence','season_margin','local_path']} if g else None,
    })
OUT.write_text(json.dumps({'count':len(rows),'rows':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'count':len(rows),'summary':[{'code':r['code'],'fid':r['fid'],'card':bool(r['card']),'ocrGender':r['ocrGender'],'validated':r['validated'],'validatedNotes':len(r['validatedNotes']),'gsFid':(r['genderSeasonCsv'] or {}).get('fragrantica_id'),'gsSeason':(r['genderSeasonCsv'] or {}).get('main_season')} for r in rows]},ensure_ascii=False,indent=2))
