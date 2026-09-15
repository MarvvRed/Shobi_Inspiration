#!/usr/bin/env python3
from __future__ import annotations
import hashlib,io,json,time,urllib.request,urllib.error
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
TARGETS={'118-HAM':'27808','325-PECK':'31590','235-HOLL':'4307','1251-ROM':'21103'}
OUTDIR=ROOT/'database/fragrantica'/'social-cards'/'images'
OUT=ROOT/'database/audits/final-four-card-refetch.json'
URLS=(
 'https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{fid}.jpeg',
 'https://fimgs.net/mdimg/perfume-social-cards/en-social-{fid}.jpeg',
 'https://fimgs.net/mdimg/perfume/social.{fid}.jpg',
 'https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{fid}.jpg',
)
HEAD={'User-Agent':'Mozilla/5.0 (compatible; ShobiExactCardRecovery/2.0)','Accept':'image/avif,image/webp,image/jpeg,image/*,*/*;q=0.8','Referer':'https://www.fragrantica.com/'}
def fetch(url):
 req=urllib.request.Request(url,headers=HEAD)
 try:
  with urllib.request.urlopen(req,timeout=30) as r:data=r.read();ctype=r.headers.get('Content-Type','')
  try:
   with Image.open(io.BytesIO(data)) as im:size=list(im.size);fmt=im.format
  except Exception:return {'url':url,'status':'INVALID_IMAGE','bytes':len(data),'contentType':ctype}
  return {'url':url,'status':'OK','bytes':len(data),'contentType':ctype,'size':size,'format':fmt,'sha256':hashlib.sha256(data).hexdigest(),'data':data}
 except urllib.error.HTTPError as e:return {'url':url,'status':f'HTTP_{e.code}'}
 except Exception as e:return {'url':url,'status':type(e).__name__,'detail':str(e)}
rows=[]
for code,fid in TARGETS.items():
 attempts=[];best=None
 for tpl in URLS:
  r=fetch(tpl.format(fid=fid));data=r.pop('data',None);attempts.append(r)
  if data is not None:
   w,h=r['size']
   if best is None or (w*h)>(best['size'][0]*best['size'][1]): best={**r,'data':data}
  time.sleep(.08)
 saved=''
 if best:
  target=OUTDIR/f'refetched_{code}_{fid}.jpeg';target.write_bytes(best.pop('data'));saved=str(target.relative_to(ROOT))
 rows.append({'code':code,'fid':fid,'saved':saved,'best':best,'attempts':attempts})
OUT.write_text(json.dumps({'rows':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'code':r['code'],'fid':r['fid'],'saved':r['saved'],'best':r['best']} for r in rows],ensure_ascii=False,indent=2))
