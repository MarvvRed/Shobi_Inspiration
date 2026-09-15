#!/usr/bin/env python3
"""Recover season for season-only yellows from the exact archived Social Card bar geometry.
Uses the same ROI/filled-bar rule as extract_gender_season.py. No guessing/OCR.
"""
import csv,json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; SITE=ROOT/'database/catalog/catalog_site.json'
GS=ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv'
TARGETS={
 '107-ARB':'database/fragrantica/social-cards/images/1407_107-ARB_127709.jpeg',
 '973-VICT':'database/fragrantica/social-cards/images/998_973-VICT_133200.jpeg',
}
SEASONS=('winter','spring','summer','fall')
ROIS={
 'winter':(0.416,0.835,0.650,0.885), 'spring':(0.680,0.835,0.915,0.885),
 'summer':(0.416,0.900,0.650,0.950), 'fall':(0.680,0.900,0.915,0.950),
}
def crop_frac(im,box):
    w,h=im.size
    return im.crop(tuple(int(v*(w if i%2==0 else h)) for i,v in enumerate(box)))
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
    with Image.open(path) as im:
        scores={s:filled_fraction(im,s) for s in SEASONS}
    ordered=sorted(scores.items(),key=lambda kv:kv[1],reverse=True)
    best,second=ordered[0],ordered[1]; margin=best[1]-second[1]
    conf='HIGH' if margin>=.10 else ('MEDIUM' if margin>.02 else 'CLOSE')
    return scores,best[0],conf,margin

rows=json.loads(DB.read_text(encoding='utf-8-sig')); site=json.loads(SITE.read_text(encoding='utf-8-sig'))
by_code={str(r.get('code') or '').strip().upper():r for r in rows}
site_by_code={str(r.get('code') or '').strip().upper():r for r in site}
with GS.open(encoding='utf-8-sig',newline='') as f:
    existing=list(csv.DictReader(f)); fields=list(existing[0]) if existing else ['prestashop_product_id','shobi_code','fragrantica_id','gender','gender_source','gender_ocr_text','winter','spring','summer','fall','main_season','season_confidence','season_margin','local_path']
existing_codes={str(x.get('shobi_code') or '').strip().upper() for x in existing}
changes=[]
for code,rel in TARGETS.items():
    r=by_code[code]; s=site_by_code[code]; fid=str(r.get('fragranticaId') or '').strip(); p=ROOT/rel
    if not p.is_file():raise SystemExit(f'Missing exact card {p}')
    # Filename itself is bound to code+FID and was independently extracted from the exact social-card records.
    if not rel.endswith(f'_{code}_{fid}.jpeg'):raise SystemExit(f'Card identity drift {code}')
    scores,main,conf,margin=measure(p)
    r['seasons']=[main]; s['seasons']=[main]
    if code not in existing_codes:
        existing.append({'prestashop_product_id':str(r.get('prestashopProductId') or ''),'shobi_code':code,'fragrantica_id':fid,'gender':'','gender_source':'','gender_ocr_text':'','winter':f"{scores['winter']:.4f}",'spring':f"{scores['spring']:.4f}",'summer':f"{scores['summer']:.4f}",'fall':f"{scores['fall']:.4f}",'main_season':main,'season_confidence':conf,'season_margin':f'{margin:.4f}','local_path':rel})
    changes.append({'code':code,'fragranticaId':fid,'mainSeason':main,'scores':scores,'confidence':conf,'margin':margin,'source':rel})
with GS.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(existing)
DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
(ROOT/'database/audits/season-only-card-geometry-fixes.json').write_text(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(changes,ensure_ascii=False,indent=2))
