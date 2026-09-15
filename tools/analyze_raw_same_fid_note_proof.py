#!/usr/bin/env python3
import json,re,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database/catalog/database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'database/catalog/catalog_site.json').read_text(encoding='utf-8-sig'))
RAW={str(x.get('code') or '').strip().upper():x for x in json.loads((ROOT/'database/fragrantica/social-cards/records/social-card-main-notes.json').read_text(encoding='utf-8'))}

def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 s=re.sub(r'[^a-z0-9]+',' ',s)
 return ' '.join(s.split())

def tokens(s): return [x for x in norm(s).split() if len(x)>1]

def slot_proves(note,raw):
 n=norm(note); r=norm(raw)
 if not n or not r:return False
 if n==r:return True
 nt=tokens(note); rt=tokens(raw)
 # Conservative OCR proof: every significant expected token must occur as a whole token in the same slot.
 return bool(nt) and all(t in rt for t in nt)

rows=[]
for db,site in zip(DB,SITE):
 if str(site.get('validationStatus') or '').lower()!='yellow': continue
 checks=site.get('validationChecks') or {}
 if checks.get('socialCard',False): continue
 c=str(db.get('code') or '').strip().upper(); fid=str(db.get('fragranticaId') or '').strip(); notes=list(db.get('fragranticaSocialCardNotes') or [])
 raw=RAW.get(c) or {}; card=str(raw.get('card') or '')
 if not fid or str(raw.get('fragranticaId') or '')!=fid or not card or not (ROOT/card).is_file(): continue
 slots=sorted(raw.get('slots') or [],key=lambda x:int(x.get('slot') or 999))
 raw_names=[str(x.get('name') or '') for x in slots]
 complete=bool(notes) and len(notes)==len(raw_names) and all(slot_proves(n,r) for n,r in zip(notes,raw_names))
 rows.append({'code':c,'fid':fid,'card':card,'notes':notes,'rawNames':raw_names,'completeOrderedProof':complete})
out={'rawSameFid':len(rows),'completeOrderedProof':sum(r['completeOrderedProof'] for r in rows),'rows':rows}
(ROOT/'database/audits/raw-same-fid-note-proof.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# RAW same-FID note proof','',f"- RAW same-FID rows: **{out['rawSameFid']}**",f"- Complete ordered note proof: **{out['completeOrderedProof']}**",'','## Proven rows','']
for r in rows:
 if r['completeOrderedProof']: lines.append(f"- `{r['code']}` — FID {r['fid']} — `{r['card']}`")
(ROOT/'database/audits/raw-same-fid-note-proof.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(out['rawSameFid'],out['completeOrderedProof'])
