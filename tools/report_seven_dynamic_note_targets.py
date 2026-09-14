#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CODES={'2282-DRC','884-RAL','236-IND','945-VER','525-DRC','487-CRT','421-BRB'}
valid=json.loads((ROOT/'social-card-main-notes-validated.json').read_text(encoding='utf-8'))
raw=json.loads((ROOT/'social-card-main-notes.json').read_text(encoding='utf-8'))
db=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'))
def idx(rows):return {str(x.get('code') or '').strip().upper():x for x in rows}
iv,ir,idb=idx(valid),idx(raw),idx(db)
out=[]
for code in sorted(CODES):
 r=idb.get(code,{})
 out.append({'code':code,'fid':str(r.get('fragranticaId') or ''),'dbNotes':r.get('fragranticaSocialCardNotes'),
             'dbStatus':r.get('fragranticaSocialCardStatus'),'validated':iv.get(code),'raw':ir.get(code)})
(ROOT/'seven-dynamic-note-targets.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'count':len(out)},ensure_ascii=False))
