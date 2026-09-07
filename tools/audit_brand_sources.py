import json
from collections import Counter
from pathlib import Path

rows=json.loads(Path('database_complete.json').read_text(encoding='utf-8'))
keys=Counter()
for r in rows:
    if isinstance(r,dict): keys.update(r.keys())

out=['# Brand source field audit','','## Field coverage','','| Field | Rows |','|---|---:|']
for k,n in keys.most_common(): out.append(f'| {k} | {n} |')
out += ['','## Sample official records','','```json']
count=0
for r in rows:
    if not isinstance(r,dict): continue
    s=str(r.get('fragrantica_status') or r.get('fragranticaStatus') or '').upper()
    if s.startswith('RESOLVED_NO_FORCE'): continue
    out.append(json.dumps(r,ensure_ascii=False))
    count+=1
    if count>=8: break
out += ['```','']
Path('brand-source-audit.md').write_text('\n'.join(out),encoding='utf-8')
print('rows',len(rows),'keys',len(keys))
