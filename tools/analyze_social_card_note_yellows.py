#!/usr/bin/env python3
"""Diagnose yellow rows failing Social Card/Main Notes without mutating catalog."""
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database/catalog/database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'database/catalog/catalog_site.json').read_text(encoding='utf-8-sig'))
VAL={str(x.get('code') or '').strip().upper():x for x in json.loads((ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json').read_text(encoding='utf-8'))}
RAW={str(x.get('code') or '').strip().upper():x for x in json.loads((ROOT/'database/fragrantica/social-cards/records/social-card-main-notes.json').read_text(encoding='utf-8'))}

def classify(db,s):
    c=str(db.get('code') or '').strip().upper(); fid=str(db.get('fragranticaId') or '').strip(); notes=db.get('fragranticaSocialCardNotes') or []
    v=VAL.get(c); r=RAW.get(c)
    if v:
        vf=str(v.get('fragranticaId') or '').strip(); card=str(v.get('card') or ''); exists=bool(card and (ROOT/card).is_file())
        suffix=bool(card.endswith(f'_{db.get("code")}_{fid}.jpeg')) if fid else False
        same_notes=(v.get('mainNotes') or [])==notes
        if v.get('validated') is True and vf==fid and exists and same_notes and not suffix:return 'validated_exact_except_filename_suffix'
        if v.get('validated') is True and vf==fid and exists and not same_notes:return 'validated_exact_id_notes_differ'
        if v.get('validated') is True and vf!=fid:return 'validated_fid_mismatch'
        if v.get('validated') is not True:return 'validated_record_unresolved'
        if not exists:return 'validated_card_file_missing'
    if r:
        rf=str(r.get('fragranticaId') or '').strip(); card=str(r.get('card') or ''); exists=bool(card and (ROOT/card).is_file())
        suffix=bool(card.endswith(f'_{db.get("code")}_{fid}.jpeg')) if fid else False
        if rf==fid and exists and suffix:return 'raw_exact_id_file_suffix'
        if rf==fid and exists:return 'raw_exact_id_file_other_name'
        if rf!=fid:return 'raw_fid_mismatch'
        if not exists:return 'raw_card_file_missing'
    return 'no_social_card_record'

rows=[]; kinds=Counter()
for db,s in zip(DB,SITE):
    if str(s.get('validationStatus') or '').lower()!='yellow':continue
    checks=s.get('validationChecks') or {}
    if checks.get('socialCard',True):continue
    k=classify(db,s); kinds[k]+=1
    failed=[x for x,v in checks.items() if not v]
    rows.append({'code':db.get('code'),'brand':db.get('brand'),'inspiredBy':db.get('inspiredBy'),'fid':db.get('fragranticaId'),'failedChecks':failed,'kind':k,'notes':db.get('fragranticaSocialCardNotes') or [],'validated':VAL.get(str(db.get('code') or '').strip().upper()),'raw':RAW.get(str(db.get('code') or '').strip().upper())})
out={'count':len(rows),'kinds':dict(kinds),'rows':rows}
(ROOT/'database/fragrantica/social-cards/records/social-card-note-yellow-analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Social Card / Main Notes yellow analysis','',f'- Rows: **{len(rows)}**']+[f'- `{k}`: **{v}**' for k,v in kinds.most_common()]+['','## Rows','']
for r in rows:lines.append(f"- `{r['code']}` — {r['kind']} — failed={','.join(r['failedChecks'])} — notes={len(r['notes'])}")
(ROOT/'database/audits/social-card-note-yellow-analysis.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('social_card_yellows',len(rows),dict(kinds))
