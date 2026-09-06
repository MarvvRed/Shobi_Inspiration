#!/usr/bin/env python3
from __future__ import annotations
import csv, json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'database_complete.json'
EXTRACT = ROOT / 'fragrantica-scraper-archive' / 'social-cards' / 'gender-season.csv'
REPORT = ROOT / 'fragrantica-scraper-archive' / 'social-cards' / 'catalog-merge-report.md'

GENDER_MAP = {
    'male': 'masculine',
    'female': 'feminine',
    'unisex': 'unisex',
}
SEASON_MAP = {
    'winter': 'winter',
    'spring': 'spring',
    'summer': 'summer',
    'fall': 'autumn',
    'autumn': 'autumn',
}

def norm_code(value):
    return str(value or '').strip().upper()

with EXTRACT.open(encoding='utf-8-sig', newline='') as f:
    source_rows = list(csv.DictReader(f))

by_code = defaultdict(list)
for row in source_rows:
    code = norm_code(row.get('shobi_code'))
    if code:
        by_code[code].append(row)

resolved = {}
conflicting_codes = {}
for code, rows in by_code.items():
    values = set()
    for r in rows:
        gender = GENDER_MAP.get((r.get('gender') or '').strip().lower(), '')
        season = SEASON_MAP.get((r.get('main_season') or '').strip().lower(), '')
        if gender and season:
            values.add((gender, season))
    if len(values) == 1:
        resolved[code] = next(iter(values))
    elif len(values) > 1:
        conflicting_codes[code] = sorted(values)

with CATALOG.open(encoding='utf-8') as f:
    data = json.load(f)

perfumes = []
if isinstance(data, list):
    for entry in data:
        if isinstance(entry, dict) and isinstance(entry.get('perfumes'), list):
            perfumes.extend(entry['perfumes'])
        elif isinstance(entry, dict):
            perfumes.append(entry)

catalog_codes = defaultdict(list)
for p in perfumes:
    code = norm_code(p.get('code'))
    if code:
        catalog_codes[code].append(p)

updated_rows = 0
updated_codes = set()
unchanged_rows = 0
missing_source_codes = set()
for code, plist in catalog_codes.items():
    values = resolved.get(code)
    if not values:
        missing_source_codes.add(code)
        continue
    gender, season = values
    for p in plist:
        before_gender = str(p.get('genderAffinity') or '').strip().lower()
        before_seasons = [str(x).strip().lower() for x in (p.get('seasons') or []) if str(x).strip()]
        p['genderAffinity'] = gender
        p['seasons'] = [season]
        if before_gender == gender and before_seasons == [season]:
            unchanged_rows += 1
        else:
            updated_rows += 1
    updated_codes.add(code)

with CATALOG.open('w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write('\n')

source_codes = set(resolved)
unmatched_source_codes = sorted(source_codes - set(catalog_codes))
matched_catalog_rows = sum(len(catalog_codes[c]) for c in updated_codes)

lines = [
    '# Gender + Season catalog merge report', '',
    f'- extraction_rows: **{len(source_rows)}**',
    f'- extraction_unique_codes: **{len(by_code)}**',
    f'- extraction_resolved_codes: **{len(resolved)}**',
    f'- extraction_conflicting_codes: **{len(conflicting_codes)}**',
    f'- catalog_perfume_rows: **{len(perfumes)}**',
    f'- catalog_unique_codes: **{len(catalog_codes)}**',
    f'- matched_catalog_codes: **{len(updated_codes)}**',
    f'- matched_catalog_rows: **{matched_catalog_rows}**',
    f'- catalog_rows_changed: **{updated_rows}**',
    f'- catalog_rows_already_equal: **{unchanged_rows}**',
    f'- catalog_codes_without_social_card_merge: **{len(missing_source_codes)}**',
    f'- extraction_codes_not_present_in_catalog: **{len(unmatched_source_codes)}**', '',
    '## Rules',
    '- Gender: male → masculine, female → feminine, unisex → unisex.',
    '- Season: the single dominant Fragrantica bar is stored as one season; fall is normalized to autumn for the existing site UI.',
    '- Existing catalog values are preserved for catalog codes without a resolved social-card match.',
]
if conflicting_codes:
    lines += ['', '## Conflicting extraction codes']
    for code, vals in sorted(conflicting_codes.items()):
        lines.append(f'- {code}: {vals}')
if missing_source_codes:
    lines += ['', '## Catalog codes without social-card merge (first 100)']
    for code in sorted(missing_source_codes)[:100]:
        lines.append(f'- {code}')
if unmatched_source_codes:
    lines += ['', '## Extraction codes not in catalog (first 100)']
    for code in unmatched_source_codes[:100]:
        lines.append(f'- {code}')
REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')

print(f'extraction_rows={len(source_rows)} unique_source_codes={len(by_code)} resolved_codes={len(resolved)} conflicts={len(conflicting_codes)}')
print(f'catalog_rows={len(perfumes)} catalog_unique_codes={len(catalog_codes)} matched_codes={len(updated_codes)} matched_rows={matched_catalog_rows}')
print(f'changed_rows={updated_rows} already_equal={unchanged_rows} catalog_unmatched_codes={len(missing_source_codes)} source_not_in_catalog={len(unmatched_source_codes)}')
