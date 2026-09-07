import json
from collections import Counter
from pathlib import Path

all_rows={}
out=Path('site-official-count.md')
out.write_text('',encoding='utf-8')
for filename in ['database_complete.json','database_v2_clean.json']:
    data=json.loads(Path(filename).read_text(encoding='utf-8'))
    rows=[]
    if isinstance(data,list) and data and isinstance(data[0],dict) and isinstance(data[0].get('perfumes'),list):
        for b in data:
            rows.extend(b.get('perfumes',[]))
    elif isinstance(data,list):
        rows=data
    else:
        raise SystemExit(f'Unexpected shape: {filename}')
    all_rows[filename]=rows
    statuses=Counter(str(r.get('fragrantica_status') or r.get('fragranticaStatus') or '') for r in rows)
    noforce=sum(1 for r in rows if str(r.get('fragrantica_status') or r.get('fragranticaStatus') or '').upper().startswith('RESOLVED_NO_FORCE'))
    verified=sum(1 for r in rows if str(r.get('fragrantica_status') or r.get('fragranticaStatus') or '').upper().startswith('VERIFIED_'))
    ids=[str(r.get('id') or r.get('code') or '') for r in rows]
    dup_ids=len(ids)-len(set(ids))
    with out.open('a',encoding='utf-8') as f:
        f.write(f'## {filename}\n\n')
        f.write(f'- rows: **{len(rows)}**\n')
        f.write(f'- VERIFIED_*: **{verified}**\n')
        f.write(f'- RESOLVED_NO_FORCE: **{noforce}**\n')
        f.write(f'- rows excluding NO_FORCE: **{len(rows)-noforce}**\n')
        f.write(f'- duplicate ids: **{dup_ids}**\n')
        f.write('- statuses:\n')
        for k,v in statuses.most_common():
            f.write(f'  - `{k or "<empty>"}`: {v}\n')
        f.write('\n')

complete={str(r.get('id') or r.get('code') or ''):r for r in all_rows['database_complete.json']}
clean={str(r.get('id') or r.get('code') or ''):r for r in all_rows['database_v2_clean.json']}
with out.open('a',encoding='utf-8') as f:
    f.write('## Status mismatches\n\n')
    for k in sorted(set(complete)&set(clean)):
        a=str(complete[k].get('fragrantica_status') or complete[k].get('fragranticaStatus') or '')
        b=str(clean[k].get('fragrantica_status') or clean[k].get('fragranticaStatus') or '')
        if a!=b:
            f.write(f'- `{k}`: complete=`{a}` clean=`{b}`; name=`{complete[k].get("inspiredBy","")}`\n')
