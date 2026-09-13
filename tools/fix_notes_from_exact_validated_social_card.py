#!/usr/bin/env python3
"""Recover Main Notes only from an exact already-validated Social Card record."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'
VAL=ROOT/'social-card-main-notes-validated.json'
rows=json.loads(DB.read_text(encoding='utf-8-sig'))
validated={str(x.get('code') or '').strip().upper():x for x in json.loads(VAL.read_text(encoding='utf-8'))}
changed=[]
for r in rows:
    c=str(r.get('code') or '').strip().upper(); fid=str(r.get('fragranticaId') or '').strip()
    if not c or not fid: continue
    v=validated.get(c)
    if not v or v.get('validated') is not True: continue
    if str(v.get('fragranticaId') or '').strip()!=fid: continue
    card=str(v.get('card') or '')
    expected=f'_{r.get("code")}_{fid}.jpeg'
    if not card.endswith(expected) or not (ROOT/card).is_file(): continue
    notes=v.get('mainNotes') or []
    if not isinstance(notes,list) or not notes or any(not isinstance(n,str) or not n.strip() for n in notes): continue
    old=r.get('fragranticaSocialCardNotes') or []
    # Source is already explicitly validated for this exact code+FID+local card.
    if old!=notes or str(r.get('fragranticaSocialCardStatus') or '').strip().upper() not in {'VALIDATED_OCR','VALIDATED_MANUAL','VALIDATED_SOCIAL_CARD'}:
        r['fragranticaSocialCardNotes']=notes
        r['fragranticaSocialCardStatus']='VALIDATED_OCR'
        r['fragranticaSocialCardVerificationSource']=card
        r['fragranticaSocialCardVerificationFragranticaId']=fid
        changed.append({'code':c,'fragranticaId':fid,'notes':notes,'card':card})
DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'exact-validated-social-card-note-fixes.json').write_text(json.dumps({'changed':len(changed),'rows':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('validated_social_card_note_fixes',len(changed))
