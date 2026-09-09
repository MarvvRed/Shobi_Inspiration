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
    return p.get('id') or p.get('code') or p.get('shobiCode') or p.get('shobi_code')

def fragrantica_status(p):
    return str(p.get('fragranticaStatus') or p.get('fragrantica_status') or '')

def official(p):
    # Keep this definition identical to finalize_social_card_main_notes.py.
    # The canonical DB has 39 RESOLVED_NO_FORCE records that are deliberately
    # excluded from the official 2330-perfume Fragrantica dataset.
    return not fragrantica_status(p).upper().startswith('RESOLVED_NO_FORCE')

def social_card_status(p):
    return str(p.get('fragranticaSocialCardStatus') or p.get('socialCardMainNotesStatus') or p.get('fragranticaSocialCardNotesStatus') or '')

rows=json.loads(DB.read_text(encoding='utf-8'))
if isinstance(rows,dict):
    rows=rows.get('perfumes') or rows.get('records') or rows.get('data') or []
if isinstance(rows,list) and rows and isinstance(rows[0],dict) and isinstance(rows[0].get('perfumes'),list):
    rows=[p for bucket in rows for p in bucket.get('perfumes',[])]

fid_rows=defaultdict(list)
issues=[]
status_counts=defaultdict(int)
official_rows=[]
for p in rows:
    if not official(p): continue
    official_rows.append(p)
    fid=fid_of(p); code=code_of(p); notes=p.get('fragranticaSocialCardNotes') or []
    status=social_card_status(p)
    status_counts[status]+=1
    if fid is not None: fid_rows[str(fid)].append({'code':code,'name':p.get('inspiredBy') or p.get('name'),'brand':p.get('brand')})
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
  'excludedResolvedNoForce':len(rows)-len(official_rows),
  'statusCounts':dict(sorted(status_counts.items())),
  'issueCount':len(issues),
  'issues':issues,
  'sharedFragranticaIdCount':len(shared),
  'sharedFragranticaIds':shared,
}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'officialRecords':len(official_rows),'excludedResolvedNoForce':len(rows)-len(official_rows),'issueCount':len(issues),'sharedFragranticaIdCount':len(shared)}))
