#!/usr/bin/env python3
"""Second non-destructive OCR refinement for current-yellow exact-sequence REVIEW rows.

Targets the 37 exact-sequence rows that remain yellow after the first supplemental pass,
including both one-label and two-label failures. A row is promoted only in this report
when every failed label obtains >=2 exact crop reads and zero competing eligible reads.
This script never changes catalog badges.
"""
from __future__ import annotations

import json
from collections import Counter
from PIL import Image

from audit_social_card_order_from_images import ROOT, DB, CROP, code, find_card
from refine_current_yellow_near_pass_ocr import inspect_label

VAL = ROOT / 'database/audits/current-yellow-v2-exact-validation.json'
PILOT = ROOT / 'database/audits/current-yellow-label-ocr-v2.json'
FIRST = ROOT / 'database/audits/current-yellow-near-pass-ocr-refinement.json'
LEXICON = ROOT / 'database/audits/fragrantica-note-lexicon.txt'
OUT = ROOT / 'database/audits/current-yellow-remaining-exact-ocr-refinement.json'


def main():
    val=json.loads(VAL.read_text(encoding='utf-8'))
    pilot=json.loads(PILOT.read_text(encoding='utf-8'))
    first=json.loads(FIRST.read_text(encoding='utf-8')) if FIRST.is_file() else {'rows':[]}
    catalog=json.loads(DB.read_text(encoding='utf-8-sig'))
    by_cat={code(r.get('code')):r for r in catalog}
    by_pilot={code(r.get('code')):r for r in pilot.get('rows',[])}
    already_strong={code(r.get('code')) for r in first.get('rows',[]) if r.get('result')=='SUPPLEMENTAL_STRONG_EXACT'}
    lex=[x.strip() for x in LEXICON.read_text(encoding='utf-8').splitlines() if x.strip()]

    targets=[]
    for r in val.get('rows',[]):
        c=code(r.get('code'))
        if r.get('status')!='REVIEW' or c in already_strong:
            continue
        failed=[x for x in r.get('labels',[]) if not x.get('ok')]
        if failed:
            targets.append((r,failed))

    results=[]
    for i,(vr,failed) in enumerate(targets,1):
        c=code(vr.get('code')); pr=by_pilot.get(c); cat=by_cat.get(c)
        base={'code':c,'fid':str(vr.get('fid') or ''),'failedLabelCount':len(failed)}
        if not pr or not cat:
            results.append({**base,'result':'MISSING_SOURCE','labels':[]}); continue
        card=find_card(cat)
        if not card:
            results.append({**base,'result':'NO_CARD','labels':[]}); continue
        try:
            with Image.open(card) as src:
                sx,sy=src.width/1200,src.height/1200
                x1,y1,x2,y2=CROP
                panel=src.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))).convert('RGB').resize((420,380),Image.Resampling.LANCZOS)
        except Exception as e:
            results.append({**base,'result':'IMAGE_ERROR','error':str(e),'labels':[]}); continue

        label_results=[]
        for fl in failed:
            expected=str(fl.get('note') or '')
            detail=next((d for d in pr.get('details',[]) if d.get('note')==expected),None)
            if not detail:
                label_results.append({'expected':expected,'strongSupplemental':False,'error':'MISSING_DETAIL'})
                continue
            box=detail.get('box')
            if not box or len(box)!=4:
                label_results.append({'expected':expected,'strongSupplemental':False,'error':'NO_BOX'})
                continue
            refined=inspect_label(panel,box,expected,lex)
            label_results.append(refined)

        strong=bool(label_results) and len(label_results)==len(failed) and all(x.get('strongSupplemental') for x in label_results)
        result='SUPPLEMENTAL_STRONG_EXACT_ALL_FAILED_LABELS' if strong else 'STILL_REVIEW'
        results.append({**base,'result':result,'labels':label_results})
        if i%10==0: print(f'processed {i}/{len(targets)}',flush=True)

    counts=Counter(r['result'] for r in results)
    payload={
        'mode':'NON_DESTRUCTIVE_REMAINING_CURRENT_YELLOW_EXACT_OCR_REFINEMENT',
        'excludedAlreadySupplementalStrong':len(already_strong),
        'targets':len(targets),
        'counts':dict(counts),
        'rule':'Every originally failed label must independently obtain >=2 exact crop reads with zero competing eligible reads; no badge changes are made here.',
        'rows':results,
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'targets':len(targets),'excludedAlreadyStrong':len(already_strong),'counts':dict(counts),'output':str(OUT)}))

if __name__=='__main__': main()
