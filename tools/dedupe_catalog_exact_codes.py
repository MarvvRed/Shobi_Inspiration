import json
from pathlib import Path
from collections import defaultdict

DB = Path('database_complete.json')
REPORT = Path('catalog-dedupe-report.md')

# Exact same perfume identity: collapse to the richest row.
SAFE_CODES = {'1068-CHA', '1270-VAN', '390-ACQ'}

# Verified cases where the same Shobi code was attached to two differently named rows.
# The value identifies the record that must survive.
KEEP_NAME_FOR_CODE = {
    '1868-VER': 'versace pour homme',
    '677-GUC': 'g by g',
    '777-LAL': 'noir premier sculpteur d epices',
    '937-VAL': 'valentino donna born in roma',
}

# These two rows were not duplicate perfumes: they had the same malformed placeholder code.
# Replace it with the official Shobi product references verified on leparfum.com.gr.
AL_HARAMAIN_FIXES = {
    'amber oud gold edition': {
        'code': 'ALH078',
        'name': 'Amber Oud Gold Edition',
        'shobiUrl': 'https://leparfum.com.gr/en/al-haramain-oriental-perfumes/al-haramain-amber-oud-gold-edition-60ml',
    },
    'dhahb': {
        'code': 'ALH004',
        'name': 'Dhahab',
        'shobiUrl': 'https://leparfum.com.gr/en/al-haramain-oriental-perfumes/dhahab-al-haramain-perfumes-oil-15ml',
    },
}


def perfumes(data):
    for brand in data:
        for p in brand.get('perfumes', []):
            yield brand, p


def richness(p):
    score = 0
    for _, value in p.items():
        if value not in (None, '', [], {}):
            score += 1
            if isinstance(value, list):
                score += len(value)
            elif isinstance(value, dict):
                score += len(value)
    return score


def norm_name(value):
    return ' '.join(str(value or '').lower().replace('-', ' ').replace("'", '').split())


def merge_missing(dst, src):
    for k, v in src.items():
        if dst.get(k) in (None, '', [], {}) and v not in (None, '', [], {}):
            dst[k] = v


data = json.loads(DB.read_text(encoding='utf-8'))
by_code = defaultdict(list)
for brand, p in perfumes(data):
    code = str(p.get('code') or '').strip()
    if code:
        by_code[code].append((brand, p))

removed = []
corrected = []

# Collapse verified identical-name duplicate cards.
for code in SAFE_CODES:
    rows = by_code.get(code, [])
    if len(rows) < 2:
        continue
    names = {norm_name(p.get('inspiredBy')) for _, p in rows}
    brands = {str(b.get('brandInfo', {}).get('name') or '').lower().strip() for b, _ in rows}
    if len(names) != 1 or len(brands) != 1:
        continue
    _, keep = max(rows, key=lambda bp: richness(bp[1]))
    for brand, p in rows:
        if p is keep:
            continue
        merge_missing(keep, p)
        brand['perfumes'].remove(p)
        removed.append((code, str(keep.get('inspiredBy') or ''), str(p.get('inspiredBy') or '')))

# Resolve verified same-code/different-name collisions. Do not merge fields from the wrong perfume.
for code, wanted in KEEP_NAME_FOR_CODE.items():
    rows = [(b, p) for b, p in perfumes(data) if str(p.get('code') or '').strip() == code]
    if len(rows) < 2:
        continue
    candidates = [(b, p) for b, p in rows if norm_name(p.get('inspiredBy')) == wanted]
    if len(candidates) != 1:
        raise RuntimeError(f'{code}: expected exactly one verified keeper, found {len(candidates)}')
    _, keep = candidates[0]
    for brand, p in rows:
        if p is keep:
            continue
        brand['perfumes'].remove(p)
        removed.append((code, str(keep.get('inspiredBy') or ''), str(p.get('inspiredBy') or '')))

# Fix the malformed Al Haramain placeholder code using official Shobi references.
for brand, p in list(perfumes(data)):
    if str(p.get('code') or '').strip() != '-AL HAR':
        continue
    key = norm_name(p.get('inspiredBy'))
    fix = AL_HARAMAIN_FIXES.get(key)
    if not fix:
        raise RuntimeError(f'-AL HAR: unexpected unresolved perfume {p.get("inspiredBy")!r}')
    old_name = str(p.get('inspiredBy') or '')
    p['code'] = fix['code']
    p['inspiredBy'] = fix['name']
    p['shobiUrl'] = fix['shobiUrl']
    p['identityStatus'] = 'CONFIRMED'
    p['identityVerifiedAt'] = '2026-09-06'
    p['identityEvidence'] = f'Official Shobi product reference verified: {fix["code"]}.'
    sources = list(p.get('identitySources') or [])
    if fix['shobiUrl'] not in sources:
        sources.insert(0, fix['shobiUrl'])
    p['identitySources'] = sources
    corrected.append((old_name, fix['name'], fix['code']))

DB.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

remaining = defaultdict(int)
for _, p in perfumes(data):
    c = str(p.get('code') or '').strip()
    if c:
        remaining[c] += 1
remaining_dupes = {c: n for c, n in remaining.items() if n > 1}

lines = [
    '# Safe duplicate cleanup', '',
    f'- Removed duplicate rows this run: **{len(removed)}**',
    f'- Corrected malformed codes this run: **{len(corrected)}**',
    f'- Remaining repeated-code groups requiring review: **{len(remaining_dupes)}**',
    '', '## Removed this run'
]
for code, kept, dropped in sorted(removed):
    lines.append(f'- `{code}` — kept `{kept}`; removed duplicate `{dropped}`')
lines += ['', '## Corrected codes']
for old_name, new_name, code in corrected:
    lines.append(f'- `{old_name}` → `{new_name}` — official Shobi reference `{code}`')
lines += ['', '## Still requiring review']
if remaining_dupes:
    for code, n in sorted(remaining_dupes.items()):
        lines.append(f'- `{code}` — {n} rows')
else:
    lines.append('- None')
REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'removed={len(removed)} corrected={len(corrected)} remaining_duplicate_groups={len(remaining_dupes)}')
