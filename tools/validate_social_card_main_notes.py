#!/usr/bin/env python3
from __future__ import annotations

import json, re
from difflib import SequenceMatcher
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'social-card-main-notes.json'; LEX=ROOT/'fragrantica-note-lexicon.txt'
OUT=ROOT/'social-card-main-notes-validated.json'; REPORT=ROOT/'social-card-main-notes-validation-report.json'

def norm(s):
    s=str(s or '').lower().replace('’',"'").replace('–','-').replace('—','-')
    s=re.sub(r'[^a-z0-9à-ž]+',' ',s); return re.sub(r'\s+',' ',s).strip()
def toks(s): return [x for x in norm(s).split() if x]
def score(raw,cand):
    a=norm(raw);b=norm(cand)
    if not a or not b:return 0.0
    if a==b:return 1.0
    best=max(SequenceMatcher(None,a,b).ratio(),SequenceMatcher(None,' '.join(sorted(toks(raw))),' '.join(sorted(toks(cand)))).ratio())
    if len(b)>=3 and (a.startswith(b+' ') or a.endswith(' '+b)):best=max(best,.97)
    if len(b)>=4 and b in a:best=max(best,.93)
    return best

def build_matcher(names):
    vals=[n for n in names if norm(n)];exact={norm(n):n for n in vals}
    def match(raw):
        nr=norm(raw)
        if not nr:return None,0,0
        if nr in exact:return exact[nr],1,1
        ranked=sorted(((score(raw,n),n) for n in vals),reverse=True);bs,bn=ranked[0];ss=ranked[1][0] if len(ranked)>1 else 0;margin=bs-ss;L=len(nr.replace(' ',''))
        ok=(L<=3 and bs>=.92 and margin>=.08) or (L>3 and (bs>=.90 or (bs>=.84 and margin>=.025) or (bs>=.78 and margin>=.08)))
        return (bn if ok else None),bs,margin
    return match

def main():
    raw=json.loads(RAW.read_text(encoding='utf-8'));lex=[x.strip() for x in LEX.read_text(encoding='utf-8').splitlines() if x.strip()];match=build_matcher(lex)
    out=[];reasons={};validated=partial=0;samples=[];bad=[]
    for item in raw:
        slots=sorted(item.get('slots') or [],key=lambda s:int(s.get('slot') or 999));fixed=[];fail=[]
        for s in slots:
            n,sc,margin=match(s.get('name',''))
            if n:fixed.append({'slot':s.get('slot'),'name':n,'raw':s.get('name',''),'matchScore':round(sc,3),'margin':round(margin,3),'ocrConfidence':s.get('ocrConfidence')})
            else:fail.append({'slot':s.get('slot'),'raw':s.get('name',''),'bestScore':round(sc,3),'margin':round(margin,3),'ocrConfidence':s.get('ocrConfidence')})
        why=[]
        if not slots:why.append('NO_OCR_SLOTS')
        if fail:why.append('LEXICON_UNCERTAIN')
        ok=bool(slots) and not fail
        if ok:validated+=1
        elif fixed:partial+=1
        for r in why:reasons[r]=reasons.get(r,0)+1
        rec={'code':item.get('code'),'fragranticaId':item.get('fragranticaId'),'card':item.get('card'),'validated':ok,'mainNotes':[x['name'] for x in fixed] if ok else [],'rawSlots':slots,'validatedSlots':fixed,'failures':fail,'reasons':why};out.append(rec)
        slim={'code':rec['code'],'fragranticaId':rec['fragranticaId'],'mainNotes':rec['mainNotes'],'raw':[s.get('name') for s in slots]}
        if ok and len(samples)<50:samples.append(slim)
        if not ok and len(bad)<50:bad.append({**slim,'reasons':why,'failures':fail})
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'rule':'Main notes are read ONLY from ordered OCR slots of the archived Fragrantica social-card notes panel. The perfume pyramid is never consulted and slot order is never changed.','official_fragrantica_lexicon_notes':len(lex),'raw_cards':len(raw),'validated_cards':validated,'unresolved_cards':len(raw)-validated,'partially_read_but_not_accepted':partial,'reason_counts':reasons,'validated_sample':samples,'unresolved_sample':bad}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
