#!/usr/bin/env python3
"""Link existing local perfume image files to the exact Fragrantica ID.
Only maps files already committed as perfume-images/<fragranticaId>.avif.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'
MAP=ROOT/'perfume-images'/'map.js'
rows=json.loads(DB.read_text(encoding='utf-8-sig'))
prefix='window.PERFUME_IMAGE_MAP='
text=MAP.read_text(encoding='utf-8').strip()
if not text.startswith(prefix): raise SystemExit('Invalid perfume image map')
mapping=json.loads(text[len(prefix):].rstrip(';'))
changed=[]
for r in rows:
    c=str(r.get('code') or '').strip().upper()
    fid=str(r.get('fragranticaId') or '').strip()
    if not c or not fid: continue
    expected=f'perfume-images/{fid}.avif'
    if not (ROOT/expected).is_file(): continue
    if mapping.get(c)==expected: continue
    mapping[c]=expected
    changed.append({'code':c,'fragranticaId':fid,'path':expected})
MAP.write_text(prefix+json.dumps(mapping,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
(ROOT/'perfume-image-map-fixes.json').write_text(json.dumps({'changed':len(changed),'rows':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('image_map_fixed',len(changed))
