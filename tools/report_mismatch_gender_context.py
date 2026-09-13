#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'))
MIS=json.loads((ROOT/'fid-mismatch-yellows.json').read_text(encoding='utf-8'))
by={str(r.get('code') or '').strip().upper():r for r in DB}
rows=[]
for x in MIS.get('rows',[]):
 c=str(x.get('code') or '').strip().upper();r=by.get(c,{})
 rows.append({'code':c,'brand':r.get('brand'),'inspiredBy':r.get('inspiredBy'),'gender':r.get('gender'),'genderAffinity':r.get('genderAffinity'),'genderStatus':r.get('genderStatus'),'currentFid':x.get('currentFid'),'validatedFid':x.get('validatedFid'),'currentNotes':r.get('fragranticaSocialCardNotes') or []})
out={'rows':rows};(ROOT/'fid-mismatch-gender-context.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
