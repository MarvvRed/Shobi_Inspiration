#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
from PIL import Image,ImageEnhance,ImageOps
import pytesseract
from pytesseract import Output
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'));SITE=json.loads((ROOT/'catalog_site.json').read_text(encoding='utf-8-sig'));VALID=json.loads((ROOT/'social-card-main-notes-validated.json').read_text(encoding='utf-8'))
def code(v):return str(v or '').strip().upper()
valid_by={code(x.get('code')):x for x in VALID}
rows=[]
for d,s in zip(DB,SITE):
 c=code(d.get('code')); checks=s.get('validationChecks') or {}
 if str(s.get('validationStatus') or '').lower()!='yellow' or not str(d.get('fragranticaId') or '').strip() or checks.get('socialCard',False):continue
 fid=str(d.get('fragranticaId') or '')
 candidates=[]
 v=valid_by.get(c) or {}
 for card in [v.get('card'), f'fragrantica-scraper-archive/social-cards/images/current_{c}_{fid}.jpeg']:
  if card and (ROOT/str(card)).is_file() and str(card) not in candidates:candidates.append(str(card))
 card=candidates[-1] if candidates else ''
 if not card:continue
 with Image.open(ROOT/card) as im:
  w,h=im.size
  gray=ImageOps.autocontrast(im.convert('L'));gray=ImageEnhance.Contrast(gray).enhance(2.0)
  # Whole-card OCR at 2x; keep text and bounding boxes so next pass can infer layout dynamically.
  big=gray.resize((w*2,h*2),Image.Resampling.LANCZOS)
  data=pytesseract.image_to_data(big,config='--psm 11',lang='eng',output_type=Output.DICT)
  words=[]
  for i,t in enumerate(data.get('text',[])):
   t=' '.join(str(t or '').split())
   try:conf=float(data['conf'][i])
   except:conf=-1
   if not t or conf<20:continue
   words.append({'text':t,'conf':round(conf,1),'x':round(int(data['left'][i])/2),'y':round(int(data['top'][i])/2),'w':round(int(data['width'][i])/2),'h':round(int(data['height'][i])/2)})
  full=' '.join(x['text'] for x in words)
  rows.append({'code':c,'fid':fid,'card':card,'width':w,'height':h,'aspect':round(w/h,3),'currentNotes':d.get('fragranticaSocialCardNotes') or [],'words':words,'fullText':full})
out={'count':len(rows),'rows':rows};(ROOT/'remaining-card-layout-analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'count':len(rows),'sizes':[{k:r[k] for k in ('code','fid','width','height','aspect')} for r in rows]},ensure_ascii=False,indent=2))
