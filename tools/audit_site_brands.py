import json
from collections import Counter
from pathlib import Path

DB = Path('database_complete.json')
OUT = Path('site-brand-audit.md')

raw = json.loads(DB.read_text(encoding='utf-8'))

# Support both flat and grouped database shapes.
records = []
if isinstance(raw, list) and raw and isinstance(raw[0], dict) and isinstance(raw[0].get('perfumes'), list):
    for group in raw:
        brand = ((group.get('brandInfo') or {}).get('name') or '').strip()
        for p in group.get('perfumes') or []:
            q = dict(p)
            q['_effective_brand'] = (q.get('brand') or brand or '').strip()
            records.append(q)
elif isinstance(raw, list):
    for p in raw:
        if not isinstance(p, dict):
            continue
        q = dict(p)
        q['_effective_brand'] = (q.get('brand') or '').strip()
        records.append(q)


def status_of(p):
    return str(p.get('fragrantica_status') or p.get('fragranticaStatus') or '').upper()

def official(p):
    return not status_of(p).startswith('RESOLVED_NO_FORCE')

site = [p for p in records if official(p) and p.get('code') and p.get('inspiredBy')]
placeholders = {'', 'unknown brand', 'unknown', 'n/a', 'na', 'none', 'null', '-'}
missing = [p for p in site if p['_effective_brand'].strip().lower() in placeholders]
counts = Counter(p['_effective_brand'].strip() for p in site if p['_effective_brand'].strip())

lines = [
    '# Site brand audit',
    '',
    f'- Official site records: **{len(site)}**',
    f'- Records with usable brand: **{len(site)-len(missing)}**',
    f'- Missing/placeholder brand: **{len(missing)}**',
    f'- Distinct non-empty brands: **{len(counts)}**',
    '',
    '## Missing/placeholder brand records',
    ''
]
if missing:
    lines += ['| Code | Inspired by | Status |', '|---|---|---|']
    for p in sorted(missing, key=lambda x: str(x.get('code'))):
        name = str(p.get('inspiredBy') or '').replace('|', '\\|')
        lines.append(f"| {p.get('code','')} | {name} | {status_of(p)} |")
else:
    lines.append('None.')

lines += ['', '## Brand counts', '', '| Brand | Perfumes |', '|---|---:|']
for brand, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower())):
    lines.append(f"| {brand.replace('|', '\\|')} | {n} |")

OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Official={len(site)} missing_brand={len(missing)} distinct_brands={len(counts)}')
