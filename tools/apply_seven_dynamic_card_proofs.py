#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'
VALID=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json'
IMG='database/fragrantica/social-cards/images'
TARGETS={
 '2282-DRC':('81847',['Fig','Green Notes','Rose']),
 '884-RAL':('14446',['Cranberry','Tonka Bean']),
 '236-IND':('42046',['Myrrh','Olibanum (Frankincense)']),
 '945-VER':('28958',['Lemon Blossom','Lemon','Jasmine','Pomegranate','Bergamot','Musk']),
 '525-DRC':('221',['Brazilian Rosewood','Amber','Sandalwood','Aldehydes','Benzoin','Oakmoss']),
 '487-CRT':('12878',['Lily','Green Notes','Citruses']),
 '421-BRB':('13014',['Wormwood','Peach','Rose','Musk','Cashmir wood','Sandalwood']),
}

def code(v):return str(v or '').strip().upper()
rows=json.loads(DB.read_text(encoding='utf-8-sig'))
valid=json.loads(VALID.read_text(encoding='utf-8'))
byrow={code(r.get('code')):r for r in rows}
byvalid={code(r.get('code')):r for r in valid}
changed=[]
for c,(fid,notes) in TARGETS.items():
    r=byrow.get(c)
    if not r: raise SystemExit(f'Missing DB row {c}')
    if str(r.get('fragranticaId') or '')!=fid: raise SystemExit(f'FID drift {c}: {r.get("fragranticaId")} != {fid}')
    card=ROOT/IMG/f'current_{c}_{fid}.jpeg'
    if not card.is_file(): raise SystemExit(f'Missing exact current card {card}')
    r['fragranticaSocialCardNotes']=notes
    r['fragranticaSocialCardStatus']='VALIDATED_SOCIAL_CARD'
    r['fragranticaSocialCardSource']=str(card.relative_to(ROOT))
    v=byvalid.get(c)
    payload={
      'code':c,'fragranticaId':int(fid),'card':str(card.relative_to(ROOT)),
      'validated':True,'mainNotes':notes,
      'rawSlots':[],'validatedSlots':[], 'failures':[],
      'reasons':['DYNAMIC_FULL_CARD_OCR_EXACT_LAYOUT_PROOF']
    }
    if v is None:
        valid.append(payload);byvalid[c]=payload
    else:
        v.clear();v.update(payload)
    changed.append({'code':c,'fid':fid,'notes':notes,'card':str(card.relative_to(ROOT))})
DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
VALID.write_text(json.dumps(valid,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'database/audits/seven-dynamic-card-proofs-applied.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'applied':len(changed),'codes':[x['code'] for x in changed]},ensure_ascii=False))
