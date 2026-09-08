#!/usr/bin/env python3
from __future__ import annotations
import json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DBS=[ROOT/'database_complete.json',ROOT/'database_v2_clean.json']
CARDS=ROOT/'fragrantica-scraper-archive'/'social-cards'
IMAGES=CARDS/'images'
CAND=CARDS/'candidate-images'
VALID=ROOT/'social-card-main-notes-validated.json'
MANUAL_DIR=ROOT/'social-card-note-review'
REPORT=ROOT/'social-card-main-notes-final-report.json'

FINAL_IDS={
 '521-DRC':('Dior','Dior Addict',215,'https://www.fragrantica.com/perfume/Dior/Dior-Addict-215.html'),
 '676-GUC':('Gucci','Flora by Gucci Eau de Toilette',5226,'https://www.fragrantica.com/perfume/Gucci/Flora-by-Gucci-Eau-de-Toilette-5226.html'),
}
UNAVAILABLE={'118-HAM':27808,'235-HOLL':4307,'325-PECK':31590}

def flatten(data):
    if isinstance(data,list) and data and isinstance(data[0],dict) and isinstance(data[0].get('perfumes'),list):
        return [p for b in data for p in b.get('perfumes',[])]
    return data if isinstance(data,list) else []

def code(p): return str(p.get('id') or p.get('code') or p.get('shobiCode') or '').strip()
def status(p): return str(p.get('fragranticaStatus') or p.get('fragrantica_status') or '')
def fid(p):
    try:return int(p.get('fragranticaId')) if p.get('fragranticaId') not in (None,'') else None
    except:return None

def prepare():
    IMAGES.mkdir(parents=True,exist_ok=True)
    for c,(_,_,f,_) in FINAL_IDS.items():
        src=CAND/f'{c}_{f}.jpeg'
        if not src.exists(): raise SystemExit(f'Missing confirmed candidate card: {src}')
        dst=IMAGES/f'confirmed_{c}_{f}.jpeg'
        if not dst.exists(): shutil.copy2(src,dst)
    for path in DBS:
        data=json.loads(path.read_text(encoding='utf-8')); recs=flatten(data); seen=set()
        for p in recs:
            c=code(p)
            if c in FINAL_IDS:
                brand,name,f,url=FINAL_IDS[c]; p['brand']=brand;p['inspiredBy']=name;p['fragranticaId']=f;p['fragranticaUrl']=url
                p['fragranticaStatus']='VERIFIED_SHOBI_FIRST';p['fragranticaVerificationSource']='social-card-main-notes-final-report.json';seen.add(c)
            if c in UNAVAILABLE:
                if fid(p)!=UNAVAILABLE[c]: raise SystemExit(f'{path.name}: unexpected FID for {c}: {fid(p)}')
                p['fragranticaSocialCardStatus']='SOCIAL_CARD_UNAVAILABLE'
        if seen!=set(FINAL_IDS): raise SystemExit(f'{path.name}: missing final identities {set(FINAL_IDS)-seen}')
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Prepared confirmed cards and final identities')

def load_manual():
    out={}
    for p in sorted(MANUAL_DIR.glob('manual-*.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            r=json.loads(line); f=int(r['fragranticaId']); notes=r.get('mainNotes') or []
            if f in out and out[f]!=notes: raise SystemExit(f'Conflicting manual notes for FID {f}')
            out[f]=notes
    return out

def missing_identity(rows):
    return [(r.get('code'),r.get('fragranticaId'),r.get('reason')) for r in rows]

def merge():
    val=json.loads(VALID.read_text(encoding='utf-8')); auto={int(r['fragranticaId']):r['mainNotes'] for r in val if r.get('validated') and r.get('mainNotes')}
    manual=load_manual(); merged={**auto,**manual}
    oud_manual=manual.get(83842); oud_raw=next((r.get('rawSlots') for r in val if int(r.get('fragranticaId') or -1)==83842),None)
    counts=[]; missing_reference=[]
    for path in DBS:
        data=json.loads(path.read_text(encoding='utf-8')); recs=flatten(data); official=with_notes=unavail=0; missing=[]
        for p in recs:
            if status(p).upper().startswith('RESOLVED_NO_FORCE'): continue
            official+=1; f=fid(p); notes=list(merged.get(f,[])) if f is not None else []
            p['fragranticaSocialCardNotes']=notes
            if code(p) in UNAVAILABLE:
                p['fragranticaSocialCardStatus']='SOCIAL_CARD_UNAVAILABLE'; p['fragranticaSocialCardNotes']=[];unavail+=1
            elif notes:
                p['fragranticaSocialCardStatus']='VALIDATED_MANUAL' if f in manual else 'VALIDATED_OCR';with_notes+=1
            else:p['fragranticaSocialCardStatus']='UNRESOLVED_NO_INFERENCE'
            if not p['fragranticaSocialCardNotes']:
                missing.append({
                    'code':code(p),
                    'brand':p.get('brand'),
                    'perfume':p.get('inspiredBy') or p.get('name') or p.get('perfume'),
                    'fragranticaId':f,
                    'fragranticaUrl':p.get('fragranticaUrl'),
                    'reason':p.get('fragranticaSocialCardStatus')
                })
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        counts.append({'database':path.name,'official':official,'withMainNotes':with_notes,'socialCardUnavailable':unavail,'withoutMainNotes':official-with_notes})
        if not missing_reference: missing_reference=missing
        elif missing_identity(missing)!=missing_identity(missing_reference): raise SystemExit('Databases disagree on identities of perfumes without Main Notes')
    report={'rule':'Main Notes come only from the left notes box of exact Fragrantica social cards; no accords, pyramid, fallback or inference.',
      'finalIdentityDecisions':{'521-DRC':215,'676-GUC':5226},'socialCardUnavailable':UNAVAILABLE,
      'validatedOcrFids':len(auto),'manualReviewedFids':len(manual),'mergedFidsWithNotes':len(merged),
      'oudMaracuja83842':{'manualNotes':oud_manual,'ocrRawSlots':oud_raw,'decision':'KEEP_MANUAL_VISUAL_REVIEW'},
      'databases':counts,'perfumesWithoutMainNotes':missing_reference}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
 import sys
 if len(sys.argv)!=2 or sys.argv[1] not in {'prepare','merge'}: raise SystemExit('usage: finalize_social_card_main_notes.py prepare|merge')
 prepare() if sys.argv[1]=='prepare' else merge()
