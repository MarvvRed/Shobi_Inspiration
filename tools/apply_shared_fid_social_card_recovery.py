#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'database_complete.json'
VALID = ROOT / 'social-card-main-notes-validated.json'
REPORT = ROOT / 'shared-fid-social-card-recovery.json'
OUT = ROOT / 'shared-fid-social-card-recovery-applied.json'

db = json.loads(DB.read_text(encoding='utf-8-sig'))
valid = json.loads(VALID.read_text(encoding='utf-8'))
report = json.loads(REPORT.read_text(encoding='utf-8'))
by_code = {str(x.get('code') or '').strip().upper(): x for x in db}
valid_by_code = {str(x.get('code') or '').strip().upper(): x for x in valid}

applied=[]
for r in report.get('rows', []):
    kind = r.get('kind')
    if kind not in {'recoverable_exact_notes','recoverable_replace_notes'}:
        continue
    code = str(r.get('code') or '').strip().upper()
    fid = str(r.get('fid') or '').strip()
    cands = r.get('candidates') or []
    if len(cands) != 1:
        continue
    cand = cands[0]
    src_code = str(cand.get('code') or '').strip().upper()
    src = valid_by_code.get(src_code)
    row = by_code.get(code)
    if not src or not row:
        continue
    card = str(src.get('card') or '')
    src_fid = str(src.get('fragranticaId') or '')
    notes = list(src.get('mainNotes') or [])
    if src.get('validated') is not True or src_fid != fid or not card or not (ROOT/card).is_file() or not notes:
        continue
    if kind == 'recoverable_exact_notes' and list(row.get('fragranticaSocialCardNotes') or []) != notes:
        continue
    old_notes = list(row.get('fragranticaSocialCardNotes') or [])
    if kind == 'recoverable_replace_notes':
        row['fragranticaSocialCardNotes'] = notes
    # Create target-code validated metadata pointing to the already validated exact-FID card.
    valid_by_code[code] = {
        **src,
        'code': code,
        'fragranticaId': int(fid) if fid.isdigit() else fid,
        'card': card,
        'validated': True,
        'mainNotes': notes,
    }
    applied.append({'code':code,'fid':fid,'kind':kind,'sourceCode':src_code,'card':card,'oldNotes':old_notes,'notes':notes})

# preserve original order, replacing existing targets and appending new target metadata
seen=set(); rebuilt=[]
for item in valid:
    c=str(item.get('code') or '').strip().upper()
    if c in valid_by_code and c not in seen:
        rebuilt.append(valid_by_code[c]); seen.add(c)
for c,item in valid_by_code.items():
    if c not in seen:
        rebuilt.append(item); seen.add(c)

DB.write_text(json.dumps(db, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
VALID.write_text(json.dumps(rebuilt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
OUT.write_text(json.dumps({'changed':len(applied),'rows':applied}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('changed', len(applied))
