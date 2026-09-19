#!/usr/bin/env python3
"""Targeted non-destructive OCR refinement for current-yellow V2 near-pass rows.

Focuses only rows with exactly one failed label in current-yellow V2 validation.
Keeps STRONG_EXACT semantics unchanged; this script only gathers extra independent
exact crop reads using tighter/looser crop variants and more OCR preprocessing.
"""
from __future__ import annotations

import csv, io, json, os, re, subprocess, unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import ROOT, DB, CROP, code, find_card

SRC = ROOT / 'database/audits/current-yellow-v2-exact-validation.json'
PILOT = ROOT / 'database/audits/current-yellow-label-ocr-v2.json'
LEXICON = ROOT / 'database/audits/fragrantica-note-lexicon.txt'
OUT = ROOT / 'database/audits/current-yellow-near-pass-ocr-refinement.json'

MIN_EXACT_OR_FUZZY = 0.84
MIN_FUZZY_MARGIN = 0.08


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii','ignore').decode()
    return ' '.join(re.findall(r'[a-z0-9]+', s.lower()))


def tsv(im, psm):
    b = io.BytesIO(); im.save(b, format='PNG')
    run = subprocess.run(
        ['tesseract','stdin','stdout','--psm',str(psm),'-l','eng','tsv'],
        input=b.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=10, check=True, env={**os.environ,'OMP_THREAD_LIMIT':'1'})
    return list(csv.DictReader(io.StringIO(run.stdout.decode('utf-8','replace')), delimiter='\t'))


def candidate(raw, lexicon):
    t = norm(raw)
    if not t: return None,0.0,0.0,False
    exact=[n for n in lexicon if norm(n)==t]
    if len(exact)==1: return exact[0],1.0,1.0,True
    ranked=sorted(((SequenceMatcher(None,t,norm(n)).ratio(),n) for n in lexicon), reverse=True)
    if not ranked: return None,0.0,0.0,False
    score,name=ranked[0]; second=ranked[1][0] if len(ranked)>1 else 0.0
    return name,score,score-second,False


def extract_text(rows):
    return ' '.join(' '.join(str(r.get('text') or '').split()) for r in rows).strip()


def crop_variants(panel, box):
    x1,y1,x2,y2=box
    variants=[]
    pads=[('tight',2,2),('base',8,6),('wide',16,10),('xwide',24,12)]
    for name,px,py in pads:
        xa=max(0,int(x1)-px); ya=max(0,int(y1)-py); xb=min(panel.width,int(x2)+px); yb=min(panel.height,int(y2)+py)
        crop=panel.crop((xa,ya,xb,yb)).convert('L')
        a=ImageOps.autocontrast(crop)
        b=ImageEnhance.Contrast(a).enhance(2.4)
        c=ImageEnhance.Sharpness(b).enhance(2.0)
        d=c.point(lambda p: 255 if p>165 else 0)
        e=c.point(lambda p: 255 if p>185 else 0)
        variants.extend([
            (f'{name}-auto',a),(f'{name}-contrast',b),(f'{name}-sharp',c),
            (f'{name}-bin165',d),(f'{name}-bin185',e)])
    return variants


def inspect_label(panel, box, expected, lexicon):
    reads=[]
    for vname,im in crop_variants(panel,box):
        big=im.resize((max(1,im.width*5),max(1,im.height*5)), Image.Resampling.LANCZOS)
        big=big.filter(ImageFilter.SHARPEN)
        for psm in (6,7,8,11,12,13):
            try:
                text=extract_text(tsv(big,psm))
            except Exception:
                continue
            if not text:
                continue
            name,score,margin,exact=candidate(text,lexicon)
            eligible=bool(name and (exact or (score>=MIN_EXACT_OR_FUZZY and margin>=MIN_FUZZY_MARGIN)))
            reads.append({'variant':vname,'psm':psm,'raw':text,'candidate':name,'score':round(score,3),'margin':round(margin,3),'exact':exact,'eligible':eligible})
    exact_expected=[r for r in reads if r.get('eligible') and r.get('exact') and r.get('candidate')==expected]
    competing=[r for r in reads if r.get('eligible') and r.get('candidate') and r.get('candidate')!=expected]
    return {
        'expected':expected,
        'exactExpectedReads':len(exact_expected),
        'competingEligibleReads':len(competing),
        'strongSupplemental':bool(len(exact_expected)>=2 and not competing),
        'reads':reads,
    }


def main():
    val=json.loads(SRC.read_text(encoding='utf-8'))
    pilot=json.loads(PILOT.read_text(encoding='utf-8'))
    catalog=json.loads(DB.read_text(encoding='utf-8-sig'))
    by_cat={code(r.get('code')):r for r in catalog}
    by_pilot={code(r.get('code')):r for r in pilot.get('rows',[])}
    lex=[x.strip() for x in LEXICON.read_text(encoding='utf-8').splitlines() if x.strip()]

    targets=[]
    for r in val.get('rows',[]):
        if r.get('status')!='REVIEW': continue
        failed=[x for x in r.get('labels',[]) if not x.get('ok')]
        if len(failed)==1:
            targets.append((r,failed[0]))

    results=[]
    for i,(vr,fl) in enumerate(targets,1):
        c=code(vr.get('code')); pr=by_pilot.get(c); cat=by_cat.get(c)
        base={'code':c,'fid':str(vr.get('fid') or ''),'failedNote':fl.get('note')}
        if not pr or not cat:
            results.append({**base,'result':'MISSING_SOURCE'}); continue
        # locate matching detail from pilot by note and failed status context
        detail=next((d for d in pr.get('details',[]) if d.get('note')==fl.get('note')),None)
        if not detail:
            results.append({**base,'result':'MISSING_DETAIL'}); continue
        card=find_card(cat)
        if not card:
            results.append({**base,'result':'NO_CARD'}); continue
        try:
            with Image.open(card) as src:
                sx,sy=src.width/1200,src.height/1200
                x1,y1,x2,y2=CROP
                panel=src.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))).convert('RGB').resize((420,380),Image.Resampling.LANCZOS)
        except Exception as e:
            results.append({**base,'result':'IMAGE_ERROR','error':str(e)}); continue
        box=detail.get('box')
        if not box or len(box)!=4:
            results.append({**base,'result':'NO_BOX'}); continue
        refined=inspect_label(panel,box,str(fl.get('note') or ''),lex)
        result='SUPPLEMENTAL_STRONG_EXACT' if refined['strongSupplemental'] else 'STILL_REVIEW'
        results.append({**base,'result':result,'original':fl,'refined':refined})
        if i%10==0: print(f'processed {i}/{len(targets)}',flush=True)

    counts=Counter(r['result'] for r in results)
    payload={'mode':'NON_DESTRUCTIVE_TARGETED_NEAR_PASS_OCR_REFINEMENT','targets':len(targets),'counts':dict(counts),'rows':results}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'targets':len(targets),'counts':dict(counts),'output':str(OUT)}))

if __name__=='__main__': main()
