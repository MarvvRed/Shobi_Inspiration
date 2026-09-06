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
        for v in x: yield from walk(v)
    elif isinstance(x, dict):
        if any(k in x for k in ('Code','code','Shobi Code','shobi_code')):
            yield x
        else:
            for v in x.values(): yield from walk(v)

def get_code(r):
    for k in ('Code','code','Shobi Code','shobi_code'):
        if r.get(k): return str(r[k]).strip()
    return ''

data = json.loads(DB.read_text(encoding='utf-8-sig'))
rows = list(walk(data))
found = {c: [r for r in rows if get_code(r) == c] for c in TARGETS}
for c, rs in found.items():
    if len(rs) != 1: raise SystemExit(f'ABORT {c}: expected exactly 1 row, found {len(rs)}')

for c, (brand, perfume) in TARGETS.items():
    r = found[c][0]
    old = r.get('inspiredBy', '')
    r['inspiredBy'] = f'{perfume} {brand}'
    r['Brand'] = brand
    r['Perfume'] = perfume
    print(f'{c}: inspiredBy={old!r} -> {r["inspiredBy"]!r}')

DB.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('fixed canonical fields', len(TARGETS))
