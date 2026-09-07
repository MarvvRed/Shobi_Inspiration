#!/usr/bin/env python3
from __future__ import annotations

import json, re
from difflib import SequenceMatcher
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'social-card-main-notes.json'
LEX=ROOT/'fragrantica-note-lexicon.txt'
OUT=ROOT/'social-card-main-notes-validated.json'
REPORT=ROOT/'social-card-main-notes-validation-report.json'

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
    # OCR often leaves a few icon/edge characters before or after the printed note.
    if len(b)>=3 and (a.startswith(b+' ') or a.endswith(' '+b)): best=max(best,0.97)
    if len(b)>=4 and b in a: best=max(best,0.93)
    return best

def build_matcher(names):
    vals=[n for n in names if norm(n)]
    exact={norm(n):n for n in vals}
    def match(raw):
        nr=norm(raw)
        if not nr: return None,0.0,0.0
        if nr in exact: return exact[nr],1.0,1.0
        ranked=sorted(((score(raw,n),n) for n in vals),reverse=True)
        best_s,best_n=ranked[0]
        second_s=ranked[1][0] if len(ranked)>1 else 0.0
        margin=best_s-second_s
        L=len(nr.replace(' ',''))
        # We only normalize OCR text to a real Fragrantica note name. We never infer
        # missing notes, never consult the perfume pyramid, and never change slot order.
        if L<=3:
            ok=best_s>=0.92 and margin>=0.08
        elif best_s>=0.90:
            ok=True
        elif best_s>=0.84 and margin>=0.025:
            ok=True
        elif best_s>=0.78 and margin>=0.08:
            ok=True
        else:
            ok=False
        return (best_n if ok else None),best_s,margin
    return match

def main():
    raw=json.loads(RAW.read_text(encoding='utf-8'))
    lex=[x.strip() for x in LEX.read_text(encoding='utf-8').splitlines() if x.strip()]
    match=build_matcher(lex)
    out=[]; reasons={}; validated=0; partial=0
    samples=[]; badsamples=[]

    for item in raw:
        slots=sorted(item.get('slots') or [], key=lambda s:int(s.get('slot') or 999))
        fixed=[]; failures=[]
        for s in slots:
            rawname=s.get('name','')
            n,sc,margin=match(rawname)
            if not n:
                failures.append({'slot':s.get('slot'),'raw':rawname,'bestScore':round(sc,3),'margin':round(margin,3),'ocrConfidence':s.get('ocrConfidence')})
            else:
                fixed.append({'slot':s.get('slot'),'name':n,'raw':rawname,'matchScore':round(sc,3),'margin':round(margin,3),'ocrConfidence':s.get('ocrConfidence')})

        reason=[]
        if not slots: reason.append('NO_OCR_SLOTS')
        if failures: reason.append('LEXICON_UNCERTAIN')
        ok=bool(slots) and not failures
        if ok:
            validated+=1
        elif fixed:
            partial+=1
        for r in reason: reasons[r]=reasons.get(r,0)+1

        rec={
            'code':item.get('code'),'fragranticaId':item.get('fragranticaId'),'card':item.get('card'),
            'validated':ok,
            'mainNotes':[x['name'] for x in fixed] if ok else [],
            'rawSlots':slots,'validatedSlots':fixed,'failures':failures,'reasons':reason,
        }
        out.append(rec)
        slim={'code':rec['code'],'fragranticaId':rec['fragranticaId'],'mainNotes':rec['mainNotes'],'raw':[s.get('name') for s in slots]}
        if ok and len(samples)<50: samples.append(slim)
        if not ok and len(badsamples)<50: badsamples.append({**slim,'reasons':reason,'failures':failures})

    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={
        'rule':'Main notes are read ONLY from ordered OCR slots of the archived Fragrantica social-card notes panel. The perfume pyramid is never consulted and slot order is never changed.',
        'official_fragrantica_lexicon_notes':len(lex),
        'raw_cards':len(raw),
        'validated_cards':validated,
        'unresolved_cards':len(raw)-validated,
        'partially_read_but_not_accepted':partial,
        'reason_counts':reasons,
        'validated_sample':samples,
        'unresolved_sample':badsamples,
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
