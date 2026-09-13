#!/usr/bin/env python3
"""Find yellow Social Card failures recoverable from another validated record with the exact same Fragrantica ID."""
import json,re
from collections import defaultdict,Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'catalog_site.json').read_text(encoding='utf-8-sig'))
VALIDATED=json.loads((ROOT/'social-card-main-notes-validated.json').read_text(encoding='utf-8'))

def code(v):return str(v or '').strip().upper()
def url_id(url):
    s=str(url or '').strip()
    for pat in (r'-(\d+)\.html(?:$|[?#])',r'/p/(\d+)(?:/?$|[?#])'):
        m=re.search(pat,s,re.I)
        if m:return m.group(1)
    return ''

by_fid=defaultdict(list)
for v in VALIDATED:
    if v.get('validated') is not True:continue
    fid=str(v.get('fragranticaId') or '').strip(); card=str(v.get('card') or '').strip(); notes=v.get('mainNotes') or []
    if not fid or not card or not notes or not (ROOT/card).is_file():continue
    by_fid[fid].append({'code':code(v.get('code')),'card':card,'notes':notes})

rows=[]; kinds=Counter()
for db,s in zip(DB,SITE):
    checks=s.get('validationChecks') or {}
    if str(s.get('validationStatus') or '').lower()!='yellow' or checks.get('socialCard',True):continue
    fid=str(db.get('fragranticaId') or '').strip(); c=code(db.get('code'))
    candidates=by_fid.get(fid,[]) if fid else []
    # Collapse candidates only if all validated records for this FID agree on ordered notes.
    unique_notes={json.dumps(x['notes'],ensure_ascii=False) for x in candidates}
    consensus=(len(unique_notes)==1 and bool(candidates))
    current=db.get('fragranticaSocialCardNotes') or []
    exact_url=bool(fid and url_id(db.get('fragranticaUrl'))==fid)
    identity_ok=bool(checks.get('identity'))
    if not candidates:k='no_validated_same_fid'
    elif not consensus:k='same_fid_conflicting_validated_notes'
    elif not exact_url:k='same_fid_but_url_not_exact'
    elif not identity_ok:k='same_fid_but_identity_not_verified'
    elif current==candidates[0]['notes']:k='recoverable_exact_notes'
    else:k='recoverable_replace_notes'
    kinds[k]+=1
    rows.append({'code':c,'brand':db.get('brand'),'inspiredBy':db.get('inspiredBy'),'fid':fid,'kind':k,'currentNotes':current,'candidates':candidates,'failedChecks':[x for x,v in checks.items() if not v]})

out={'count':len(rows),'kinds':dict(kinds),'rows':rows}
(ROOT/'shared-fid-social-card-recovery.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Shared-FID Social Card recovery','',f'- Social Card failures inspected: **{len(rows)}**']+[f'- `{k}`: **{v}**' for k,v in kinds.most_common()]+['','## Recoverable','']
for r in rows:
    if r['kind'].startswith('recoverable_'):
        src=r['candidates'][0]
        lines.append(f"- `{r['code']}` — {r['brand']} · {r['inspiredBy']} — FID {r['fid']} — {r['kind']} — source `{src['code']}` `{src['card']}`")
(ROOT/'shared-fid-social-card-recovery.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'count':len(rows),'kinds':dict(kinds)},ensure_ascii=False))
