#!/usr/bin/env python3
from __future__ import annotations
import json,re,unicodedata
from pathlib import Path
from PIL import Image,ImageEnhance,ImageOps
import pytesseract
from pytesseract import Output

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json';SITE=ROOT/'database/catalog/catalog_site.json';CARD_DIR=ROOT/'database/fragrantica'/'social-cards'/'images';PAT=ROOT/'database/audits/validated-note-slot-patterns.json';OUT=ROOT/'database/audits/existing-notes-current-card-fast-proof.json'
CROP=(48,738,448,1097);BANDS=[(145,232),(288,359)];COLS=[(0,133),(133,267),(267,400)]
def code(v):return str(v or '').strip().upper()
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return ' '.join(re.findall(r'[a-z0-9]+',s))
STOP={'and','or','of','the','oil','notes','note'}
def toks(s):return [x for x in norm(s).split() if x not in STOP and len(x)>1]
def proves(note,text):
 # OCR sometimes joins otherwise exact words (for example ``Bagasde``).
 # Accept only a complete normalized label; this never turns a partial label
 # (such as ``Fig`` versus ``Fig Leaf``) into a match.
 compact_note=norm(note).replace(' ','');compact_text=norm(text).replace(' ','')
 if len(compact_note)>=5 and compact_note in compact_text:return True
 nt=toks(note);tt=norm(text).split()
 if not nt:return False
 # Allow conservative OCR prefix matching for tokens >=5 chars; short tokens must be exact.
 for n in nt:
  if n in tt:continue
  if len(n)>=5 and any((t.startswith(n[:max(4,len(n)-1)]) or n.startswith(t[:max(4,len(t)-1)])) for t in tt if len(t)>=4):continue
  return False
 return True

db=json.loads(DB.read_text(encoding='utf-8-sig'));site=json.loads(SITE.read_text(encoding='utf-8-sig'));patterns=json.loads(PAT.read_text(encoding='utf-8'))
bycount={}
for k,items in patterns.get('byCount',{}).items():
 bycount[int(k)]=[tuple(int(v) for v in x.get('slots') or []) for x in items if x.get('slots')]
rows=[]
for r,s in zip(db,site):
 if str(s.get('validationStatus') or '').lower()!='yellow' or (s.get('validationChecks') or {}).get('socialCard',False):continue
 notes=list(r.get('fragranticaSocialCardNotes') or []);fid=str(r.get('fragranticaId') or '');c=code(r.get('code'))
 if not notes or not fid:continue
 matches=sorted(CARD_DIR.glob(f'*_{c}_{fid}.jpeg'))+sorted(CARD_DIR.glob(f'*_{c}_{fid}.jpg'))
 if not matches:continue
 p=matches[0];card=str(p.relative_to(ROOT))
 if not p.is_file():continue
 with Image.open(p) as im:
  sx=im.width/1200;sy=im.height/1200;x1,y1,x2,y2=CROP;panel=im.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))).resize((400,359)).convert('L');panel=ImageOps.autocontrast(panel);panel=ImageEnhance.Contrast(panel).enhance(2.3);panel=panel.resize((800,718),Image.Resampling.LANCZOS)
  data=pytesseract.image_to_data(panel,config='--psm 6',lang='eng',output_type=Output.DICT)
 slots={i:[] for i in range(1,7)}
 for i,txt in enumerate(data.get('text',[])):
  txt=' '.join(str(txt).split())
  if not txt:continue
  try:conf=float(data['conf'][i])
  except:conf=-1
  if conf<15:continue
  x=(int(data['left'][i])+int(data['width'][i])/2)/2;y=(int(data['top'][i])+int(data['height'][i])/2)/2
  for sl in range(1,7):
   ry,cx=divmod(sl-1,3);xa,xb=COLS[cx];ya,yb=BANDS[ry]
   if xa<=x<xb and ya<=y<yb:slots[sl].append(txt);break
 st={k:' '.join(v) for k,v in slots.items()}
 passing=[]
 for pat in bycount.get(len(notes),[]):
  if len(pat)!=len(notes):continue
  if all(proves(n,st.get(sl,'')) for n,sl in zip(notes,pat)):passing.append(pat)
 rows.append({'code':c,'fid':fid,'card':card,'notes':notes,'slotText':st,'passingPatterns':[list(x) for x in passing],'uniqueProof':len(passing)==1})
out={'tested':len(rows),'uniqueProof':sum(r['uniqueProof'] for r in rows),'ambiguousOrFail':sum(not r['uniqueProof'] for r in rows),'rows':rows}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:out[k] for k in ('tested','uniqueProof','ambiguousOrFail')},indent=2))
