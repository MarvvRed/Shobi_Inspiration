#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'database_complete.json'
OUT = ROOT / 'social-card-main-notes-audit.json'

def fid_of(p):
    for k in ('fragranticaId','fragrantica_id','fid'):
        v=p.get(k)
        if v not in (None,''):
            try: return int(v)
            except (TypeError,ValueError): return str(v)
    return None

def code_of(p):
    return p.get('code') or p.get('shobiCode') or p.get('shobi_code') or p.get('id')

def official(p):
    return p.get('status') != 'NO_FORCE'

rows=json.loads(DB.read_text(encoding='utf-8'))
if isinstance(rows,dict):
    rows=rows.get('perfumes') or rows.get('records') or rows.get('data') or []

fid_rows=defaultdict(list)
issues=[]
status_counts=defaultdict(int)
official_rows=[]
for p in rows:
    if not official(p): continue
    official_rows.append(p)
    fid=fid_of(p); code=code_of(p); notes=p.get('fragranticaSocialCardNotes') or []
    status=p.get('socialCardMainNotesStatus') or p.get('fragranticaSocialCardNotesStatus') or ''
    status_counts[status]+=1
    if fid is not None: fid_rows[str(fid)].append({'code':code,'name':p.get('name'),'brand':p.get('brand')})
    if not isinstance(notes,list):
        issues.append({'type':'NOT_ARRAY','code':code,'fid':fid})
        continue
    if any(not isinstance(n,str) or not n.strip() for n in notes):
        issues.append({'type':'INVALID_NOTE_VALUE','code':code,'fid':fid,'notes':notes})
    seen=set(); dup=[]
    for n in notes:
        key=n.strip().casefold() if isinstance(n,str) else repr(n)
        if key in seen: dup.append(n)
        seen.add(key)
    if dup:
        issues.append({'type':'DUPLICATE_NOTE_IN_CARD','code':code,'fid':fid,'duplicates':dup,'notes':notes})
    if status=='SOCIAL_CARD_UNAVAILABLE' and notes:
        issues.append({'type':'UNAVAILABLE_HAS_NOTES','code':code,'fid':fid,'notes':notes})
    if status not in ('SOCIAL_CARD_UNAVAILABLE','UNRESOLVED_NO_INFERENCE') and not notes:
        issues.append({'type':'VALIDATED_WITHOUT_NOTES','code':code,'fid':fid,'status':status})

shared=[{'fid':fid,'records':rs} for fid,rs in fid_rows.items() if len(rs)>1]
report={
  'rule':'Audit only. Do not infer, reorder, deduplicate, or replace Social Card notes automatically.',
  'totalRecords':len(rows),
  'officialRecords':len(official_rows),
  'statusCounts':dict(sorted(status_counts.items())),
  'issueCount':len(issues),
  'issues':issues,
  'sharedFragranticaIdCount':len(shared),
  'sharedFragranticaIds':shared,
}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'officialRecords':len(official_rows),'issueCount':len(issues),'sharedFragranticaIdCount':len(shared)}))
