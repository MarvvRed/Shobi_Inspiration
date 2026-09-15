#!/usr/bin/env python3
from __future__ import annotations
import csv,json,re
from pathlib import Path
from PIL import Image,ImageEnhance,ImageFilter,ImageOps
import pytesseract

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; SITE=ROOT/'database/catalog/catalog_site.json'; VAL=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json'; GS=ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv'; OUT=ROOT/'database/audits/identity-gender-season-four-fixes.json'
EXPECTED={'2313-DRC':'56324','2106-MARC':'46802','1950-SWISA':'22928','1767-LTN':'51016'}
SEASONS=('winter','spring','summer','fall'); ROIS={'winter':(0.416,0.835,0.650,0.885),'spring':(0.680,0.835,0.915,0.885),'summer':(0.416,0.900,0.650,0.950),'fall':(0.680,0.900,0.915,0.950)}
GENDER_ROI_WIDE=(0.005,0.005,0.995,0.340)

def code(v):return str(v or '').strip().upper()
def crop_frac(im,box):
 w,h=im.size;return im.crop(tuple(int(v*(w if i%2==0 else h)) for i,v in enumerate(box)))
def saturation(rgb):
 hi,lo=max(rgb),min(rgb);return 0 if hi==0 else (hi-lo)/hi
def filled(im,season):
 roi=crop_frac(im.convert('RGB'),ROIS[season]);w,h=roi.size;x0,x1=max(1,int(w*.02)),max(2,int(w*.98));ys=range(max(1,int(h*.18)),max(2,int(h*.82)));active=[]
 for x in range(x0,x1):
  vals=[saturation(roi.getpixel((x,y)))>.10 for y in ys];active.append(sum(vals)/max(1,len(vals))>=.22)
 first=next((i for i,on in enumerate(active[:max(8,len(active)//4)]) if on),None)
 if first is None:return 0.0
 last,gap=first,0
 for i in range(first,len(active)):
  if active[i]:last,gap=i,0
  else:
   gap+=1
   if gap>8:break
 return min(1.0,(last+1)/max(1,len(active)))
def season_measure(im):
 sc={s:filled(im,s) for s in SEASONS};o=sorted(sc.items(),key=lambda x:x[1],reverse=True);margin=o[0][1]-o[1][1];return sc,o[0][0],('HIGH' if margin>=.10 else ('MEDIUM' if margin>.02 else 'CLOSE')),margin
def norm_ocr(t):return re.sub(r'\s+',' ',re.sub(r'[^a-z ]+',' ',t.lower().replace('\n',' '))).strip()
def parse_gender(t):
 if re.search(r'(?:for )?(?:women|woman)\s+(?:and|ancl|anci)\s+(?:men|man)',t) or re.search(r'(?:for )?(?:men|man)\s+(?:and|ancl|anci)\s+(?:women|woman)',t):return 'unisex'
 if re.search(r'\bfor\s+wom[ae]n\b',t):return 'female'
 if re.search(r'\bfor\s+m[ae]n\b',t):return 'male'
 return ''
def gender_from_card(im):
 crop=crop_frac(im,GENDER_ROI_WIDE).convert('L');crop=ImageOps.autocontrast(crop);crop=ImageEnhance.Contrast(crop).enhance(2.8);crop=crop.resize((crop.width*3,crop.height*3),Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
 attempts=[]
 for psm in (6,11,12):
  raw=pytesseract.image_to_string(crop,config=f'--psm {psm}',lang='eng');t=norm_ocr(raw);attempts.append(t);g=parse_gender(t)
  if g:return g,' | '.join(dict.fromkeys(attempts))
 return '',' | '.join(dict.fromkeys(attempts))
def norm_gender(v):
 s=str(v or '').strip().lower();return {'feminine':'female','women':'female','woman':'female','masculine':'male','men':'male','man':'male','unisex':'unisex','female':'female','male':'male'}.get(s,s)
def url_id(u):
 m=re.search(r'-(\d+)\.html(?:$|[?#])',str(u or ''),re.I);return m.group(1) if m else ''

db=json.loads(DB.read_text(encoding='utf-8-sig'));site=json.loads(SITE.read_text(encoding='utf-8-sig'));val={code(x.get('code')):x for x in json.loads(VAL.read_text(encoding='utf-8'))}
with GS.open(encoding='utf-8-sig',newline='') as f:gs=list(csv.DictReader(f));fields=list(gs[0]) if gs else ['prestashop_product_id','shobi_code','fragrantica_id','gender','gender_source','gender_ocr_text','winter','spring','summer','fall','main_season','season_confidence','season_margin','local_path']
bygs={code(x.get('shobi_code')):x for x in gs};changes=[]
for r,s in zip(db,site):
 c=code(r.get('code'))
 if c not in EXPECTED:continue
 fid=str(r.get('fragranticaId') or '').strip();url=str(r.get('fragranticaUrl') or '').strip();src=val.get(c) or {};card=str(src.get('card') or '')
 if fid!=EXPECTED[c] or url_id(url)!=fid or src.get('validated') is not True or str(src.get('fragranticaId') or '')!=fid or not card or not (ROOT/card).is_file():
  print('SKIP chain',c,fid,url,card);continue
 with Image.open(ROOT/card) as im:
  scores,main,conf,margin=season_measure(im);g,ocr=gender_from_card(im)
 current=norm_gender(r.get('gender') or r.get('genderAffinity'))
 r['fragranticaVerificationSource']=url
 r['identityStatus']='CONFIRMED'
 r['seasons']=[main];s['seasons']=[main]
 gender_ok=bool(g and current and g==current)
 if gender_ok:r['genderStatus']='VALIDATED_SOCIAL_CARD'
 rec=bygs.get(c);vals={'prestashop_product_id':str(r.get('prestashopProductId') or ''),'shobi_code':c,'fragrantica_id':fid,'gender':g if gender_ok else (rec or {}).get('gender',''),'gender_source':'SOCIAL_CARD_OCR' if gender_ok else (rec or {}).get('gender_source',''),'gender_ocr_text':ocr,'winter':f"{scores['winter']:.4f}",'spring':f"{scores['spring']:.4f}",'summer':f"{scores['summer']:.4f}",'fall':f"{scores['fall']:.4f}",'main_season':main,'season_confidence':conf,'season_margin':f'{margin:.4f}','local_path':card}
 if rec:rec.update(vals)
 else:gs.append(vals);bygs[c]=vals
 changes.append({'code':c,'fid':fid,'url':url,'card':card,'currentGender':current,'ocrGender':g,'genderVerified':gender_ok,'season':main,'scores':scores})
with GS.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(gs)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');OUT.write_text(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2))
