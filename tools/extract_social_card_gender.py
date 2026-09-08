#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DBS=[ROOT/'database_complete.json',ROOT/'database_v2_clean.json']
CARD_DIR=ROOT/'fragrantica-scraper-archive'/'social-cards'/'images'
OUT=ROOT/'social-card-gender.json'
REPORT=ROOT/'social-card-gender-report.json'

def flatten(data):
    if isinstance(data,list) and data and isinstance(data[0],dict) and isinstance(data[0].get('perfumes'),list): return [p for b in data for p in b.get('perfumes',[])]
    return data if isinstance(data,list) else []
def official(p): return not str(p.get('fragrantica_status') or p.get('fragranticaStatus') or '').upper().startswith('RESOLVED_NO_FORCE')
def fid(p):
    for k in ('fragranticaId','fragrantica_id','fragranticaID'):
        try:
            if p.get(k) not in (None,''): return int(p[k])
        except: pass
    for k in ('fragranticaUrl','fragranticaLocalUrl','fragrantica_url'):
        m=re.search(r'-(\d+)\.html',str(p.get(k) or ''))
        if m:return int(m.group(1))
def code(p): return str(p.get('code') or p.get('shobiCode') or '').strip()

def main():
    from PIL import Image
    import pytesseract
    base=json.loads(DBS[0].read_text(encoding='utf-8')); recs=[p for p in flatten(base) if official(p)]; byid={fid(p):p for p in recs if fid(p)}
    cards={}
    for f in CARD_DIR.iterdir():
        if f.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}: continue
        m=re.search(r'_(\d+)$',f.stem)
        if m and int(m.group(1)) in byid: cards[int(m.group(1))]=f
    found={}; unresolved=[]
    for n,(i,f) in enumerate(sorted(cards.items()),1):
        im=Image.open(f).convert('L')
        # Gender label is in the upper metadata area; OCR a broad crop and classify only explicit Fragrantica wording.
        crop=im.crop((0,0,im.width,min(im.height,int(im.height*.68))))
        text=' '.join(pytesseract.image_to_string(crop,config='--psm 11').split())
        low=text.lower()
        g=None
        if re.search(r'\bfor women and men\b|\bfor men and women\b|\bunisex\b',low): g='Unisex'
        elif re.search(r'\bfor women\b|\bfor woman\b',low): g='Female'
        elif re.search(r'\bfor men\b|\bfor man\b',low): g='Male'
        if g: found[i]=g
        else: unresolved.append({'code':code(byid[i]),'fragranticaId':i,'card':str(f.relative_to(ROOT))})
        if n%100==0: print(n,len(found),len(unresolved))
    # Never overwrite unresolved records with an inferred value.
    for db in DBS:
        data=json.loads(db.read_text(encoding='utf-8'))
        for p in flatten(data):
            if not official(p): continue
            i=fid(p)
            if i in found:
                p['gender']=found[i]; p['genderSource']='Fragrantica social card'; p['genderStatus']='VALIDATED_SOCIAL_CARD'
            elif i in cards:
                p.pop('genderSource',None); p['genderStatus']='UNRESOLVED_NO_INFERENCE'
        db.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows=[{'code':code(byid[i]),'fragranticaId':i,'gender':g,'source':'Fragrantica social card'} for i,g in sorted(found.items())]
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    counts={g:sum(x==g for x in found.values()) for g in ('Male','Female','Unisex')}
    report={'official':len(recs),'archivedCards':len(cards),'withGender':len(found),'withoutGender':len(recs)-len(found),'counts':counts,'unresolved':unresolved}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
