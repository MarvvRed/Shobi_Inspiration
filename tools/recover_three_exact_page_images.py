#!/usr/bin/env python3
from __future__ import annotations
import io,json,re,urllib.parse,urllib.request
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
IMAP=ROOT/'database/assets/perfumes'/'map.js';OUT=ROOT/'database/audits/three-exact-page-image-recovery.json'
TARGETS={
 '2265-KAY':('85186','https://www.fragrantica.com/perfume/Kayali-Fragrances/Oudgasm-Rose-Oud-16-Eau-de-Parfum-Intense-85186.html'),
 '716-ISS':('6432','https://www.fragrantica.com/perfume/Issey-Miyake/A-Scent-by-Issey-Miyake-6432.html'),
 '1165-HUG':('569','https://www.fragrantica.com/perfume/Hugo-Boss/Hugo-Energise-569.html'),
}
HEAD={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36','Accept':'text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8','Accept-Language':'en-US,en;q=0.9'}
def get(url,referer=None):
 h=dict(HEAD)
 if referer:h['Referer']=referer
 req=urllib.request.Request(url,headers=h)
 with urllib.request.urlopen(req,timeout=30) as r:return r.read(),r.headers.get('Content-Type','')
def candidates(html):
 text=html.decode('utf-8','ignore');out=[]
 pats=[r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)',r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image["\']',r'"image"\s*:\s*"(https?:[^"\\]+(?:jpg|jpeg|png|webp|avif)[^"\\]*)"',r'(https?://[^"\'<> ]*fimgs\.net/[^"\'<> ]*\.(?:jpg|jpeg|png|webp|avif))']
 for p in pats:
  for m in re.findall(p,text,re.I):
   u=m.replace('\\/','/').replace('&amp;','&')
   if u not in out:out.append(u)
 return out
prefix='window.PERFUME_IMAGE_MAP=';txt=IMAP.read_text(encoding='utf-8').strip();imap=json.loads(txt[len(prefix):].rstrip(';'));rows=[]
for code,(fid,page) in TARGETS.items():
 result={'code':code,'fid':fid,'page':page,'status':'UNRESOLVED','candidates':[]}
 try:html,_=get(page)
 except Exception as e:result['error']='page '+repr(e);rows.append(result);continue
 for u in candidates(html):
  result['candidates'].append(u)
  # Reject avatars/social-card graphics; prefer URLs whose basename or query points to FID or perfume image path.
  low=u.lower()
  if any(x in low for x in ('avatar','member','user','social-card')):continue
  try:data,ctype=get(u,page)
  except Exception:continue
  if len(data)<1500 or not ctype.lower().startswith('image/'):continue
  try:
   im=Image.open(io.BytesIO(data));im.load()
   if im.width<80 or im.height<100:continue
   if im.mode not in ('RGB','RGBA'):im=im.convert('RGB')
   if im.mode=='RGBA':
    bg=Image.new('RGB',im.size,'white');bg.paste(im,mask=im.getchannel('A'));im=bg
   target=ROOT/'database/assets/perfumes'/f'{fid}.avif'
   try:im.save(target,'AVIF',quality=90)
   except Exception:
    # Pillow build may lack AVIF encoder; install pillow-avif-plugin in workflow and import there.
    import pillow_avif  # noqa
    im.save(target,'AVIF',quality=90)
   if target.stat().st_size<1000:continue
   imap[code]=f'database/assets/perfumes/{fid}.avif';result.update({'status':'RECOVERED','source':u,'width':im.width,'height':im.height});break
  except Exception as e:result['lastImageError']=repr(e)
 rows.append(result)
IMAP.write_text(prefix+json.dumps(imap,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8');OUT.write_text(json.dumps({'recovered':sum(r['status']=='RECOVERED' for r in rows),'rows':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'recovered':sum(r['status']=='RECOVERED' for r in rows),'rows':rows},ensure_ascii=False,indent=2))
