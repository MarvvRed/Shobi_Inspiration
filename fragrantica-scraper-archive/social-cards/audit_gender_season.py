#!/usr/bin/env python3
import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOCIAL = ROOT / 'fragrantica-scraper-archive' / 'social-cards'
SRC = SOCIAL / 'gender-season.csv'
MANIFEST = SOCIAL / 'manifest.csv'
SUMMARY = SOCIAL / 'gender-season-audit.md'
UNRESOLVED = SOCIAL / 'gender-unresolved.csv'
TIES = SOCIAL / 'season-ties.csv'

with SRC.open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
with MANIFEST.open(encoding='utf-8-sig', newline='') as f:
    manifest = list(csv.DictReader(f))

base_fields = list(rows[0].keys()) if rows else []
season_counts = Counter(r.get('main_season','') for r in rows)
gender_counts = Counter(r.get('gender','') or 'unresolved' for r in rows)
confidence_counts = Counter(r.get('season_confidence','') for r in rows)

unresolved = [dict(r) for r in rows if not (r.get('gender') or '').strip()]
ties = [dict(r) for r in rows if r.get('main_season') == 'TIE']

# For each tie, record the actual longest bar and raw margin without mutating source rows.
for r in ties:
    vals = {s: float(r.get(s) or 0) for s in ('winter','spring','summer','fall')}
    ordered = sorted(vals.items(), key=lambda kv: kv[1], reverse=True)
    r['actual_longest'] = ordered[0][0]
    r['actual_longest_value'] = f'{ordered[0][1]:.4f}'
    r['runner_up'] = ordered[1][0]
    r['runner_up_value'] = f'{ordered[1][1]:.4f}'
    r['actual_margin'] = f'{ordered[0][1]-ordered[1][1]:.4f}'

# Duplicate diagnostics.
by_pid = defaultdict(list)
by_fid = defaultdict(list)
by_path = defaultdict(list)
for r in rows:
    by_pid[r.get('prestashop_product_id','')].append(r)
    by_fid[r.get('fragrantica_id','')].append(r)
    by_path[r.get('local_path','')].append(r)

dup_pid = {k:v for k,v in by_pid.items() if k and len(v)>1}
dup_fid = {k:v for k,v in by_fid.items() if k and len(v)>1}
dup_path = {k:v for k,v in by_path.items() if k and len(v)>1}

manifest_cards = [r for r in manifest if r.get('card_status') in {'EXISTS','DOWNLOADED'} and r.get('local_path')]
manifest_unique_paths = len({r.get('local_path') for r in manifest_cards})

with UNRESOLVED.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=base_fields)
    w.writeheader(); w.writerows(unresolved)

if ties:
    tie_fields = base_fields + ['actual_longest','actual_longest_value','runner_up','runner_up_value','actual_margin']
    with TIES.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=tie_fields)
        w.writeheader(); w.writerows(ties)

lines = [
    '# Gender + Season extraction audit', '',
    f'- extracted_rows: **{len(rows)}**',
    f'- manifest_card_rows: **{len(manifest_cards)}**',
    f'- manifest_unique_card_paths: **{manifest_unique_paths}**',
    f'- gender_resolved: **{len(rows)-len(unresolved)}**',
    f'- gender_unresolved: **{len(unresolved)}**',
    f'- season_ties: **{len(ties)}**',
    f'- duplicate_prestashop_ids: **{len(dup_pid)}**',
    f'- duplicate_fragrantica_ids: **{len(dup_fid)}**',
    f'- duplicate_local_paths: **{len(dup_path)}**', '',
    '## Gender',
]
for k,v in sorted(gender_counts.items()): lines.append(f'- {k}: {v}')
lines += ['', '## Main season']
for k,v in sorted(season_counts.items()): lines.append(f'- {k}: {v}')
lines += ['', '## Season confidence']
for k,v in sorted(confidence_counts.items()): lines.append(f'- {k}: {v}')
lines += ['', '## Duplicate Fragrantica IDs (first 50)']
for k,v in list(sorted(dup_fid.items()))[:50]:
    ids = ', '.join(f"pid={x.get('prestashop_product_id')} code={x.get('shobi_code')}" for x in v)
    lines.append(f'- {k}: {ids}')
lines += ['', '## Duplicate Prestashop IDs (first 50)']
for k,v in list(sorted(dup_pid.items()))[:50]:
    ids = ', '.join(f"fid={x.get('fragrantica_id')} code={x.get('shobi_code')}" for x in v)
    lines.append(f'- {k}: {ids}')
SUMMARY.write_text('\n'.join(lines) + '\n', encoding='utf-8')

print(f'rows={len(rows)} gender_unresolved={len(unresolved)} ties={len(ties)}')
print('gender=', dict(gender_counts))
print('season=', dict(season_counts))
print('confidence=', dict(confidence_counts))
print(f'dup_pid={len(dup_pid)} dup_fid={len(dup_fid)} dup_path={len(dup_path)} manifest_cards={len(manifest_cards)} unique_paths={manifest_unique_paths}')
