#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
db=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'))
site=json.loads((ROOT/'catalog_site.json').read_text(encoding='utf-8-sig'))
rows=[]
for d,s in zip(db,site):
    checks=s.get('validationChecks') or {}
    fails=[k for k,v in checks.items() if not v]
    if str(s.get('validationStatus') or '').lower()=='yellow' and fails==['identity']:
        rows.append({k:d.get(k) for k in ('code','brand','inspiredBy','fragranticaId','fragranticaUrl','identityStatus','fragranticaVerificationSource')})
out={'count':len(rows),'rows':rows}
(ROOT/'identity-only-current.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
