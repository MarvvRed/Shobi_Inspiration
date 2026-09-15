#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
from PIL import Image,ImageEnhance,ImageFilter,ImageOps
import pytesseract
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; VALID=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json'; GS=ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv'; OUT=ROOT/'database/audits/miu-miu-leau-bleue-gender-fix.json'
CODE='828-MIY';FID='42720';WEB='https://www.fragrantica.com/perfume/Miu-Miu/Miu-Miu-L-Eau-Bleue-42720.html'
def code(v):return str(v or '').strip().upper()
def normocr(t):return re.sub(r'\s+',' ',re.sub(r'[^a-z ]+',' ',t.lower().replace('\n',' '))).strip()
def parse(t):
 if re.search(r'(?:for )?(?:women|woman)\s+(?:and|ancl|anci)\s+(?:men|man)',t):return 'unisex'
 if re.search(r'\bfor\s+wom[ae]n\b',t):return 'female'
 if re.search(r'\bfor\s+m[ae]n\b',t):return 'male'
 return ''
def read_gender(im):
 w,h=im.size;crop=im.crop((int(.005*w),int(.005*h),int(.995*w),int(.340*h))).convert('L');attempts=[]
 for thr in (None,170,205):
  x=ImageOps.autocontrast(crop);x=ImageEnhance.Contrast(x).enhance(2.7);x=x.resize((x.width*3,x.height*3),Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
  if thr is not None:x=x.point(lambda p:255 if p>thr else 0)
  for psm in (6,11,12):
   t=normocr(pytesseract.image_to_string(x,config=f'--psm {psm}',lang='eng'));attempts.append(t);g=parse(t)
   if g:return g,' | '.join(dict.fromkeys(a for a in attempts if a))
 return '',' | '.join(dict.fromkeys(a for a in attempts if a))
rows=json.loads(DB.read_text(encoding='utf-8-sig')); row=next((r for r in rows if code(r.get('code'))==CODE),None)
if not row or str(row.get('fragranticaId') or '')!=FID:raise SystemExit('Miu Miu row/FID drift')
valid=json.loads(VALID.read_text(encoding='utf-8')); src=next((x for x in valid if code(x.get('code'))==CODE and x.get('validated') is True and str(x.get('fragranticaId') or '')==FID),None)
if not src:raise SystemExit('No validated exact-FID Social Card')
card=ROOT/str(src.get('card') or '')
if not card.is_file():raise SystemExit('Exact card missing')
with Image.open(card) as im:g,ocr=read_gender(im)
if g!='female':raise SystemExit(f'Exact-card OCR did not prove female: {g} / {ocr}')
old={'gender':row.get('gender'),'genderAffinity':row.get('genderAffinity'),'genderStatus':row.get('genderStatus')}
row['gender']='Female';row['genderAffinity']='feminine';row['genderStatus']='VALIDATED_SOCIAL_CARD';row['genderVerificationSource']=str(src.get('card'));row['genderVerificationFragranticaId']=FID;row['genderVerificationWebCorroboration']=WEB
DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
OUT.write_text(json.dumps({'code':CODE,'fid':FID,'card':str(src.get('card')),'ocrGender':g,'ocrText':ocr,'webCorroboration':WEB,'old':old,'new':{'gender':'Female','genderAffinity':'feminine','genderStatus':'VALIDATED_SOCIAL_CARD'}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'code':CODE,'fid':FID,'ocrGender':g},ensure_ascii=False))
