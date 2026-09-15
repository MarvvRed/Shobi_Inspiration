#!/usr/bin/env python3
from __future__ import annotations
import csv,json,time,urllib.request,urllib.error
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; SITE=ROOT/'database/catalog/catalog_site.json'
VAL=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json'; GS=ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv'
IMAP=ROOT/'database/assets/perfumes'/'map.js'; OUT=ROOT/'database/audits/image-season-recovery.json'
SEASONS=('winter','spring','summer','fall')
ROIS={'winter':(0.416,0.835,0.650,0.885),'spring':(0.680,0.835,0.915,0.885),'summer':(0.416,0.900,0.650,0.950),'fall':(0.680,0.900,0.915,0.950)}

def code(v): return str(v or '').strip().upper()
def crop_frac(im,box):
 w,h=im.size; return im.crop(tuple(int(v*(w if i%2==0 else h)) for i,v in enumerate(box)))
def saturation(rgb):
 hi,lo=max(rgb),min(rgb); return 0.0 if hi==0 else (hi-lo)/hi
def filled_fraction(im,season):
 roi=crop_frac(im.convert('RGB'),ROIS[season]); w,h=roi.size
 if w<4 or h<4:return 0.0
 x0,x1=max(1,int(w*.02)),max(2,int(w*.98)); ys=range(max(1,int(h*.18)),max(2,int(h*.82)))
 active=[]
 for x in range(x0,x1):
  vals=[saturation(roi.getpixel((x,y)))>.10 for y in ys]
  active.append(sum(vals)/max(1,len(vals))>=.22)
 first=next((i for i,on in enumerate(active[:max(8,len(active)//4)]) if on),None)
 if first is None:return 0.0
 last,gap=first,0
 for i in range(first,len(active)):
  if active[i]:last,gap=i,0
  else:
   gap+=1
   if gap>8:break
 return min(1.0,(last+1)/max(1,len(active)))
def measure(path):
 with Image.open(path) as im:scores={s:filled_fraction(im,s) for s in SEASONS}
 ordered=sorted(scores.items(),key=lambda kv:kv[1],reverse=True); best,second=ordered[0],ordered[1]; margin=best[1]-second[1]
 return scores,best[0],('HIGH' if margin>=.10 else ('MEDIUM' if margin>.02 else 'CLOSE')),margin

def valid_avif(data,ctype=''):
 return len(data)>=1000 and (b'ftypavif' in data[:32] or b'ftypavis' in data[:32] or 'image/avif' in ctype.lower())
def fetch_image(fid):
 url=f'https://fimgs.net/mdimg/perfume-thumbs/dark-375x500.{fid}.avif'
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'image/avif,image/webp,image/*,*/*;q=0.8','Referer':'https://www.fragrantica.com/'})
 try:
  with urllib.request.urlopen(req,timeout=25) as r:
   data=r.read(); ctype=r.headers.get('Content-Type','')
  return (data if valid_avif(data,ctype) else None),url,''
 except Exception as e:return None,url,f'{type(e).__name__}: {e}'

db=json.loads(DB.read_text(encoding='utf-8-sig')); site=json.loads(SITE.read_text(encoding='utf-8-sig'))
val={code(x.get('code')):x for x in json.loads(VAL.read_text(encoding='utf-8'))}
prefix='window.PERFUME_IMAGE_MAP='; txt=IMAP.read_text(encoding='utf-8').strip(); imap=json.loads(txt[len(prefix):].rstrip(';'))
with GS.open(encoding='utf-8-sig',newline='') as f:
 gs_rows=list(csv.DictReader(f)); fields=list(gs_rows[0]) if gs_rows else ['prestashop_product_id','shobi_code','fragrantica_id','gender','gender_source','gender_ocr_text','winter','spring','summer','fall','main_season','season_confidence','season_margin','local_path']
by_gs={code(x.get('shobi_code')):x for x in gs_rows}
changes=[]
for r,s in zip(db,site):
 if str(s.get('validationStatus') or '').lower()!='yellow':continue
 failed=[k for k,v in (s.get('validationChecks') or {}).items() if not v]
 if failed!=['image','season']:continue
 c=code(r.get('code')); fid=str(r.get('fragranticaId') or '').strip(); src=val.get(c) or {}
 card=str(src.get('card') or '').strip()
 if not fid or str(src.get('fragranticaId') or '').strip()!=fid or src.get('validated') is not True or not card or not (ROOT/card).is_file():
  print('SKIP proof',c);continue
 scores,main,conf,margin=measure(ROOT/card)
 data,url,err=fetch_image(fid)
 target=ROOT/'database/assets/perfumes'/f'{fid}.avif'
 if data is None and not (target.is_file() and target.stat().st_size>=1000):
  print('SKIP image',c,err);continue
 if data is not None:
  target.write_bytes(data);time.sleep(.05)
 imap[c]=f'database/assets/perfumes/{fid}.avif'
 r['seasons']=[main]; s['seasons']=[main]
 rec=by_gs.get(c)
 vals={'prestashop_product_id':str(r.get('prestashopProductId') or ''),'shobi_code':c,'fragrantica_id':fid,'gender':(rec or {}).get('gender',''),'gender_source':(rec or {}).get('gender_source',''),'gender_ocr_text':(rec or {}).get('gender_ocr_text',''),'winter':f"{scores['winter']:.4f}",'spring':f"{scores['spring']:.4f}",'summer':f"{scores['summer']:.4f}",'fall':f"{scores['fall']:.4f}",'main_season':main,'season_confidence':conf,'season_margin':f'{margin:.4f}','local_path':card}
 if rec:rec.update(vals)
 else:gs_rows.append(vals);by_gs[c]=vals
 changes.append({'code':c,'fid':fid,'season':main,'seasonScores':scores,'image':f'database/assets/perfumes/{fid}.avif','imageUrl':url,'card':card})

with GS.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(gs_rows)
IMAP.write_text(prefix+json.dumps(imap,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
OUT.write_text(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('changed',len(changes))
