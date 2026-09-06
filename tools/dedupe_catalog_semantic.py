import json
import re
import unicodedata
from pathlib import Path

DB = Path('database_complete.json')
REPORT = Path('catalog-semantic-dedupe-report.md')

# Verified same-real-perfume duplicates under different Shobi codes / missing codes.
# Keep the canonical/current code shown on Shobi where available.
KEEP_CODE_FOR_IDENTITY = {
    ('calvin klein', 'ck one summer'): '1052-CAL',
    ('lartisan parfumeur', 'premier figuier'): '1195-LART',
    ('louis vuitton', 'attrape reves'): '1767-LTN',
    ('missguided', 'babe power'): '826-MIS',
    ('prada', 'infusion d oeillet'): '1239-PRA',
    ('serge lutens', 'jeux de peau'): '1796-SERG',
    ('swiss arabian', 'al amaken'): '1950-SWISA',
    ('swiss arabian', 'kashkha'): '2172-SWISA',
}

# Verified wrong identity in our enriched catalog: Shobi list says 1220-MOS = TOY,
# while 2352-MOS = TOY BOY.
NAME_FIXES = {
    '1220-MOS': 'Toy',
}


def norm(value):
    s = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return ' '.join(s.split())


def iter_rows(data):
    for group in data:
        brand = norm((group.get('brandInfo') or {}).get('name'))
        for p in group.get('perfumes', []):
            yield group, brand, p


def merge_missing(dst, src):
    for key, value in src.items():
        if key in {'code', 'shobiUrl', 'prestashopProductId'}:
            continue
        if dst.get(key) in (None, '', [], {}) and value not in (None, '', [], {}):
            dst[key] = value


data = json.loads(DB.read_text(encoding='utf-8'))
removed = []
corrected = []
not_found = []

# Correct known misidentification first.
for _, _, p in iter_rows(data):
    code = str(p.get('code') or '').strip().upper()
    if code not in NAME_FIXES:
        continue
    wanted = NAME_FIXES[code]
    if norm(p.get('inspiredBy')) != norm(wanted):
        old = str(p.get('inspiredBy') or '')
        p['inspiredBy'] = wanted
        p['identityStatus'] = 'CONFIRMED'
        p['identityVerifiedAt'] = '2026-09-06'
        p['identityEvidence'] = 'Verified against Shobi master list: 1220-MOS = TOY; 2352-MOS = TOY BOY.'
        corrected.append((code, old, wanted))

# Collapse only explicitly verified semantic duplicate groups.
for (wanted_brand, wanted_name), keep_code in KEEP_CODE_FOR_IDENTITY.items():
    matches = []
    for group, brand, p in iter_rows(data):
        if brand == wanted_brand and norm(p.get('inspiredBy')) == wanted_name:
            matches.append((group, p))

    if len(matches) < 2:
        not_found.append((wanted_brand, wanted_name, keep_code, len(matches)))
        continue

    keepers = [(g, p) for g, p in matches if str(p.get('code') or '').strip().upper() == keep_code]
    if len(keepers) != 1:
        raise RuntimeError(f'{wanted_brand}/{wanted_name}: expected one keeper {keep_code}, found {len(keepers)}')

    _, keep = keepers[0]
    for group, p in list(matches):
        if p is keep:
            continue
        old_code = str(p.get('code') or '').strip().upper()
        merge_missing(keep, p)
        group['perfumes'].remove(p)
        removed.append((wanted_brand, wanted_name, keep_code, old_code or '(empty)'))

# Remove brand groups left empty by deduplication.
data = [g for g in data if g.get('perfumes')]
DB.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

rows = sum(len(g.get('perfumes', [])) for g in data)
lines = [
    '# Semantic catalog dedupe', '',
    f'- Final catalog rows: **{rows}**',
    f'- Semantic duplicate rows removed this run: **{len(removed)}**',
    f'- Identity/name corrections this run: **{len(corrected)}**',
    f'- Verified target groups not found as duplicate pairs: **{len(not_found)}**',
    '', '## Removed'
]
for brand, name, keep, drop in removed:
    lines.append(f'- {brand} — {name}: kept `{keep}`, removed `{drop}`')
lines += ['', '## Corrected identities']
for code, old, new in corrected:
    lines.append(f'- `{code}`: `{old}` → `{new}`')
lines += ['', '## Target groups not present as duplicate pairs']
if not_found:
    for brand, name, keep, count in not_found:
        lines.append(f'- {brand} — {name}: keeper `{keep}`, matching rows found={count}')
else:
    lines.append('- None')
REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'rows={rows} removed={len(removed)} corrected={len(corrected)} not_found={len(not_found)}')
