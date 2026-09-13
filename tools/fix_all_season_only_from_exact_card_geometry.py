#!/usr/bin/env python3
"""Resolve any yellow whose only failed check is season from exact archived Social Card geometry."""
import csv,json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'; SITE=ROOT/'catalog_site.json'
VAL=ROOT/'social-card-main-notes-validated.json'; RAW=ROOT/'social-card-main-notes.json'
GS=ROOT/'fragrantica-scraper-archive'/'social-cards'/'gender-season.csv'
SEASONS=('winter','spring','summer','fall')
ROIS={'winter':(0.416,0.835,0.650,0.885),'spring':(0.680,0.835,0.915,0.885),'summer':(0.416,0.900,0.650,0.950),'fall':(0.680,0.900,0.915,0.950)}

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
    with Image.open(path) as im:scores={s:filled_fraction(im,s) for s in SEASONS}
    ordered=sorted(scores.items(),key=lambda kv:kv[1],reverse=True)
    best,second=ordered[0],ordered[1]; margin=best[1]-second[1]
    return scores,best[0],('HIGH' if margin>=.10 else ('MEDIUM' if margin>.02 else 'CLOSE')),margin

def code(v):return str(v or '').strip().upper()

db=json.loads(DB.read_text(encoding='utf-8-sig')); site=json.loads(SITE.read_text(encoding='utf-8-sig'))
val={code(x.get('code')):x for x in json.loads(VAL.read_text(encoding='utf-8'))}
raw={code(x.get('code')):x for x in json.loads(RAW.read_text(encoding='utf-8'))}
with GS.open(encoding='utf-8-sig',newline='') as f:
    gs_rows=list(csv.DictReader(f)); fields=list(gs_rows[0]) if gs_rows else ['prestashop_product_id','shobi_code','fragrantica_id','gender','gender_source','gender_ocr_text','winter','spring','summer','fall','main_season','season_confidence','season_margin','local_path']
by_gs={code(x.get('shobi_code')):x for x in gs_rows}
changes=[]
for r,s in zip(db,site):
    if str(s.get('validationStatus') or '').lower()!='yellow':continue
    failed=[k for k,v in (s.get('validationChecks') or {}).items() if not v]
    if failed!=['season']:continue
    c=code(r.get('code')); fid=str(r.get('fragranticaId') or '').strip()
    candidates=[]
    for src_name,src in [('validated',val.get(c)),('raw',raw.get(c))]:
        if not src:continue
        if str(src.get('fragranticaId') or '').strip()!=fid:continue
        card=str(src.get('card') or '').strip()
        if card and (ROOT/card).is_file():candidates.append((src_name,card))
    unique=[]
    for item in candidates:
        if item[1] not in [x[1] for x in unique]:unique.append(item)
    if len(unique)!=1:
        print('SKIP',c,'candidate_cards',unique);continue
    src_name,card=unique[0]
    scores,main,conf,margin=measure(ROOT/card)
    r['seasons']=[main]; s['seasons']=[main]
    rec=by_gs.get(c)
    values={'prestashop_product_id':str(r.get('prestashopProductId') or ''),'shobi_code':c,'fragrantica_id':fid,'gender':(rec or {}).get('gender',''),'gender_source':(rec or {}).get('gender_source',''),'gender_ocr_text':(rec or {}).get('gender_ocr_text',''),'winter':f"{scores['winter']:.4f}",'spring':f"{scores['spring']:.4f}",'summer':f"{scores['summer']:.4f}",'fall':f"{scores['fall']:.4f}",'main_season':main,'season_confidence':conf,'season_margin':f'{margin:.4f}','local_path':card}
    if rec:rec.update(values)
    else:gs_rows.append(values);by_gs[c]=values
    changes.append({'code':c,'fragranticaId':fid,'mainSeason':main,'scores':scores,'confidence':conf,'margin':margin,'sourceType':src_name,'source':card})

with GS.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(gs_rows)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
(ROOT/'all-season-only-card-geometry-fixes.json').write_text(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2))
