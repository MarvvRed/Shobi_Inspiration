#!/usr/bin/env python3
"""Correct catalog Main Notes from exact already-validated Social Card metadata.

Only rows with the same Shobi code, same Fragrantica ID, validated=true, an existing
local card file, and a non-empty validated ordered note list are eligible.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'
SITE=ROOT/'catalog_site.json'
VAL=ROOT/'social-card-main-notes-validated.json'
rows=json.loads(DB.read_text(encoding='utf-8-sig'))
site=json.loads(SITE.read_text(encoding='utf-8-sig'))
validated={str(x.get('code') or '').strip().upper():x for x in json.loads(VAL.read_text(encoding='utf-8'))}

changes=[]
for db,s in zip(rows,site):
    code=str(db.get('code') or '').strip().upper()
    fid=str(db.get('fragranticaId') or '').strip()
    src=validated.get(code)
    if not src or src.get('validated') is not True: continue
    if str(src.get('fragranticaId') or '').strip()!=fid: continue
    card=str(src.get('card') or '').strip()
    if not card or not (ROOT/card).is_file(): continue
    new=list(src.get('mainNotes') or [])
    if not new or any(not str(x).strip() for x in new): continue
    old=list(db.get('fragranticaSocialCardNotes') or [])
    if old==new: continue
    # Restrict to rows whose current strict audit is failing Social Card / notes;
    # this avoids changing unrelated historical rows.
    checks=(db.get('validationAudit') or {}).get('checks') or {}
    if checks.get('socialCard',True) or checks.get('notes',True): continue
    db['fragranticaSocialCardNotes']=new
    db['fragranticaSocialCardStatus']='VALIDATED_OCR'
    db['fragranticaSocialCardVerificationSource']=card
    db['fragranticaSocialCardVerificationFragranticaId']=fid
    if 'fragranticaSocialCardNotes' in s: s['fragranticaSocialCardNotes']=new
    changes.append({'code':code,'fragranticaId':fid,'source':card,'oldNotes':old,'validatedNotes':new})

DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
(ROOT/'exact-validated-note-corrections.json').write_text(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('exact_validated_note_corrections',len(changes))
