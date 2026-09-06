import json
from pathlib import Path

SRC = Path('database_v2_clean.json')
LIVE = Path('database_complete.json')
BACKUP = Path('perfume-database/archive/database_complete_pre_v2.json')

clean = json.loads(SRC.read_text(encoding='utf-8-sig'))
if len(clean) != 2369:
    raise SystemExit(f'ABORT: expected 2369 clean rows, found {len(clean)}')

BACKUP.parent.mkdir(parents=True, exist_ok=True)
if not BACKUP.exists() and LIVE.exists():
    BACKUP.write_text(LIVE.read_text(encoding='utf-8-sig'), encoding='utf-8')

live = []
for row in clean:
    r = dict(row)
    if not str(r.get('code') or '').strip():
        fallback = str(r.get('reference') or r.get('id') or '').strip()
        if not fallback:
            raise SystemExit('ABORT: row without code/reference/id')
        r['code'] = fallback
        r['liveKeyFallback'] = True
    r['brand'] = str(r.get('brand') or '').strip() or 'Unknown Brand'
    r['genderAffinity'] = str(r.get('genderAffinity') or '')
    r['seasons'] = r.get('seasons') or []
    r['occasions'] = []
    r['mainAccords'] = r.get('mainAccords') or []
    r['notes'] = r.get('notes') or {'top': [], 'heart': [], 'base': []}
    live.append(r)

LIVE.write_text(json.dumps(live, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

codes = [str(r.get('code') or '').strip() for r in live]
print('live rows', len(live))
print('unique live keys', len(set(codes)))
print('fallback keys', sum(bool(r.get('liveKeyFallback')) for r in live))
if len(live) != 2369 or len(set(codes)) != 2369:
    raise SystemExit('ABORT: live row/key gate failed')
