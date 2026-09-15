#!/usr/bin/env python3
from __future__ import annotations
import io,json,urllib.request
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; IMAP=ROOT/'database/assets/perfumes'/'map.js'; OUT=ROOT/'database/audits/dior-addict-image-recovery.json'
CODE='521-DRC'; FID='215'; PAGE='https://www.fragrantica.com/perfume/Christian-Dior/Dior-Addict-215.html'
CANDIDATES=[f'https://fimgs.net/mdimg/perfume-thumbs/dark-375x500.{FID}.avif',f'https://fimgs.net/mdimg/perfume/social.{FID}.jpg',f'https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{FID}.jpeg']
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'image/avif,image/jpeg,image/*,*/*;q=0.8','Referer':'https://www.fragrantica.com/'})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read(),r.headers.get('Content-Type','')
rows=json.loads(DB.read_text(encoding='utf-8-sig')); row=next((r for r in rows if str(r.get('code') or '').strip().upper()==CODE),None)
if not row: raise SystemExit('Missing Dior Addict row')
if str(row.get('fragranticaId') or '')!=FID: raise SystemExit(f'Unexpected FID {row.get("fragranticaId")}')
url=str(row.get('fragranticaUrl') or '')
if FID not in url: raise SystemExit(f'Unexpected URL {url}')
target=ROOT/'database/assets/perfumes'/f'{FID}.avif'; used=''; attempts=[]
for u in CANDIDATES:
 try:data,ctype=fetch(u)
 except Exception as e:
  attempts.append({'url':u,'status':type(e).__name__});continue
 try:
  if b'ftypavif' in data[:32] or b'ftypavis' in data[:32]:
   target.write_bytes(data)
  else:
   im=Image.open(io.BytesIO(data)).convert('RGB'); im.save(target,'AVIF',quality=88)
  if target.stat().st_size<1000: raise ValueError('too small')
  used=u;attempts.append({'url':u,'status':'RECOVERED','contentType':ctype,'bytes':target.stat().st_size});break
 except Exception as e: attempts.append({'url':u,'status':'INVALID','detail':str(e)})
if not used: raise SystemExit('No exact-FID image candidate recovered')
txt=IMAP.read_text(encoding='utf-8').strip(); prefix='window.PERFUME_IMAGE_MAP='; mp=json.loads(txt[len(prefix):].rstrip(';'))
mp[CODE]=f'database/assets/perfumes/{FID}.avif'; IMAP.write_text(prefix+json.dumps(mp,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
OUT.write_text(json.dumps({'code':CODE,'fid':FID,'page':PAGE,'source':used,'target':f'database/assets/perfumes/{FID}.avif','attempts':attempts},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'code':CODE,'fid':FID,'source':used},ensure_ascii=False))
