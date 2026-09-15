#!/usr/bin/env python3
from __future__ import annotations
import json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json';SITE=ROOT/'database/catalog/catalog_site.json';VALID=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json';PROOF=ROOT/'database/audits/existing-notes-current-card-fast-proof.json';IMAP=ROOT/'database/assets/perfumes'/'map.js';OUT=ROOT/'database/audits/fix-bvlgari-1036-1037.json'
def code(v):return str(v or '').strip().upper()
def fetch_img(fid):
 u=f'https://fimgs.net/mdimg/perfume-thumbs/dark-375x500.{fid}.avif';req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'image/avif,image/*,*/*;q=0.8','Referer':'https://www.fragrantica.com/'})
 try:
  with urllib.request.urlopen(req,timeout=30) as r:data=r.read()
  if len(data)>=1000 and (b'ftypavif' in data[:32] or b'ftypavis' in data[:32]):
   p=ROOT/'database/assets/perfumes'/f'{fid}.avif';p.write_bytes(data);return str(p.relative_to(ROOT))
 except Exception:pass
 return ''
db=json.loads(DB.read_text(encoding='utf-8-sig'));site=json.loads(SITE.read_text(encoding='utf-8-sig'));valid=json.loads(VALID.read_text(encoding='utf-8'));proof=json.loads(PROOF.read_text(encoding='utf-8'))
bydb={code(x.get('code')):x for x in db};bys={code(x.get('code')):x for x in site};byv={code(x.get('code')):x for x in valid}
# 1037 is Bvlgari Man; Shobi names it explicitly. Exact Fragrantica identity is FID 9403.
r=bydb['1037-BLG'];s=bys['1037-BLG']
if str(r.get('fragranticaId') or '')!='148':raise SystemExit(f'1037 FID drift {r.get("fragranticaId")}')
src=next((x for x in valid if code(x.get('code'))=='1037-BLG' and x.get('validated') is True and str(x.get('fragranticaId') or '')=='9403' and x.get('card') and (ROOT/str(x.get('card'))).is_file()),None)
if not src:raise SystemExit('No validated exact 9403 card for 1037-BLG')
notes1037=list(src.get('mainNotes') or [])
if not notes1037:raise SystemExit('9403 validated card has no notes')
r['fragranticaId']='9403';r['fragranticaUrl']='https://www.fragrantica.com/perfume/Bvlgari/Bvlgari-Man-9403.html';r['fragranticaVerificationSource']=r['fragranticaUrl'];r['fragranticaVerificationReason']='SHOBI_1037_IS_BVLGARI_MAN_AND_EXACT_FRAGRANTICA_9403';r['fragranticaVerificationFragranticaId']='9403';r['identityStatus']='CONFIRMED';r['fragranticaSocialCardNotes']=notes1037;r['fragranticaSocialCardStatus']='VALIDATED_OCR';r['genderStatus']='';r['seasons']=[];s['fragranticaUrl']=r['fragranticaUrl'];s['seasons']=[]
# 1036 is BLV Pour Homme FID 148. Require exact-card OCR report to prove all six current main-note slots.
r2=bydb['1036-BLG'];s2=bys['1036-BLG']
if str(r2.get('fragranticaId') or '')!='148':raise SystemExit('1036 FID drift')
p=next((x for x in proof.get('rows',[]) if code(x.get('code'))=='1036-BLG' and str(x.get('fid') or '')=='148'),None)
expected=['Ginger','Cardamom','Tobacco Blossom','Sandalwood','Juniper','Galanga']
if not p or [p.get('slotText',{}).get(str(i),'') for i in range(1,7)]!=expected:raise SystemExit('1036 exact-card OCR no longer proves expected six notes')
card=str(p.get('card') or '')
if not card or not (ROOT/card).is_file():raise SystemExit('1036 exact card missing')
r2['fragranticaSocialCardNotes']=expected;r2['fragranticaSocialCardStatus']='VALIDATED_OCR'
byv['1036-BLG']={'code':'1036-BLG','fragranticaId':148,'card':card,'validated':True,'mainNotes':expected,'rawSlots':[{'slot':i,'name':n,'ocrConfidence':None} for i,n in enumerate(expected,1)],'validatedSlots':[{'slot':i,'name':n,'raw':'CURRENT_FID_FAST_EXACT_OCR','matchScore':1.0,'margin':None} for i,n in enumerate(expected,1)],'failures':[],'reasons':[],'validationMethod':'CURRENT_FID_FAST_EXACT_OCR'}
# Image map for 1037 exact FID.
txt=IMAP.read_text(encoding='utf-8').strip();prefix='window.PERFUME_IMAGE_MAP=';mp=json.loads(txt[len(prefix):].rstrip(';'));p9403=ROOT/'database/assets/perfumes'/'9403.avif'
if p9403.exists() and p9403.stat().st_size>=1000:mp['1037-BLG']='database/assets/perfumes/9403.avif'
else:
 im=fetch_img('9403')
 if im:mp['1037-BLG']=im
IMAP.write_text(prefix+json.dumps(mp,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
seen=set();reb=[]
for x in valid:
 c=code(x.get('code'));reb.append(byv.get(c,x));seen.add(c)
for c,x in byv.items():
 if c not in seen:reb.append(x)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');VALID.write_text(json.dumps(reb,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
OUT.write_text(json.dumps({'1037':{'oldFid':'148','newFid':'9403','card':src.get('card'),'notes':notes1037},'1036':{'fid':'148','card':card,'notes':expected}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'1037':'9403','1037Notes':len(notes1037),'1036Notes':expected},ensure_ascii=False))
