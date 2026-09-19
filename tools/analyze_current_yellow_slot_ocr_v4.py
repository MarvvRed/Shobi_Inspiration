#!/usr/bin/env python3
"""Independent report-only slot OCR V4 for current yellow Social Cards.

This deliberately does NOT reuse V2 label boxes or the component grouping path.
It divides the visible note area into a fixed 2x3 geometric grid, OCRs every slot
independently, and accepts a slot only when >=2 exact lexicon reads agree with
zero competing eligible candidates. The observed sequence is produced from the
image first and only then compared with the live catalog.
"""
from __future__ import annotations

import csv, io, json, os, re, subprocess, unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import ROOT, DB, CROP, code, find_card

SITE = ROOT / 'database/catalog/catalog_site.json'
LEXICON = ROOT / 'database/audits/fragrantica-note-lexicon.txt'
OUT = ROOT / 'database/audits/current-yellow-slot-ocr-v4.json'

MIN_FUZZY = 0.90
MIN_MARGIN = 0.10


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii','ignore').decode()
    return ' '.join(re.findall(r'[a-z0-9]+', s.lower()))


def tsv_text(im, psm):
    b=io.BytesIO(); im.save(b, format='PNG')
    run=subprocess.run(['tesseract','stdin','stdout','--psm',str(psm),'-l','eng','tsv'],
        input=b.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=10, check=True, env={**os.environ,'OMP_THREAD_LIMIT':'1'})
    rows=list(csv.DictReader(io.StringIO(run.stdout.decode('utf-8','replace')), delimiter='\t'))
    words=[]
    for r in rows:
        txt=' '.join(str(r.get('text') or '').split())
        if not txt: continue
        try: conf=float(r.get('conf') or -1)
        except Exception: conf=-1
        if conf >= 30: words.append(txt)
    return ' '.join(words).strip()


def classify(raw, lexicon):
    t=norm(raw)
    if not t: return None,0.0,0.0,False
    exact=[n for n in lexicon if norm(n)==t]
    if len(exact)==1: return exact[0],1.0,1.0,True
    ranked=sorted(((SequenceMatcher(None,t,norm(n)).ratio(),n) for n in lexicon), reverse=True)
    if not ranked: return None,0.0,0.0,False
    score,name=ranked[0]; second=ranked[1][0] if len(ranked)>1 else 0.0
    return name,score,score-second,False


def variants(im):
    g=im.convert('L')
    a=ImageOps.autocontrast(g)
    b=ImageEnhance.Contrast(a).enhance(2.2)
    c=ImageEnhance.Sharpness(b).enhance(2.2)
    return [
        ('auto',a),('contrast',b),('sharp',c),
        ('bin150',c.point(lambda p:255 if p>150 else 0)),
        ('bin170',c.point(lambda p:255 if p>170 else 0)),
        ('bin190',c.point(lambda p:255 if p>190 else 0)),
    ]


def slot_read(im, lexicon):
    reads=[]
    for vname,v in variants(im):
        big=v.resize((max(1,v.width*5),max(1,v.height*5)),Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
        for psm in (6,7,8,11,12,13):
            try: raw=tsv_text(big,psm)
            except Exception: continue
            if not raw: continue
            name,score,margin,exact=classify(raw,lexicon)
            eligible=bool(name and (exact or (score>=MIN_FUZZY and margin>=MIN_MARGIN)))
            reads.append({'variant':vname,'psm':psm,'raw':raw,'candidate':name,'score':round(score,3),'margin':round(margin,3),'exact':exact,'eligible':eligible})
    exact_counts=Counter(r['candidate'] for r in reads if r['eligible'] and r['exact'] and r['candidate'])
    eligible_counts=Counter(r['candidate'] for r in reads if r['eligible'] and r['candidate'])
    winner,count=exact_counts.most_common(1)[0] if exact_counts else (None,0)
    competitors=sum(n for cand,n in eligible_counts.items() if cand!=winner)
    strong=bool(winner and count>=2 and competitors==0)
    # empty slots must remain empty; OCR garbage cannot become evidence.
    return {'winner':winner if strong else None,'strong':strong,'exactReads':count,'competingEligibleReads':competitors,'reads':reads}


def crop_note_grid(src):
    sx,sy=src.width/1200,src.height/1200
    x1,y1,x2,y2=CROP
    panel=src.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))).convert('RGB').resize((420,380),Image.Resampling.LANCZOS)
    # Relative geometry learned from the standard 1200x1200 Social Card notes panel.
    # Header occupies the top section; two note rows occupy the remainder.
    row_bands=((112,214),(244,365))
    cols=((0,140),(140,280),(280,420))
    slots=[]
    for r,(ya,yb) in enumerate(row_bands):
        for c,(xa,xb) in enumerate(cols):
            pad=4
            slots.append((r,c,panel.crop((max(0,xa-pad),max(0,ya-pad),min(420,xb+pad),min(380,yb+pad)))))
    return slots


def main():
    db=json.loads(DB.read_text(encoding='utf-8-sig'))
    site=json.loads(SITE.read_text(encoding='utf-8-sig'))
    by_site={code(r.get('code')):r for r in site}
    lex=[x.strip() for x in LEXICON.read_text(encoding='utf-8').splitlines() if x.strip()]
    targets=[]
    for row in db:
        c=code(row.get('code'))
        s=by_site.get(c) or {}
        if s.get('validationStatus')!='yellow': continue
        if 'Main Notes order not fully verified' not in (s.get('validationIssues') or []): continue
        targets.append(row)

    out=[]
    for i,row in enumerate(targets,1):
        c=code(row.get('code')); fid=str(row.get('fragranticaId') or '').strip(); catalog=list(row.get('fragranticaSocialCardNotes') or [])
        card=find_card(row)
        base={'code':c,'fid':fid,'catalog':catalog,'card':str(card.relative_to(ROOT)) if card else None}
        if not card:
            out.append({**base,'result':'NO_EXACT_CARD'}); continue
        try:
            with Image.open(card) as src:
                if src.width<800 or src.height<800 or src.height/src.width<0.85:
                    out.append({**base,'result':'UNSUPPORTED_CARD_GEOMETRY','size':[src.width,src.height]}); continue
                slot_imgs=crop_note_grid(src)
        except Exception as e:
            out.append({**base,'result':'IMAGE_ERROR','error':str(e)}); continue
        slot_results=[]; observed=[]; all_slots_strong_or_empty=True
        for r,cidx,im in slot_imgs:
            sr=slot_read(im,lex); sr.update({'row':r,'col':cidx}); slot_results.append(sr)
            if sr['strong'] and sr['winner']:
                observed.append(sr['winner'])
            else:
                # A slot is considered safely empty only when it has zero eligible candidates.
                eligible_any=any(x.get('eligible') for x in sr['reads'])
                if eligible_any: all_slots_strong_or_empty=False
        exact=bool(catalog and observed==catalog and all_slots_strong_or_empty)
        out.append({**base,'result':'EXACT_SLOT_SEQUENCE' if exact else 'SLOT_SEQUENCE_UNRESOLVED','observed':observed,'slots':slot_results})
        if i%25==0: print(f'processed {i}/{len(targets)}',flush=True)

    counts=Counter(r['result'] for r in out)
    payload={'mode':'NON_DESTRUCTIVE_INDEPENDENT_2X3_SLOT_OCR_V4','targets':len(targets),'counts':dict(counts),'rows':out}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'targets':len(targets),'counts':dict(counts),'output':str(OUT)},ensure_ascii=False))

if __name__=='__main__': main()
