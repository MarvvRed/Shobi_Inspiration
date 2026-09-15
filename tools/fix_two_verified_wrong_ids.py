#!/usr/bin/env python3
from __future__ import annotations
import json,urllib.request,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; SITE=ROOT/'database/catalog/catalog_site.json'; CARD=ROOT/'database/fragrantica'/'social-cards'/'images'; IMAP=ROOT/'database/assets/perfumes'/'map.js'; OUT=ROOT/'database/audits/two-verified-id-corrections.json'
FIX={
 '1751-GUL':{'old':'12088','fid':'3681','url':'https://www.fragrantica.com/perfume/Jean-Paul-Gaultier/Ma-Dame-3681.html','brand':'Jean Paul Gaultier','name':'Madame'},
 '928-TRU':{'old':'93471','fid':'16241','url':'https://www.fragrantica.com/perfume/Trussardi/Trussardi-Delicate-Rose-16241.html','brand':'Trussardi','name':'Delicate Rose'},
}
def code(v):return str(v or '').strip().upper()
def fetch(url,accept):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':accept,'Referer':'https://www.fragrantica.com/'})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read()
db=json.loads(DB.read_text(encoding='utf-8-sig'));site=json.loads(SITE.read_text(encoding='utf-8-sig'))
prefix='window.PERFUME_IMAGE_MAP=';txt=IMAP.read_text(encoding='utf-8').strip();imap=json.loads(txt[len(prefix):].rstrip(';'))
changes=[]
for r,s in zip(db,site):
 c=code(r.get('code'));f=FIX.get(c)
 if not f:continue
 old=str(r.get('fragranticaId') or '').strip()
 if old!=f['old']:raise SystemExit(f'Unexpected old FID {c}: {old}')
 # External direct-page verification is documented in source URL. Fetch exact-ID media only.
 card_url=f"https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{f['fid']}.jpeg"
 image_url=f"https://fimgs.net/mdimg/perfume-thumbs/dark-375x500.{f['fid']}.avif"
 card_data=fetch(card_url,'image/jpeg,image/*,*/*;q=0.8')
 if not (card_data.startswith(b'\xff\xd8') and card_data.endswith(b'\xff\xd9')):raise SystemExit(f'Invalid card {c}')
 card_path=CARD/f"verified_{c}_{f['fid']}.jpeg";card_path.write_bytes(card_data)
 image_ok=False;image_path=ROOT/'database/assets/perfumes'/f"{f['fid']}.avif"
 try:
  data=fetch(image_url,'image/avif,image/*,*/*;q=0.8')
  if len(data)>=1000 and (b'ftypavif' in data[:32] or b'ftypavis' in data[:32]):image_path.write_bytes(data);image_ok=True
 except Exception:pass
 r['fragranticaId']=f['fid'];r['fragranticaUrl']=f['url'];r['fragranticaVerificationSource']=f['url'];r['identityStatus']='CONFIRMED'
 s['fragranticaUrl']=f['url']
 if image_ok:imap[c]=f"database/assets/perfumes/{f['fid']}.avif"
 # Old notes/gender/season evidence belonged to old ID, so explicitly clear derived values until rebuilt from new card.
 r['fragranticaSocialCardNotes']=[];r['fragranticaSocialCardStatus']='';r['seasons']=[];s['seasons']=[];r['genderStatus']=''
 changes.append({'code':c,'oldFid':old,'newFid':f['fid'],'url':f['url'],'card':str(card_path.relative_to(ROOT)),'image':image_ok})
 time.sleep(.1)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');IMAP.write_text(prefix+json.dumps(imap,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8');OUT.write_text(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2))
