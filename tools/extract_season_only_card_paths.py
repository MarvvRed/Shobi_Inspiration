#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'catalog_site.json').read_text(encoding='utf-8-sig'))
VAL={str(x.get('code') or '').strip().upper():x for x in json.loads((ROOT/'social-card-main-notes-validated.json').read_text(encoding='utf-8'))}
RAW={str(x.get('code') or '').strip().upper():x for x in json.loads((ROOT/'social-card-main-notes.json').read_text(encoding='utf-8'))}
out=[]
for db,s in zip(DB,SITE):
    if str(s.get('validationStatus') or '').lower()!='yellow': continue
    failed=[k for k,v in (s.get('validationChecks') or {}).items() if not v]
    if failed!=['season']: continue
    c=str(db.get('code') or '').strip().upper(); fid=str(db.get('fragranticaId') or '').strip()
    v=VAL.get(c) or {}; r=RAW.get(c) or {}
    candidates=[]
    for kind,item in [('validated',v),('raw',r)]:
        card=str(item.get('card') or '')
        if str(item.get('fragranticaId') or '').strip()==fid and card and (ROOT/card).is_file():
            candidates.append({'kind':kind,'card':card,'validated':item.get('validated'),'fragranticaId':fid})
    out.append({'code':c,'brand':db.get('brand'),'inspiredBy':db.get('inspiredBy'),'fragranticaId':fid,'fragranticaUrl':db.get('fragranticaUrl'),'cards':candidates})
(ROOT/'season-only-card-paths.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
