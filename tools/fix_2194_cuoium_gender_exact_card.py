#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
from PIL import Image,ImageEnhance,ImageFilter,ImageOps
import pytesseract
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json';VALID=ROOT/'social-card-main-notes-validated.json';OUT=ROOT/'fix-2194-cuoium-gender.json';CODE='2194-ORT';FID='69923'
def code(v):return str(v or '').strip().upper()
def norm(t):return re.sub(r'\s+',' ',re.sub(r'[^a-z ]+',' ',str(t or '').lower().replace('\n',' '))).strip()
def parse(t):
 if (re.search(r'\bwom[ae]n\b',t) and re.search(r'\bm[ae]n\b',t)) or re.search(r'for\s+(?:women|woman).*?(?:and|&).*?(?:men|man)',t):return 'unisex'
 if re.search(r'\bfor\s+wom[ae]n\b',t):return 'female'
 if re.search(r'\bfor\s+m[ae]n\b',t):return 'male'
 return ''
def ocr_gender(im):
 w,h=im.size; boxes=[(0,0,w,int(h*.42)),(0,0,w,int(h*.52)),(0,0,w,int(h*.62))]; attempts=[]
 for box in boxes:
  crop=im.crop(box).convert('L')
  for contrast in (2.0,2.8,3.5):
   base=ImageOps.autocontrast(crop);base=ImageEnhance.Contrast(base).enhance(contrast)
   for thr in (None,150,175,200,220):
    x=base if thr is None else base.point(lambda p:255 if p>thr else 0)
    x=x.resize((x.width*4,x.height*4),Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
    for psm in (3,6,11,12):
     try:t=norm(pytesseract.image_to_string(x,config=f'--psm {psm}',lang='eng'))
     except Exception:continue
     if not t:continue
     g=parse(t);attempts.append({'psm':psm,'contrast':contrast,'threshold':thr,'text':t,'gender':g})
     if g:return g,attempts
 return '',attempts
rows=json.loads(DB.read_text(encoding='utf-8-sig'));row=next((r for r in rows if code(r.get('code'))==CODE),None)
if not row or str(row.get('fragranticaId') or '')!=FID:raise SystemExit('2194-ORT is not current Cuoium 69923')
valid=json.loads(VALID.read_text(encoding='utf-8'));src=next((x for x in valid if code(x.get('code'))==CODE and x.get('validated') is True and str(x.get('fragranticaId') or '')==FID and x.get('card')),None)
if not src or not (ROOT/str(src.get('card'))).is_file():raise SystemExit('No validated exact-FID Cuoium card')
with Image.open(ROOT/str(src.get('card'))) as im:g,attempts=ocr_gender(im)
if g!='unisex':raise SystemExit(f'Exact Cuoium card did not prove unisex; got {g}')
row['gender']='Unisex';row['genderAffinity']='unisex';row['genderStatus']='VALIDATED_SOCIAL_CARD';row['genderVerificationSource']=str(src.get('card'));row['genderVerificationFragranticaId']=FID
DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
OUT.write_text(json.dumps({'code':CODE,'fid':FID,'card':src.get('card'),'ocrGender':g,'successfulAttempt':next((a for a in attempts if a['gender']==g),None),'attemptCount':len(attempts)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'code':CODE,'fid':FID,'ocrGender':g,'attempts':len(attempts)},ensure_ascii=False))
