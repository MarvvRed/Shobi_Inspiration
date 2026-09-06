import json
from pathlib import Path
from collections import defaultdict

DB = Path('database_complete.json')
REPORT = Path('catalog-dedupe-report.md')

# Codes whose duplicate rows represent the same perfume/card and are safe to collapse.
# Keep the richer record (notes/accords/etc.) while preserving missing useful fields from the other row.
SAFE_CODES = {'1068-CHA', '1270-VAN', '390-ACQ', '777-LAL'}


def perfumes(data):
    for brand in data:
        for p in brand.get('perfumes', []):
            yield brand, p


def richness(p):
    score = 0
    for key, value in p.items():
        if value not in (None, '', [], {}):
            score += 1
            if isinstance(value, list): score += len(value)
            elif isinstance(value, dict): score += len(value)
    return score


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
for code in SAFE_CODES:
    rows = by_code.get(code, [])
    if len(rows) < 2:
        continue
    # Same normalized perfume identity is required before deletion.
    names = {str(p.get('inspiredBy') or '').lower().replace('-', ' ').replace("'", '').strip() for _, p in rows}
    brands = {str(b.get('brandInfo', {}).get('name') or '').lower().strip() for b, _ in rows}
    if len(names) != 1 or len(brands) != 1:
        continue
    keep_brand, keep = max(rows, key=lambda bp: richness(bp[1]))
    for brand, p in rows:
        if p is keep:
            continue
        merge_missing(keep, p)
        brand['perfumes'].remove(p)
        removed.append((code, str(keep.get('inspiredBy') or ''), str(p.get('inspiredBy') or '')))

DB.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

remaining = defaultdict(int)
for _, p in perfumes(data):
    c = str(p.get('code') or '').strip()
    if c: remaining[c] += 1
remaining_dupes = {c:n for c,n in remaining.items() if n > 1}

lines = ['# Safe duplicate cleanup', '', f'- Removed duplicate rows: **{len(removed)}**', f'- Remaining repeated-code groups requiring review: **{len(remaining_dupes)}**', '', '## Removed']
for code, kept, dropped in sorted(removed):
    lines.append(f'- `{code}` — kept `{kept}`; removed duplicate `{dropped}`')
lines += ['', '## Still requiring review']
for code, n in sorted(remaining_dupes.items()):
    lines.append(f'- `{code}` — {n} rows')
REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'removed={len(removed)} remaining_duplicate_groups={len(remaining_dupes)}')
