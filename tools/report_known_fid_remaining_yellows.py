#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
db=json.loads((ROOT/'database/catalog/database_complete.json').read_text(encoding='utf-8-sig'));site=json.loads((ROOT/'database/catalog/catalog_site.json').read_text(encoding='utf-8-sig'))
rows=[]
for d,s in zip(db,site):
 if str(s.get('validationStatus') or '').lower()!='yellow':continue
 if not str(d.get('fragranticaId') or '').strip():continue
 checks=s.get('validationChecks') or {}
 rows.append({'code':d.get('code'),'brand':d.get('brand'),'inspiredBy':d.get('inspiredBy'),'fid':d.get('fragranticaId'),'url':d.get('fragranticaUrl'),'identityStatus':d.get('identityStatus'),'verificationSource':d.get('fragranticaVerificationSource'),'gender':d.get('gender'),'genderAffinity':d.get('genderAffinity'),'notes':d.get('fragranticaSocialCardNotes') or [],'failed':[k for k,v in checks.items() if not v]})
out={'count':len(rows),'rows':rows};(ROOT/'database/audits/known-fid-remaining-yellows.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
