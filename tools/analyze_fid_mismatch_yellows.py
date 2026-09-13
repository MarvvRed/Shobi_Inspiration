#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'catalog_site.json').read_text(encoding='utf-8-sig'))
VALID={str(x.get('code') or '').strip().upper():x for x in json.loads((ROOT/'social-card-main-notes-validated.json').read_text(encoding='utf-8'))}
RAW={str(x.get('code') or '').strip().upper():x for x in json.loads((ROOT/'social-card-main-notes.json').read_text(encoding='utf-8'))}

def code(v):return str(v or '').strip().upper()
def uid(u):
 m=re.search(r'-(\d+)\.html(?:$|[?#])',str(u or ''),re.I);return m.group(1) if m else ''
rows=[]
for db,s in zip(DB,SITE):
 if str(s.get('validationStatus') or '').lower()!='yellow' or (s.get('validationChecks') or {}).get('socialCard',False):continue
 c=code(db.get('code'));v=VALID.get(c) or {};raw=RAW.get(c) or {};fid=str(db.get('fragranticaId') or '').strip();vf=str(v.get('fragranticaId') or '').strip();rf=str(raw.get('fragranticaId') or '').strip()
 if not vf or vf==fid:continue
 rows.append({'code':c,'brand':db.get('brand'),'inspiredBy':db.get('inspiredBy'),'currentFid':fid,'currentUrl':db.get('fragranticaUrl'),'currentUrlFid':uid(db.get('fragranticaUrl')),'identityStatus':db.get('identityStatus'),'verificationSource':db.get('fragranticaVerificationSource'),'validatedFid':vf,'validated':v.get('validated'),'validatedCard':v.get('card'),'validatedNotes':v.get('mainNotes'),'rawFid':rf,'rawCard':raw.get('card'),'currentNotes':db.get('fragranticaSocialCardNotes') or [],'failedChecks':[k for k,x in (s.get('validationChecks') or {}).items() if not x]})
out={'count':len(rows),'rows':rows};(ROOT/'fid-mismatch-yellows.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Remaining validated-card FID mismatches','',f'- Rows: **{len(rows)}**','','| Code | Brand | Name | Current FID | Validated-card FID | Identity |','|---|---|---|---:|---:|---|']
for r in rows:lines.append(f"| {r['code']} | {r['brand']} | {str(r['inspiredBy']).replace('|','/')} | {r['currentFid']} | {r['validatedFid']} | {r['identityStatus']} |")
(ROOT/'fid-mismatch-yellows.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
