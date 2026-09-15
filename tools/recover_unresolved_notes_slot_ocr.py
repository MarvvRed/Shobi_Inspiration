#!/usr/bin/env python3
from __future__ import annotations
import json,re,unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from PIL import Image,ImageEnhance,ImageFilter,ImageOps
import pytesseract

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; SITE=ROOT/'database/catalog/catalog_site.json'; RAW=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes.json'; VALID=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json'; LEX=ROOT/'database/audits/fragrantica-note-lexicon.txt'; OUT=ROOT/'database/audits/slot-ocr-note-recovery.json'
CROP_1200=(48,738,448,1097); LABEL_BANDS=[(145,232),(288,359)]; COL_RANGES=[(0,133),(133,267),(267,400)]

def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower().replace('’',"'")
 return ' '.join(re.findall(r'[a-z0-9]+',s))
def score(a,b):
 a,b=norm(a),norm(b)
 if not a or not b:return 0.0
 if a==b:return 1.0
 r=SequenceMatcher(None,a,b).ratio()
 if len(b)>=4 and b in a:r=max(r,.94)
 if len(a)>=4 and a in b:r=max(r,.92)
 return r

def best_match(text,names):
 ranked=sorted(((score(text,n),n) for n in names),reverse=True)
 if not ranked:return None,0,0
 bs,bn=ranked[0]; ss=ranked[1][0] if len(ranked)>1 else 0; margin=bs-ss
 L=len(norm(text).replace(' ',''))
 # Stricter than the normal validator because this pass mutates evidence.
 ok=(L<=3 and bs>=.96 and margin>=.10) or (L>3 and ((bs>=.93 and margin>=.02) or (bs>=.88 and margin>=.08)))
 return (bn if ok else None),bs,margin

def code(v):return str(v or '').strip().upper()
def preprocess(crop,scale,contrast,threshold=None,invert=False):
 im=crop.convert('L'); im=ImageOps.autocontrast(im); im=ImageEnhance.Contrast(im).enhance(contrast)
 if threshold is not None:im=im.point(lambda p:255 if p>threshold else 0)
 if invert:im=ImageOps.invert(im)
 im=im.resize((max(1,im.width*scale),max(1,im.height*scale)),Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
 return im

def ocr_slot(crop,names):
 attempts=[]
 specs=[(4,2.0,None,False),(5,2.7,None,False),(5,2.4,175,False),(5,2.4,205,False),(5,2.2,185,True)]
 for scale,contrast,thr,inv in specs:
  im=preprocess(crop,scale,contrast,thr,inv)
  for psm in (6,7,11,13):
   try:raw=pytesseract.image_to_string(im,config=f'--psm {psm}',lang='eng').strip()
   except Exception:continue
   text=' '.join(raw.split())
   if not text:continue
   n,sc,margin=best_match(text,names); attempts.append({'raw':text,'match':n,'score':round(sc,3),'margin':round(margin,3),'psm':psm})
 # Require either an extremely strong single match or agreement from >=2 independent attempts.
 valid=[a for a in attempts if a['match']]
 counts={}
 for a in valid:counts[a['match']]=counts.get(a['match'],0)+1
 agreed=sorted(counts.items(),key=lambda kv:kv[1],reverse=True)
 if agreed:
  name,count=agreed[0]; strongest=max((a for a in valid if a['match']==name),key=lambda x:x['score'])
  if count>=2 or strongest['score']>=.975:return name,strongest,attempts
 return None,None,attempts

db=json.loads(DB.read_text(encoding='utf-8-sig')); site=json.loads(SITE.read_text(encoding='utf-8-sig'))
raw_by={code(x.get('code')):x for x in json.loads(RAW.read_text(encoding='utf-8'))}; valid_list=json.loads(VALID.read_text(encoding='utf-8')); valid_by={code(x.get('code')):x for x in valid_list}
names=[x.strip() for x in LEX.read_text(encoding='utf-8').splitlines() if x.strip()]
recovered=[]; diagnostics=[]
for row,srow in zip(db,site):
 if str(srow.get('validationStatus') or '').lower()!='yellow' or (srow.get('validationChecks') or {}).get('socialCard',False):continue
 c=code(row.get('code')); fid=str(row.get('fragranticaId') or '').strip(); raw=raw_by.get(c) or {}; vr=valid_by.get(c) or {}
 # Only retry unresolved existing RAW evidence of the exact current FID.
 if not fid or str(raw.get('fragranticaId') or '')!=fid:continue
 card=str(raw.get('card') or ''); slots=sorted(raw.get('slots') or [],key=lambda x:int(x.get('slot') or 999))
 if not card or not (ROOT/card).is_file() or not slots:continue
 # Do not override already validated evidence.
 if vr.get('validated') is True:continue
 with Image.open(ROOT/card) as im:
  sx=im.width/1200; sy=im.height/1200; x1,y1,x2,y2=CROP_1200
  panel=im.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))).resize((400,359))
  outnotes=[]; slotdiag=[]; ok=True
  expected_slots=[int(x.get('slot') or 0) for x in slots if 1<=int(x.get('slot') or 0)<=6]
  for sl in expected_slots:
   idx=sl-1; ry,cx=divmod(idx,3); xa,xb=COL_RANGES[cx]; ya,yb=LABEL_BANDS[ry]
   # inset minimally so neighboring columns/labels cannot leak in
   crop=panel.crop((xa+2,ya,max(xa+3,xb-2),yb))
   note,strong,attempts=ocr_slot(crop,names); slotdiag.append({'slot':sl,'note':note,'strongest':strong,'attempts':attempts[:12]})
   if not note:ok=False;break
   outnotes.append(note)
 if ok and outnotes and len(outnotes)==len(expected_slots):
  old=list(row.get('fragranticaSocialCardNotes') or [])
  row['fragranticaSocialCardNotes']=outnotes
  row['fragranticaSocialCardStatus']='VALIDATED_OCR'
  valid_by[c]={'code':c,'fragranticaId':int(fid) if fid.isdigit() else fid,'card':card,'validated':True,'mainNotes':outnotes,'rawSlots':slots,'validatedSlots':[{'slot':sl,'name':n,'raw':'MULTIPASS_SLOT_OCR'} for sl,n in zip(expected_slots,outnotes)],'failures':[],'reasons':[],'validationMethod':'MULTIPASS_SLOT_OCR'}
  recovered.append({'code':c,'fid':fid,'card':card,'oldNotes':old,'notes':outnotes,'slots':slotdiag})
 else:diagnostics.append({'code':c,'fid':fid,'card':card,'expectedSlots':expected_slots,'slots':slotdiag})
# rebuild validated list preserving order then append new codes
seen=set(); rebuilt=[]
for item in valid_list:
 c=code(item.get('code'))
 if c in valid_by and c not in seen:rebuilt.append(valid_by[c]);seen.add(c)
for c,item in valid_by.items():
 if c not in seen:rebuilt.append(item);seen.add(c)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); VALID.write_text(json.dumps(rebuilt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
OUT.write_text(json.dumps({'recovered':len(recovered),'rows':recovered,'unresolvedDiagnostics':diagnostics},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('recovered',len(recovered),'unresolved',len(diagnostics))
