#!/usr/bin/env python3
from __future__ import annotations
import json,re,math
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
VAL=ROOT/'social-card-main-notes-validated.json'
CARD_DIR=ROOT/'fragrantica-scraper-archive'/'social-cards'/'images'
OUT=ROOT/'social-card-note-review'
CROP=(40,700,470,1120)
PER_SHEET=20
COLS=4
CELL_W=920
CELL_H=930

def card_for(fid:int):
    hits=[]
    for p in CARD_DIR.glob(f'*_{fid}.*'):
        if p.suffix.lower() in {'.jpg','.jpeg','.png','.webp'}: hits.append(p)
    return sorted(hits)[0] if hits else None

def main():
    data=json.loads(VAL.read_text(encoding='utf-8'))
    unresolved=[x for x in data if not x.get('validated')]
    # prioritize partially readable cards, then empty cards
    unresolved.sort(key=lambda x:(0 if x.get('rawSlots') else 1, int(x.get('fragranticaId') or 10**9)))
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob('sheet-*.jpg'): old.unlink()
    manifest=[]
    for si in range(math.ceil(len(unresolved)/PER_SHEET)):
        batch=unresolved[si*PER_SHEET:(si+1)*PER_SHEET]
        rows=math.ceil(len(batch)/COLS)
        sheet=Image.new('RGB',(COLS*CELL_W,rows*CELL_H),'white')
        draw=ImageDraw.Draw(sheet)
        for i,item in enumerate(batch):
            fid=int(item.get('fragranticaId') or 0); code=str(item.get('code') or '')
            p=card_for(fid)
            cx=(i%COLS)*CELL_W; cy=(i//COLS)*CELL_H
            title=f'{si*PER_SHEET+i+1}. {code} | FID {fid}'
            draw.text((cx+12,cy+8),title,fill='black')
            raw=' | '.join(str(s.get('name') or '') for s in (item.get('rawSlots') or []))
            if raw: draw.text((cx+12,cy+42),'OCR: '+raw[:110],fill='black')
            if p:
                im=Image.open(p).convert('RGB')
                sx=im.width/1200; sy=im.height/1200
                x1,y1,x2,y2=CROP
                crop=im.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy)))
                crop=ImageOps.autocontrast(crop)
                crop.thumbnail((CELL_W-24,CELL_H-95),Image.Resampling.LANCZOS)
                sheet.paste(crop,(cx+12,cy+82))
            else:
                draw.text((cx+12,cy+90),'CARD NOT FOUND',fill='black')
            manifest.append({'index':si*PER_SHEET+i+1,'sheet':si+1,'code':code,'fragranticaId':fid,'card':str(p.relative_to(ROOT)) if p else None,'rawSlots':item.get('rawSlots') or [],'failures':item.get('failures') or []})
        sheet.save(OUT/f'sheet-{si+1:03d}.jpg',quality=92,optimize=True)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Unresolved cards: {len(unresolved)} | sheets: {math.ceil(len(unresolved)/PER_SHEET)}')
if __name__=='__main__': main()
