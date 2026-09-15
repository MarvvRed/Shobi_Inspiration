#!/usr/bin/env python3
from __future__ import annotations
import json,re,difflib
from pathlib import Path
from PIL import Image
import pytesseract

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'database/audits/validation-yellow-report.json'
DB=ROOT/'database/catalog/database_complete.json'
MAP=ROOT/'database'/'assets'/'note-icons'/'map.js'
IMGDIR=ROOT/'database/fragrantica'/'social-cards'/'images'
OUT=ROOT/'database/audits/remaining-card-dynamic-analysis.json'

def norm(s):
    s=str(s or '').lower().replace('&',' and ')
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return re.sub(r'\s+',' ',s).strip()

def parse_gender(text):
    t=norm(text)
    if re.search(r'\bfor women and men\b|\bfor men and women\b',t): return 'unisex'
    if re.search(r'\bfor women\b',t): return 'female'
    if re.search(r'\bfor men\b',t): return 'male'
    return ''

def load_note_lexicon():
    txt=MAP.read_text(encoding='utf-8')
    m=re.search(r'window\.FRAGRANTICA_NOTE_ICON_MAP\s*=\s*(\{.*\})\s*;?\s*$',txt,re.S)
    if not m: raise SystemExit('Cannot parse note-icons/map.js')
    obj=json.loads(m.group(1))
    return {norm(k):k for k in obj.keys() if norm(k)}

def card_path(code,fid):
    p=IMGDIR/f'current_{code}_{fid}.jpeg'
    if p.is_file(): return p
    hits=list(IMGDIR.glob(f'*{code}*{fid}*.jpeg'))+list(IMGDIR.glob(f'*{code}*{fid}*.jpg'))+list(IMGDIR.glob(f'*{code}*{fid}*.png'))
    return hits[0] if hits else None

def ocr_words(im):
    d=pytesseract.image_to_data(im,config='--psm 11',lang='eng',output_type=pytesseract.Output.DICT)
    out=[]
    for i,t in enumerate(d['text']):
        t=str(t or '').strip()
        if not t: continue
        try: conf=float(d['conf'][i])
        except: conf=-1
        out.append({'text':t,'conf':conf,'x':int(d['left'][i]),'y':int(d['top'][i]),'w':int(d['width'][i]),'h':int(d['height'][i])})
    return out

def match_note(text,lex):
    n=norm(text)
    if not n:return None,0.0
    if n in lex:return lex[n],1.0
    best=None;score=0.0
    for nk,orig in lex.items():
        # avoid dangerous fuzzy matches for very short note names
        if len(nk)<4 or len(n)<4: continue
        r=difflib.SequenceMatcher(None,n,nk).ratio()
        if r>score:
            best,score=orig,r
    if score>=0.90:return best,score
    return None,score

def analyze_notes(words,w,h,lex):
    anchors=[z for z in words if norm(z['text'])=='notes' and z['x']<0.45*w and z['y']>0.45*h]
    if not anchors:return {'anchor':None,'clusters':[],'matchedNotes':[]}
    a=min(anchors,key=lambda z:z['y'])
    # note labels live below the Notes heading and left of the profile/seasons panel
    cand=[z for z in words if z['conf']>=35 and z['x']<0.43*w and z['y']>a['y']+0.035*h and z['y']<0.94*h]
    # cluster by horizontal center: wrapped multi-word labels stay in same column
    clusters=[]
    for z in sorted(cand,key=lambda q:(q['x']+q['w']/2,q['y'])):
        cx=z['x']+z['w']/2
        target=None
        for c in clusters:
            if abs(cx-c['cx'])<=45:
                target=c;break
        if target is None:
            target={'cx':cx,'words':[]};clusters.append(target)
        target['words'].append(z)
        target['cx']=sum(q['x']+q['w']/2 for q in target['words'])/len(target['words'])
    result=[];matched=[]
    for c in sorted(clusters,key=lambda q:q['cx']):
        ws=sorted(c['words'],key=lambda q:(q['y'],q['x']))
        text=' '.join(q['text'] for q in ws)
        note,score=match_note(text,lex)
        # Also test short contiguous subsets because OCR noise may share a cluster.
        if not note:
            toks=[q['text'] for q in ws]
            for size in range(min(4,len(toks)),0,-1):
                for i in range(len(toks)-size+1):
                    n2,s2=match_note(' '.join(toks[i:i+size]),lex)
                    if n2 and s2>score:
                        note,score=n2,s2
        result.append({'cx':round(c['cx'],1),'text':text,'note':note,'score':round(score,3)})
        if note and note not in matched:matched.append(note)
    return {'anchor':{'x':a['x'],'y':a['y']},'clusters':result,'matchedNotes':matched}

def main():
    report=json.loads(REPORT.read_text(encoding='utf-8'))
    db=json.loads(DB.read_text(encoding='utf-8-sig'))
    bycode={str(r.get('code') or '').upper():r for r in db}
    lex=load_note_lexicon()
    targets=[]
    for y in report.get('rows',report.get('yellowRows',[])):
        code=str(y.get('code') or '').upper(); failed=y.get('failedChecks') or y.get('failed') or []
        row=bycode.get(code) or {}
        fid=str(row.get('fragranticaId') or '')
        if fid and ('socialCard' in failed or 'notes' in failed or 'gender' in failed):targets.append((code,fid,row,failed))
    out=[]
    for code,fid,row,failed in targets:
        p=card_path(code,fid)
        if not p:
            out.append({'code':code,'fid':fid,'error':'card missing'});continue
        with Image.open(p) as im:
            im=im.convert('RGB'); w,h=im.size; words=ocr_words(im)
        full=' '.join(z['text'] for z in sorted(words,key=lambda q:(q['y'],q['x'])))
        top=' '.join(z['text'] for z in words if z['y']<0.18*h)
        notes=analyze_notes(words,w,h,lex)
        existing=row.get('mainNotes') or row.get('notes') or []
        if isinstance(existing,str): existing=[x.strip() for x in existing.split(',') if x.strip()]
        existing_norm=[norm(x) for x in existing]
        matched_norm=[norm(x) for x in notes['matchedNotes']]
        existing_proven=bool(existing_norm) and all(x in matched_norm for x in existing_norm)
        out.append({'code':code,'fid':fid,'failed':failed,'card':str(p.relative_to(ROOT)),'size':[w,h],
                    'gender':parse_gender(top),'topText':top,'existingNotes':existing,
                    'matchedNotes':notes['matchedNotes'],'existingNotesProven':existing_proven,
                    'noteClusters':notes['clusters'],'fullText':full})
    payload={'count':len(out),'rows':out}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'count':len(out),'provenExistingNotes':sum(1 for x in out if x.get('existingNotesProven')),'genderFound':sum(1 for x in out if x.get('gender'))},ensure_ascii=False))
if __name__=='__main__':main()
