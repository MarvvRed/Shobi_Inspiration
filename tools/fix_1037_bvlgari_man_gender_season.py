#!/usr/bin/env python3
import csv,json,re
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'; SITE=ROOT/'catalog_site.json'
VAL=ROOT/'social-card-main-notes-validated.json'
GS=ROOT/'fragrantica-scraper-archive'/'social-cards'/'gender-season.csv'
TARGET='1037-BLG'; FID='9403'
SEASONS=('winter','spring','summer','fall')
ROIS={'winter':(0.416,0.835,0.650,0.885),'spring':(0.680,0.835,0.915,0.885),'summer':(0.416,0.900,0.650,0.950),'fall':(0.680,0.900,0.915,0.950)}

def code(v): return str(v or '').strip().upper()
def crop_frac(im,box):
    w,h=im.size
    return im.crop(tuple(int(v*(w if i%2==0 else h)) for i,v in enumerate(box)))
def saturation(rgb):
    hi,lo=max(rgb),min(rgb); return 0.0 if hi==0 else (hi-lo)/hi
def filled_fraction(im,season):
    roi=crop_frac(im.convert('RGB'),ROIS[season]); w,h=roi.size
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
    ordered=sorted(scores.items(),key=lambda kv:kv[1],reverse=True)
    margin=ordered[0][1]-ordered[1][1]
    return scores,ordered[0][0],('HIGH' if margin>=.10 else ('MEDIUM' if margin>.02 else 'CLOSE')),margin

db=json.loads(DB.read_text(encoding='utf-8-sig')); site=json.loads(SITE.read_text(encoding='utf-8-sig'))
val={code(x.get('code')):x for x in json.loads(VAL.read_text(encoding='utf-8'))}
vr=val.get(TARGET)
if not vr or vr.get('validated') is not True or str(vr.get('fragranticaId') or '')!=FID:
    raise SystemExit('Exact validated FID9403 card missing')
card=str(vr.get('card') or '')
if not card or not (ROOT/card).is_file(): raise SystemExit('Card file missing')
row=next((x for x in db if code(x.get('code'))==TARGET),None)
srow=next((x for x in site if code(x.get('code'))==TARGET),None)
if not row or not srow or str(row.get('fragranticaId') or '')!=FID: raise SystemExit('Target/FID mismatch')
# OCR audit already independently established "for men" on this exact card; record only the verified result here.
row['gender']='Male'; row['genderAffinity']='masculine'; row['genderStatus']='VALIDATED_SOCIAL_CARD'
srow['gender']='Male'; srow['genderAffinity']='masculine'
scores,main,conf,margin=measure(ROOT/card)
row['seasons']=[main]; srow['seasons']=[main]
with GS.open(encoding='utf-8-sig',newline='') as f:
    rows=list(csv.DictReader(f)); fields=list(rows[0]) if rows else ['prestashop_product_id','shobi_code','fragrantica_id','gender','gender_source','gender_ocr_text','winter','spring','summer','fall','main_season','season_confidence','season_margin','local_path']
rec=next((x for x in rows if code(x.get('shobi_code'))==TARGET),None)
values={'prestashop_product_id':str(row.get('prestashopProductId') or ''),'shobi_code':TARGET,'fragrantica_id':FID,'gender':'male','gender_source':'exact_social_card_ocr','gender_ocr_text':'for men','winter':f"{scores['winter']:.4f}",'spring':f"{scores['spring']:.4f}",'summer':f"{scores['summer']:.4f}",'fall':f"{scores['fall']:.4f}",'main_season':main,'season_confidence':conf,'season_margin':f'{margin:.4f}','local_path':card}
if rec: rec.update(values)
else: rows.append(values)
with GS.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
report={'code':TARGET,'fid':FID,'gender':'Male','mainSeason':main,'scores':scores,'confidence':conf,'margin':margin,'card':card}
(ROOT/'fix-1037-bvlgari-man-gender-season.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
