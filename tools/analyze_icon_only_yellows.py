#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'catalog_site.json').read_text(encoding='utf-8-sig'))
txt=(ROOT/'note-icons'/'map.js').read_text(encoding='utf-8').strip(); p='window.NOTE_ICON_MAP='; mp=json.loads(txt[len(p):].rstrip(';'))
def key(s): return re.sub(r'\s+',' ',str(s or '').strip().lower())
def loose(s): return re.sub(r'[^a-z0-9]+','',key(s))
loose_map={}
for k,v in mp.items(): loose_map.setdefault(loose(k),[]).append((k,v))
rows=[]
for d,s in zip(DB,SITE):
    checks=s.get('validationChecks') or {}
    fails=[k for k,v in checks.items() if not v]
    if str(s.get('validationStatus') or '').lower()!='yellow' or fails!=['icons']: continue
    notes=d.get('fragranticaSocialCardNotes') or []
    miss=[]
    for n in notes:
        k=key(n)
        if k in mp: continue
        cand=loose_map.get(loose(n),[])
        miss.append({'note':n,'key':k,'normalizedCandidates':[{'key':x,'path':y} for x,y in cand]})
    rows.append({'code':d.get('code'),'brand':d.get('brand'),'inspiredBy':d.get('inspiredBy'),'notes':notes,'missing':miss})
out={'count':len(rows),'rows':rows}
(ROOT/'icon-only-yellow-analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
