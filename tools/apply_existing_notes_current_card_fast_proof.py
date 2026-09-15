#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; VALID=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json'; PROOF=ROOT/'database/audits/existing-notes-current-card-fast-proof.json'; OUT=ROOT/'database/audits/existing-notes-current-card-fast-applied.json'
def code(v): return str(v or '').strip().upper()
db=json.loads(DB.read_text(encoding='utf-8-sig')); valid=json.loads(VALID.read_text(encoding='utf-8')); proof=json.loads(PROOF.read_text(encoding='utf-8'))
bydb={code(x.get('code')):x for x in db}; byv={code(x.get('code')):x for x in valid}
applied=[]
for p in proof.get('rows',[]):
    if p.get('uniqueProof') is not True: continue
    c=code(p.get('code')); row=bydb.get(c)
    if not row: continue
    fid=str(p.get('fid') or '')
    if str(row.get('fragranticaId') or '')!=fid: continue
    notes=list(p.get('notes') or []); card=str(p.get('card') or '')
    if not notes or not card or not (ROOT/card).is_file(): continue
    row['fragranticaSocialCardNotes']=notes
    row['fragranticaSocialCardStatus']='VALIDATED_OCR'
    patterns=p.get('passingPatterns') or []
    slots=patterns[0] if len(patterns)==1 else list(range(1,len(notes)+1))
    byv[c]={
      'code':c,'fragranticaId':int(fid) if fid.isdigit() else fid,'card':card,'validated':True,'mainNotes':notes,
      'rawSlots':[{'slot':int(sl),'name':n,'ocrConfidence':None} for n,sl in zip(notes,slots)],
      'validatedSlots':[{'slot':int(sl),'name':n,'raw':'CURRENT_FID_FAST_EXACT_PROOF','matchScore':1.0,'margin':None} for n,sl in zip(notes,slots)],
      'failures':[],'reasons':[],'validationMethod':'CURRENT_FID_FAST_EXACT_PROOF'
    }
    applied.append({'code':c,'fid':fid,'card':card,'notes':notes,'slots':slots})
seen=set(); rebuilt=[]
for x in valid:
    c=code(x.get('code')); rebuilt.append(byv.get(c,x)); seen.add(c)
for c,x in byv.items():
    if c not in seen: rebuilt.append(x)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
VALID.write_text(json.dumps(rebuilt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
OUT.write_text(json.dumps({'applied':len(applied),'rows':applied},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'applied':len(applied),'codes':[x['code'] for x in applied]},ensure_ascii=False))
