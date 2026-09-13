#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'; REPORT=ROOT/'all-identity-card-proof.json'; OUT=ROOT/'all-identity-card-proof-applied.json'
db=json.loads(DB.read_text(encoding='utf-8-sig')); report=json.loads(REPORT.read_text(encoding='utf-8'))
strict={str(r.get('code') or '').strip().upper():r for r in report.get('rows',[]) if r.get('strictProof')}
changed=[]
for row in db:
 c=str(row.get('code') or '').strip().upper(); r=strict.get(c)
 if not r: continue
 fid=str(row.get('fragranticaId') or '').strip(); card=str(r.get('card') or '')
 if not fid or fid!=str(r.get('fid') or '').strip() or not r.get('exactIdFile') or not card or not (ROOT/card).is_file():continue
 if str(row.get('identityStatus') or '').strip().upper() not in {'CONFIRMED','VERIFIED','VALIDATED','OK','MATCH_CORRETTO','MATCH CORRETTO'}:continue
 old=str(row.get('fragranticaVerificationSource') or '')
 if old:continue
 row['fragranticaVerificationSource']=card
 changed.append({'code':c,'fid':fid,'source':card,'brand':row.get('brand'),'inspiredBy':row.get('inspiredBy')})
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
OUT.write_text(json.dumps({'changed':len(changed),'rows':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('changed',len(changed))
