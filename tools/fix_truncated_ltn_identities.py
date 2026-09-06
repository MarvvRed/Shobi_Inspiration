import json
from pathlib import Path

DB = Path('database_complete.json')
TARGETS = {
    '2783-LTN': ('Louis Vuitton', 'Ink Mark'),
    '2786-LTN': ('Louis Vuitton', 'Rain Tea'),
    '2791-LTN': ('Louis Vuitton', 'Moon Tale'),
}

def walk(x):
    if isinstance(x, list):
        for v in x:
            yield from walk(v)
    elif isinstance(x, dict):
        if any(k in x for k in ('Code','code','Shobi Code','shobi_code')):
            yield x
        else:
            for v in x.values():
                yield from walk(v)

def get_code(r):
    for k in ('Code','code','Shobi Code','shobi_code'):
        if r.get(k): return str(r[k]).strip()
    return ''

def set_first(r, keys, value):
    for k in keys:
        if k in r:
            r[k] = value
            return k
    r[keys[0]] = value
    return keys[0]

data = json.loads(DB.read_text(encoding='utf-8-sig'))
rows = list(walk(data))
found = {c: [r for r in rows if get_code(r) == c] for c in TARGETS}
for c, rs in found.items():
    if len(rs) != 1:
        raise SystemExit(f'ABORT {c}: expected exactly 1 row, found {len(rs)}')

for c, (brand, perfume) in TARGETS.items():
    r = found[c][0]
    old_brand = next((str(r.get(k,'')) for k in ('Brand','brand','Designer','designer') if k in r), '')
    old_name = next((str(r.get(k,'')) for k in ('Perfume','perfume','Name','name','Inspired By','inspired_by') if k in r), '')
    set_first(r, ('Brand','brand','Designer','designer'), brand)
    set_first(r, ('Perfume','perfume','Name','name','Inspired By','inspired_by'), perfume)
    print(f'{c}: {old_brand} / {old_name} -> {brand} / {perfume}')

DB.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('fixed', len(TARGETS))
