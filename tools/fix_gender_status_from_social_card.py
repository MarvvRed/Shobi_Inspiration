#!/usr/bin/env python3
"""Mark gender verified only when exact local Social Card evidence agrees.
No gender value is guessed or changed.
"""
import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'
GS=ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv'
rows=json.loads(DB.read_text(encoding='utf-8-sig'))

def norm(v):
    s=str(v or '').strip().lower()
    return {'female':'feminine','woman':'feminine','women':'feminine','male':'masculine','man':'masculine','men':'masculine','unisex':'unisex'}.get(s,s)
def code(r): return str(r.get('code') or '').strip().upper()

with GS.open(encoding='utf-8-sig',newline='') as f:
    evidence={str(x.get('shobi_code') or '').strip().upper():x for x in csv.DictReader(f)}

changed=[]
for r in rows:
    c=code(r); e=evidence.get(c)
    if not e: continue
    fid=str(r.get('fragranticaId') or '').strip()
    efid=str(e.get('fragrantica_id') or '').strip()
    current=norm(r.get('gender') or r.get('genderAffinity'))
    observed=norm(e.get('gender'))
    source=str(e.get('gender_source') or '').strip().upper()
    local=str(e.get('local_path') or '').strip()
    if not (fid and fid==efid and current and observed and current==observed): continue
    if source!='SOCIAL_CARD_OCR': continue
    if not local or not (ROOT/local).is_file(): continue
    if str(r.get('genderStatus') or '').strip().upper()=='VALIDATED_SOCIAL_CARD': continue
    r['genderStatus']='VALIDATED_SOCIAL_CARD'
    r['genderVerificationSource']=local
    r['genderVerificationFragranticaId']=fid
    changed.append(c)

DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'database/audits/gender-status-social-card-fixes.json').write_text(json.dumps({'changed':len(changed),'codes':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('gender_status_fixed',len(changed))
