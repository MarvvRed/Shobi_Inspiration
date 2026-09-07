#!/usr/bin/env python3
from __future__ import annotations

import json, re
from difflib import SequenceMatcher
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'social-card-main-notes.json'
LEX=ROOT/'fragrantica-note-lexicon.txt'
OUT=ROOT/'social-card-main-notes-validated.json'
REPORT=ROOT/'social-card-main-notes-validation-report.json'
CROP_1200=(48,738,448,1097)
COLS=[(5,135),(135,270),(270,400)]
ROWS=[(154,226),(302,359)]

def norm(s):
    s=str(s or '').lower().replace('’',"'").replace('–','-').replace('—','-')
    s=re.sub(r'[^a-z0-9à-ž]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def toks(s):
    return [x for x in norm(s).split() if x]

def score(raw,cand):
    a=norm(raw); b=norm(cand)
    if not a or not b: return 0.0
    if a==b: return 1.0
    seq=SequenceMatcher(None,a,b).ratio()
    ta=' '.join(sorted(toks(raw))); tb=' '.join(sorted(toks(cand)))
    ts=SequenceMatcher(None,ta,tb).ratio()
    best=max(seq,ts)
    # Strong, conservative allowance for obvious OCR debris around a full note name.
    if len(b)>=5 and (a.startswith(b+' ') or a.endswith(' '+b)): best=max(best,0.94)
    if len(a)>=5 and (b.startswith(a+' ') or b.endswith(' '+a)): best=max(best,0.90)
    return best

def build_matcher(names):
    vals=[(n,norm(n)) for n in names if norm(n)]
    exact={nn:n for n,nn in vals}
    def match(raw):
        nr=norm(raw)
        if nr in exact: return exact[nr],1.0,1.0
        ranked=sorted(((score(raw,n),n) for n,_ in vals),reverse=True)
        best_s,best_n=ranked[0]; second_s=ranked[1][0] if len(ranked)>1 else 0.0
        margin=best_s-second_s
        L=len(nr.replace(' ',''))
        ok=False
        if L<=4:
            ok=best_s>=0.96 and margin>=0.08
        elif best_s>=0.94 and margin>=0.025:
            ok=True
        elif best_s>=0.89 and margin>=0.06:
            ok=True
        elif best_s>=0.85 and margin>=0.12:
            ok=True
        return (best_n if ok else None),best_s,margin
    return match

def occupancy(card_rel):
    p=ROOT/card_rel
    try:
        im=Image.open(p).convert('L')
    except Exception:
        return []
    x1,y1,x2,y2=CROP_1200
    sx=im.width/1200.0; sy=im.height/1200.0
    panel=im.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))).resize((400,359))
    occ=[]
    for ry,(ya,yb) in enumerate(ROWS):
        for cx,(xa,xb) in enumerate(COLS):
            # Inner label zone avoids card borders and neighbouring tiles.
            z=panel.crop((xa+5,ya+2,xb-5,yb-2))
            hist=z.histogram()
            dark=sum(hist[:175]); very_dark=sum(hist[:120]); total=z.width*z.height
            # Printed labels produce many dark/medium-dark pixels; an empty cell does not.
            if dark/max(total,1) > 0.004 or very_dark/max(total,1) > 0.0015:
                occ.append(ry*3+cx+1)
    return occ

def main():
    raw=json.loads(RAW.read_text(encoding='utf-8'))
    lex=[x.strip() for x in LEX.read_text(encoding='utf-8').splitlines() if x.strip()]
    match=build_matcher(lex)
    out=[]; reasons={}; validated=0
    samples=[]; badsamples=[]
    for item in raw:
        slots=item.get('slots') or []
        raw_slot_ids=[int(s.get('slot')) for s in slots if s.get('slot')]
        occ=occupancy(item.get('card',''))
        fixed=[]; failures=[]
        for s in slots:
            rawname=s.get('name','')
            n,sc,margin=match(rawname)
            if not n:
                failures.append({'slot':s.get('slot'),'raw':rawname,'bestScore':round(sc,3),'margin':round(margin,3)})
            else:
                fixed.append({'slot':s.get('slot'),'name':n,'raw':rawname,'matchScore':round(sc,3),'margin':round(margin,3),'ocrConfidence':s.get('ocrConfidence')})
        reason=[]
        if not slots: reason.append('NO_OCR_SLOTS')
        if raw_slot_ids != occ: reason.append('VISUAL_OCCUPANCY_MISMATCH')
        if failures: reason.append('LEXICON_UNCERTAIN')
        if any((s.get('ocrConfidence') or 0)<65 for s in slots): reason.append('LOW_OCR_TOKEN_CONFIDENCE')
        ok=bool(slots) and not reason
        if ok: validated+=1
        for r in reason: reasons[r]=reasons.get(r,0)+1
        rec={
            'code':item.get('code'),'fragranticaId':item.get('fragranticaId'),'card':item.get('card'),
            'validated':ok,'mainNotes':[x['name'] for x in fixed] if ok else [],
            'rawSlots':slots,'visualOccupiedSlots':occ,'validatedSlots':fixed,'failures':failures,'reasons':reason,
        }
        out.append(rec)
        slim={'code':rec['code'],'fragranticaId':rec['fragranticaId'],'mainNotes':rec['mainNotes'],'raw':[s.get('name') for s in slots],'occ':occ}
        if ok and len(samples)<40: samples.append(slim)
        if not ok and len(badsamples)<40: badsamples.append({**slim,'reasons':reason,'failures':failures})
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={
        'rule':'Validation uses ONLY social-card pixels/OCR plus the official Fragrantica global notes lexicon; perfume pyramid is never consulted.',
        'official_fragrantica_lexicon_notes':len(lex),'raw_cards':len(raw),'validated_cards':validated,'unresolved_cards':len(raw)-validated,
        'reason_counts':reasons,'validated_sample':samples,'unresolved_sample':badsamples,
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
