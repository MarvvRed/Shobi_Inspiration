#!/usr/bin/env python3
from __future__ import annotations
import json,re,unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from PIL import Image,ImageEnhance,ImageFilter,ImageOps
import pytesseract

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json';SITE=ROOT/'catalog_site.json';VALID=ROOT/'social-card-main-notes-validated.json';LEX=ROOT/'fragrantica-note-lexicon.txt';PAT=ROOT/'validated-note-slot-patterns.json';FETCH=ROOT/'current-fid-card-fetch-report.json';OUT=ROOT/'current-fid-card-multipass-validation.json'
CROP_1200=(48,738,448,1097);BANDS=[(145,232),(288,359)];COLS=[(0,133),(133,267),(267,400)]

def code(v):return str(v or '').strip().upper()
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower().replace('’',"'")
 return ' '.join(re.findall(r'[a-z0-9]+',s))
def sim(a,b):
 a,b=norm(a),norm(b)
 if not a or not b:return 0.0
 if a==b:return 1.0
 r=SequenceMatcher(None,a,b).ratio()
 if len(b)>=4 and b in a:r=max(r,.945)
 if len(a)>=4 and a in b:r=max(r,.925)
 return r
def best(text,names):
 ranked=sorted(((sim(text,n),n) for n in names),reverse=True)
 if not ranked:return None,0,0
 bs,bn=ranked[0];ss=ranked[1][0] if len(ranked)>1 else 0;margin=bs-ss;L=len(norm(text).replace(' ',''))
 ok=(L<=3 and bs>=.97 and margin>=.12) or (L>3 and ((bs>=.94 and margin>=.025) or (bs>=.89 and margin>=.10)))
 return (bn if ok else None),bs,margin
def prep(crop,scale,contrast,thr=None,inv=False):
 im=ImageOps.autocontrast(crop.convert('L'));im=ImageEnhance.Contrast(im).enhance(contrast)
 if thr is not None:im=im.point(lambda p:255 if p>thr else 0)
 if inv:im=ImageOps.invert(im)
 return im.resize((max(1,im.width*scale),max(1,im.height*scale)),Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
def read_slot(crop,names):
 attempts=[]
 for scale,contrast,thr,inv in [(4,2.0,None,False),(5,2.7,None,False),(5,2.4,175,False),(5,2.4,205,False),(5,2.2,185,True)]:
  im=prep(crop,scale,contrast,thr,inv)
  for psm in (6,7,11,13):
   try:raw=' '.join(pytesseract.image_to_string(im,config=f'--psm {psm}',lang='eng').split())
   except Exception:continue
   if not raw:continue
   n,sc,margin=best(raw,names);attempts.append({'raw':raw,'match':n,'score':round(sc,3),'margin':round(margin,3),'psm':psm})
 votes=defaultdict(list)
 for a in attempts:
  if a['match']:votes[a['match']].append(a)
 if not votes:return None,None,attempts
 name,arr=max(votes.items(),key=lambda kv:(len(kv[1]),max(a['score'] for a in kv[1])))
 strongest=max(arr,key=lambda a:a['score'])
 # Require independent agreement or near-perfect OCR.
 if len(arr)>=2 or strongest['score']>=.985:return name,strongest,attempts
 return None,None,attempts

db=json.loads(DB.read_text(encoding='utf-8-sig'));site=json.loads(SITE.read_text(encoding='utf-8-sig'));valid_list=json.loads(VALID.read_text(encoding='utf-8'));valid_by={code(x.get('code')):x for x in valid_list};fetch=json.loads(FETCH.read_text(encoding='utf-8'));names=[x.strip() for x in LEX.read_text(encoding='utf-8').splitlines() if x.strip()];patterns=json.loads(PAT.read_text(encoding='utf-8'))
allowed=set()
for x in patterns.get('allPatterns',[]):
 p=tuple(int(v) for v in x.get('slots') or []);count=int(x.get('count') or 0)
 # For rare 2/3 note layouts require pattern seen at least once; for >=4 require normal observed layout.
 if p and count>=1:allowed.add(p)
byrow={code(r.get('code')):(r,s) for r,s in zip(db,site)}
accepted=[];rejected=[]
for fr in fetch.get('rows',[]):
 if fr.get('status') not in {'RECOVERED','EXISTS'}:continue
 c=code(fr.get('code'));fid=str(fr.get('fid') or '');pair=byrow.get(c)
 if not pair:continue
 row,srow=pair
 if str(srow.get('validationStatus') or '').lower()!='yellow' or (srow.get('validationChecks') or {}).get('socialCard',False):continue
 if str(row.get('fragranticaId') or '')!=fid:continue
 card=str(fr.get('card') or '');path=ROOT/card
 if not path.is_file():continue
 try:im=Image.open(path)
 except Exception:continue
 with im:
  sx=im.width/1200;sy=im.height/1200;x1,y1,x2,y2=CROP_1200
  panel=im.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))).resize((400,359))
  found=[];diag=[]
  for sl in range(1,7):
   ry,cx=divmod(sl-1,3);xa,xb=COLS[cx];ya,yb=BANDS[ry];crop=panel.crop((xa+2,ya,xb-2,yb))
   note,strong,attempts=read_slot(crop,names);diag.append({'slot':sl,'note':note,'strongest':strong,'attempts':attempts[:10]})
   if note:found.append((sl,note,strong))
 slots=tuple(sl for sl,_,_ in found);notes=[n for _,n,_ in found]
 # Reject repeated identical note caused by OCR spillover, and only accept known validated layouts.
 valid_layout=bool(notes and slots in allowed and len(notes)==len(set((sl,n) for sl,n,_ in found)))
 if valid_layout:
  old=list(row.get('fragranticaSocialCardNotes') or [])
  row['fragranticaSocialCardNotes']=notes;row['fragranticaSocialCardStatus']='VALIDATED_OCR'
  valid_by[c]={'code':c,'fragranticaId':int(fid) if fid.isdigit() else fid,'card':card,'validated':True,'mainNotes':notes,'rawSlots':[{'slot':sl,'name':n,'ocrConfidence':None} for sl,n,_ in found],'validatedSlots':[{'slot':sl,'name':n,'raw':'CURRENT_FID_MULTIPASS_OCR','matchScore':(st or {}).get('score'),'margin':(st or {}).get('margin')} for sl,n,st in found],'failures':[],'reasons':[],'validationMethod':'CURRENT_FID_MULTIPASS_OCR'}
  accepted.append({'code':c,'fid':fid,'card':card,'slots':list(slots),'oldNotes':old,'notes':notes,'diagnostics':diag})
 else:rejected.append({'code':c,'fid':fid,'card':card,'slots':list(slots),'notes':notes,'knownLayout':slots in allowed,'diagnostics':diag})
seen=set();rebuilt=[]
for item in valid_list:
 c=code(item.get('code'))
 if c in valid_by and c not in seen:rebuilt.append(valid_by[c]);seen.add(c)
for c,item in valid_by.items():
 if c not in seen:rebuilt.append(item);seen.add(c)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');VALID.write_text(json.dumps(rebuilt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');OUT.write_text(json.dumps({'accepted':len(accepted),'rejected':len(rejected),'rows':accepted,'rejectedRows':rejected},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('accepted',len(accepted),'rejected',len(rejected))
