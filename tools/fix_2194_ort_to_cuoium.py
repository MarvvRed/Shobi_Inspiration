#!/usr/bin/env python3
from __future__ import annotations
import json,urllib.request,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json';SITE=ROOT/'database/catalog/catalog_site.json';VALID=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json';IMAP=ROOT/'database/assets/perfumes'/'map.js';OUT=ROOT/'database/audits/fix-2194-ort-cuoium.json'
CODE='2194-ORT';OLD='119473';NEW='69923';URL='https://www.fragrantica.com/perfume/Orto-Parisi/Cuoium-69923.html';SHOBI='https://leparfum.com.gr/en/niche-perfumes?page=10'
def code(v):return str(v or '').strip().upper()
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'image/avif,image/*,*/*;q=0.8','Referer':'https://www.fragrantica.com/'})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read(),r.headers.get('Content-Type','')
db=json.loads(DB.read_text(encoding='utf-8-sig'));site=json.loads(SITE.read_text(encoding='utf-8-sig'));valid=json.loads(VALID.read_text(encoding='utf-8'))
row=next((r for r in db if code(r.get('code'))==CODE),None);srow=next((r for r in site if code(r.get('code'))==CODE),None)
if not row or not srow:raise SystemExit('2194-ORT missing')
if str(row.get('fragranticaId') or '')!=OLD:raise SystemExit(f'Unexpected current FID {row.get("fragranticaId")}')
# Require an already validated exact-Cuoium Social Card before changing identity.
src=next((x for x in valid if code(x.get('code'))==CODE and x.get('validated') is True and str(x.get('fragranticaId') or '')==NEW and x.get('card') and (ROOT/str(x.get('card'))).is_file()),None)
if not src:raise SystemExit('No validated exact 69923 Social Card for 2194-ORT')
notes=list(src.get('mainNotes') or [])
if not notes:raise SystemExit('Validated 69923 card has no Main Notes')
row['fragranticaId']=NEW;row['fragranticaUrl']=URL;row['fragranticaVerificationSource']=URL;row['identityStatus']='CONFIRMED';row['fragranticaVerificationReason']='SHOBI_2194_ORT_IS_CUOIUM_ORTO_PARISI_AND_EXACT_FRAGRANTICA_69923';row['fragranticaVerificationFragranticaId']=NEW;row['fragranticaSocialCardNotes']=notes;row['fragranticaSocialCardStatus']='VALIDATED_OCR';row['genderStatus']='';row['seasons']=[]
srow['fragranticaUrl']=URL;srow['seasons']=[]
# Ensure exact perfume image exists and map points to it.
target=ROOT/'database/assets/perfumes'/f'{NEW}.avif';img_status='EXISTS' if target.exists() and target.stat().st_size>=1000 else 'MISSING'
if img_status=='MISSING':
 try:
  data,ctype=fetch(f'https://fimgs.net/mdimg/perfume-thumbs/dark-375x500.{NEW}.avif')
  if len(data)>=1000 and (b'ftypavif' in data[:32] or b'ftypavis' in data[:32]):target.write_bytes(data);img_status='DOWNLOADED'
 except Exception as e:img_status=f'ERROR:{type(e).__name__}'
txt=IMAP.read_text(encoding='utf-8').strip();prefix='window.PERFUME_IMAGE_MAP=';mp=json.loads(txt[len(prefix):].rstrip(';'))
if target.exists() and target.stat().st_size>=1000:mp[CODE]=f'database/assets/perfumes/{NEW}.avif'
IMAP.write_text(prefix+json.dumps(mp,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
OUT.write_text(json.dumps({'code':CODE,'oldFid':OLD,'newFid':NEW,'url':URL,'shobiEvidence':SHOBI,'card':src.get('card'),'notes':notes,'imageStatus':img_status},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'code':CODE,'old':OLD,'new':NEW,'notes':len(notes),'image':img_status},ensure_ascii=False))
