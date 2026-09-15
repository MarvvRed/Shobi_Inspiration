#!/usr/bin/env python3
from __future__ import annotations
import csv,json,re
from pathlib import Path
from PIL import Image,ImageEnhance,ImageFilter,ImageOps
import pytesseract

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json';SITE=ROOT/'database/catalog/catalog_site.json';VALID=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json';RAW=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes.json';GS=ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv';OUT=ROOT/'database/audits/all-exact-card-gender-season-recovery.json'
SEASONS=('winter','spring','summer','fall');ROIS={'winter':(0.416,0.835,0.650,0.885),'spring':(0.680,0.835,0.915,0.885),'summer':(0.416,0.900,0.650,0.950),'fall':(0.680,0.900,0.915,0.950)};GENDER_ROI=(0.005,0.005,0.995,0.340)

def code(v):return str(v or '').strip().upper()
def crop_frac(im,b):
 w,h=im.size;return im.crop(tuple(int(v*(w if i%2==0 else h)) for i,v in enumerate(b)))
def sat(rgb):
 hi,lo=max(rgb),min(rgb);return 0.0 if hi==0 else (hi-lo)/hi
def filled(im,s):
 roi=crop_frac(im.convert('RGB'),ROIS[s]);w,h=roi.size
 if w<4 or h<4:return 0.0
 ys=range(max(1,int(h*.18)),max(2,int(h*.82)));active=[]
 for x in range(max(1,int(w*.02)),max(2,int(w*.98))):
  vals=[sat(roi.getpixel((x,y)))>.10 for y in ys];active.append(sum(vals)/max(1,len(vals))>=.22)
 first=next((i for i,on in enumerate(active[:max(8,len(active)//4)]) if on),None)
 if first is None:return 0.0
 last,gap=first,0
 for i in range(first,len(active)):
  if active[i]:last,gap=i,0
  else:
   gap+=1
   if gap>8:break
 return min(1.0,(last+1)/max(1,len(active)))
def season(im):
 sc={s:filled(im,s) for s in SEASONS};o=sorted(sc.items(),key=lambda x:x[1],reverse=True);m=o[0][1]-o[1][1];return sc,o[0][0],('HIGH' if m>=.10 else ('MEDIUM' if m>.02 else 'CLOSE')),m
def normocr(t):return re.sub(r'\s+',' ',re.sub(r'[^a-z ]+',' ',t.lower().replace('\n',' '))).strip()
def parse_gender(t):
 if re.search(r'(?:for )?(?:women|woman)\s+(?:and|ancl|anci)\s+(?:men|man)',t) or re.search(r'(?:for )?(?:men|man)\s+(?:and|ancl|anci)\s+(?:women|woman)',t):return 'unisex'
 if re.search(r'\bfor\s+wom[ae]n\b',t):return 'female'
 if re.search(r'\bfor\s+m[ae]n\b',t):return 'male'
 return ''
def gender(im):
 crop=crop_frac(im,GENDER_ROI).convert('L');attempt=[]
 for thr in (None,170,205):
  x=ImageOps.autocontrast(crop);x=ImageEnhance.Contrast(x).enhance(2.7);x=x.resize((x.width*3,x.height*3),Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
  if thr is not None:x=x.point(lambda p:255 if p>thr else 0)
  for psm in (6,11,12):
   try:t=normocr(pytesseract.image_to_string(x,config=f'--psm {psm}',lang='eng'))
   except Exception:continue
   if t:attempt.append(t)
   g=parse_gender(t)
   if g:return g,' | '.join(dict.fromkeys(attempt))
 return '',' | '.join(dict.fromkeys(attempt))
def ng(v):
 s=str(v or '').strip().lower();return {'feminine':'female','women':'female','woman':'female','masculine':'male','men':'male','man':'male','female':'female','male':'male','unisex':'unisex'}.get(s,s)

db=json.loads(DB.read_text(encoding='utf-8-sig'));site=json.loads(SITE.read_text(encoding='utf-8-sig'));valid={code(x.get('code')):x for x in json.loads(VALID.read_text(encoding='utf-8'))};raw={code(x.get('code')):x for x in json.loads(RAW.read_text(encoding='utf-8'))}
with GS.open(encoding='utf-8-sig',newline='') as f:gs=list(csv.DictReader(f));fields=list(gs[0]) if gs else ['prestashop_product_id','shobi_code','fragrantica_id','gender','gender_source','gender_ocr_text','winter','spring','summer','fall','main_season','season_confidence','season_margin','local_path']
bygs={code(x.get('shobi_code')):x for x in gs};changes=[]
for r,sr in zip(db,site):
 if str(sr.get('validationStatus') or '').lower()!='yellow':continue
 checks=sr.get('validationChecks') or {}
 if checks.get('gender',False) and checks.get('season',False):continue
 c=code(r.get('code'));fid=str(r.get('fragranticaId') or '').strip()
 cards=[]
 for src in (valid.get(c),raw.get(c)):
  if src and str(src.get('fragranticaId') or '')==fid and src.get('card'):cards.append(str(src.get('card')))
 # also allow a previously recovered exact path from gender-season row
 oldgs=bygs.get(c) or {}
 if str(oldgs.get('fragrantica_id') or '')==fid and oldgs.get('local_path'):cards.append(str(oldgs.get('local_path')))
 card=next((p for p in dict.fromkeys(cards) if (ROOT/p).is_file()),None)
 if not fid or not card:continue
 with Image.open(ROOT/card) as im:
  sc,main,conf,margin=season(im);g,ocr=gender(im)
 current=ng(r.get('gender') or r.get('genderAffinity'));gender_ok=bool(g and current and g==current)
 changed_checks=[]
 if not checks.get('season',False):r['seasons']=[main];sr['seasons']=[main];changed_checks.append('season')
 if not checks.get('gender',False) and gender_ok:r['genderStatus']='VALIDATED_SOCIAL_CARD';changed_checks.append('gender')
 if not changed_checks:continue
 rec=bygs.get(c);vals={'prestashop_product_id':str(r.get('prestashopProductId') or ''),'shobi_code':c,'fragrantica_id':fid,'gender':g if gender_ok else (rec or {}).get('gender',''),'gender_source':'SOCIAL_CARD_OCR' if gender_ok else (rec or {}).get('gender_source',''),'gender_ocr_text':ocr,'winter':f"{sc['winter']:.4f}",'spring':f"{sc['spring']:.4f}",'summer':f"{sc['summer']:.4f}",'fall':f"{sc['fall']:.4f}",'main_season':main,'season_confidence':conf,'season_margin':f'{margin:.4f}','local_path':card}
 if rec:rec.update(vals)
 else:gs.append(vals);bygs[c]=vals
 changes.append({'code':c,'fid':fid,'card':card,'checks':changed_checks,'currentGender':current,'ocrGender':g,'season':main,'scores':sc,'seasonConfidence':conf,'seasonMargin':margin})
with GS.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(gs)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');OUT.write_text(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('changed',len(changes),'gender',sum('gender' in x['checks'] for x in changes),'season',sum('season' in x['checks'] for x in changes))
