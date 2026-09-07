#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'
CARD_DIR=ROOT/'fragrantica-scraper-archive'/'social-cards'/'images'
WORK=ROOT/'.social-card-notes-work'
TIFF=WORK/'social-note-panels.tiff'
MANIFEST=WORK/'manifest.json'
TSV=WORK/'ocr.tsv'
REPORT=ROOT/'social-card-main-notes-report.json'
OUT_JSON=ROOT/'social-card-main-notes.json'
CROP_1200=(48,738,448,1097)
SCALE=5
LABEL_BANDS=[(145,232),(288,359)]
COL_RANGES=[(0,133),(133,267),(267,400)]

def flatten_records(data):
    if isinstance(data,list) and data and isinstance(data[0],dict) and isinstance(data[0].get('perfumes'),list):
        return [p for b in data for p in b.get('perfumes',[])]
    return data if isinstance(data,list) else []

def official(p):
    return not str(p.get('fragrantica_status') or p.get('fragranticaStatus') or '').upper().startswith('RESOLVED_NO_FORCE')

def frag_id(p):
    for k in ('fragranticaId','fragrantica_id','fragranticaID'):
        try:
            if p.get(k) not in (None,''): return int(str(p[k]))
        except: pass
    for k in ('fragrantica_url','fragranticaLocalUrl','fragranticaUrl'):
        m=re.search(r'-(\d+)\.html',str(p.get(k) or ''))
        if m:return int(m.group(1))

def code_of(p): return str(p.get('code') or p.get('shobiCode') or p.get('shobi_code') or '').strip()

def load_official():
    data=json.loads(DB.read_text(encoding='utf-8')); recs=[p for p in flatten_records(data) if official(p)]
    return recs,{frag_id(p):p for p in recs if frag_id(p)}

def cards_by_final_id(by_id):
    out={}
    if not CARD_DIR.exists():return out
    for p in CARD_DIR.iterdir():
        if p.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}:continue
        m=re.search(r'_(\d+)$',p.stem)
        if m and int(m.group(1)) in by_id:out.setdefault(int(m.group(1)),p)
    return out

def prepare():
    from PIL import Image,ImageOps,ImageEnhance,ImageFilter
    recs,by_id=load_official(); cards=cards_by_final_id(by_id); WORK.mkdir(exist_ok=True)
    pages=[];frames=[]
    for fid,p in sorted(cards.items()):
        im=Image.open(p).convert('L'); x1,y1,x2,y2=CROP_1200; sx=im.width/1200;sy=im.height/1200
        src=im.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))).resize((400,359))
        panel=Image.new('L',(400,359),255)
        for ya,yb in LABEL_BANDS: panel.paste(src.crop((0,ya,400,yb)),(0,ya))
        panel=ImageOps.autocontrast(panel); panel=ImageEnhance.Contrast(panel).enhance(1.9)
        panel=panel.resize((400*SCALE,359*SCALE),Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
        frames.append(panel); rec=by_id[fid]
        pages.append({'page':len(pages)+1,'fragranticaId':fid,'code':code_of(rec),'card':str(p.relative_to(ROOT))})
    if not frames:raise SystemExit('No matching archived social cards found')
    frames[0].save(TIFF,save_all=True,append_images=frames[1:],compression='tiff_deflate',dpi=(400,400))
    MANIFEST.write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Prepared {len(frames)} social-card note panels; official={len(recs)}')

def clean_token(s):
    s=s.replace('|','').replace('©','').strip()
    return re.sub(r'^[^\wÀ-ž&+\-™®\'’]+|[^\wÀ-ž&+\-™®\'’]+$','',s)

def parse_tsv():
    pages=json.loads(MANIFEST.read_text(encoding='utf-8')); by_page={int(x['page']):x for x in pages}; words={n:[] for n in by_page}
    with TSV.open(encoding='utf-8',errors='replace',newline='') as f:
        for r in csv.DictReader(f,delimiter='\t'):
            try:
                pg=int(r.get('page_num') or 0); conf=float(r.get('conf') or -1); text=clean_token(r.get('text') or '')
                if pg not in words or conf<15 or not text:continue
                words[pg].append((int(r['left']),int(r['top']),int(r['width']),int(r['height']),conf,text))
            except:pass
    results=[];low=[]
    for pg,meta in by_page.items():
        slots=[]
        for ry,(y1,y2) in enumerate(LABEL_BANDS):
            for cx,(x1,x2) in enumerate(COL_RANGES):
                zone=[]
                for left,top,w,h,conf,text in words.get(pg,[]):
                    center=(left+w/2)/SCALE; cy=(top+h/2)/SCALE
                    if x1<=center<x2 and y1<=cy<y2:
                        if len(text)==1 and not text.isdigit() and conf<70:continue
                        zone.append((top,left,conf,text))
                if not zone:continue
                zone.sort(key=lambda z:(z[0],z[1])); toks=[]
                for z in zone:
                    if not toks or z[3]!=toks[-1]:toks.append(z[3])
                label=re.sub(r'\s+',' ',' '.join(toks)).strip(); label=re.sub(r'\s+-\s+','-',label)
                alpha=sum(c.isalpha() for c in label)
                if alpha<2 or len(label)>60:continue
                slots.append({'slot':ry*3+cx+1,'name':label,'ocrConfidence':round(sum(z[2] for z in zone)/len(zone),1)})
        slots.sort(key=lambda x:x['slot']); names=[x['name'] for x in slots]
        avg=round(sum(x['ocrConfidence'] for x in slots)/len(slots),1) if slots else 0
        item={**meta,'mainNotes':names,'slots':slots,'ocrConfidence':avg};results.append(item)
        if not names or avg<60:low.append(item)
    OUT_JSON.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    dist={}
    for x in results:dist[str(len(x['mainNotes']))]=dist.get(str(len(x['mainNotes'])),0)+1
    report={'rule':'mainNotes come ONLY from archived Fragrantica social-card notes panel, read row-major; pyramid is never used','processed_cards':len(results),'with_notes':sum(bool(x['mainNotes']) for x in results),'empty':sum(not x['mainNotes'] for x in results),'low_confidence_lt60':len(low),'note_count_distribution':dist,'low_confidence_sample':[{'code':x['code'],'fragranticaId':x['fragranticaId'],'mainNotes':x['mainNotes'],'ocrConfidence':x['ocrConfidence']} for x in low[:50]]}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','parse']);a=ap.parse_args();prepare() if a.mode=='prepare' else parse_tsv()
if __name__=='__main__':main()
