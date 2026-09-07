#!/usr/bin/env python3
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'tools/promote_shobi_first_residuals_v2.py'
ADD_SPEC = ROOT / 'tools/shobi_first_additional_v2.py'
BATCH_SPECS = [
    (ROOT / f'tools/shobi_first_batch_large_{i:02d}_v2.py', f'APPROVED_BATCH_LARGE_{i:02d}')
    for i in range(1, 16)
]
DBS = [ROOT / 'database_v2_clean.json', ROOT / 'database_complete.json']
URLS = ROOT / 'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
OUT = ROOT / 'fragrantica-v2-shobi-first-promotion.md'
FORCE_CORRECTIONS = {'1186-JOO'}

def load_literal(path, name):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise RuntimeError(f'{name} not found in {path}')

def load_url_ids():
    ids = set()
    for line in URLS.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.search(r'-(\d+)\.html(?:[?#].*)?$', line)
        if m:
            ids.add(int(m.group(1)))
    return ids

APPROVED = load_literal(SPEC, 'APPROVED')
NO_FORCE = load_literal(SPEC, 'NO_FORCE')
APPROVED.update(load_literal(ADD_SPEC, 'APPROVED_ADDITIONAL'))
for batch_path, var_name in BATCH_SPECS:
    APPROVED.update(load_literal(batch_path, var_name))
url_ids = load_url_ids()

probe_ids = [200, 204, 456, 520, 719, 905, 925, 970, 993, 1014, 1061, 1365, 1499, 2068, 12201]
probe = {pid: (pid in url_ids) for pid in probe_ids}
present = {code: spec for code, spec in APPROVED.items() if int(spec[0]) in url_ids}
missing = {code: spec for code, spec in APPROVED.items() if int(spec[0]) not in url_ids}

changed = {db.name: 0 for db in DBS}
already = 0
conflicts = 0
promoted = 0

for db_path in DBS:
    data = json.loads(db_path.read_text(encoding='utf-8'))
    rows = data if isinstance(data, list) else data.get('products', data.get('items', []))
    if not isinstance(rows, list):
        raise RuntimeError(f'Unsupported DB structure in {db_path}')
    n = 0
    for row in rows:
        code = str(row.get('code') or row.get('shobi_code') or row.get('id') or '').strip()
        if code not in APPROVED:
            continue
        target_id, brand, name, reason = APPROVED[code]
        current = row.get('fragrantica_id')
        status = str(row.get('fragrantica_status') or row.get('status') or '').upper()
        if current is not None and str(current).strip() == str(target_id):
            already += 1
            continue
        if 'VERIFIED' in status and current not in (None, '', 0, '0') and code not in FORCE_CORRECTIONS:
            conflicts += 1
            continue
        row['fragrantica_id'] = int(target_id)
        row['fragrantica_url'] = f'https://www.fragrantica.com/perfume/{brand.replace(" ", "-")}/{name.replace(" ", "-")}-{target_id}.html'
        row['fragrantica_status'] = 'VERIFIED_SHOBI_FIRST'
        row['fragrantica_match_method'] = 'shobi_first_exact_identity_web_or_local'
        row['fragrantica_match_reason'] = reason
        n += 1
        promoted += 1
    if n:
        db_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    changed[db_path.name] = n

lines = [
    '# Shobi-first residual promotion', '',
    f'- Local corpus numeric IDs parsed: **{len(url_ids)}**',
    f'- Reviewed exact identities with Fragrantica target: **{len(APPROVED)}**',
    f'- Target IDs present in local corpus: **{len(present)}**',
    f'- Target IDs missing from local corpus: **{len(missing)}**',
    f'- Promotion policy: **all reviewed exact identities are eligible; local corpus presence is informational only**',
    f'- Promoted this run: **{promoted}**',
    f'- Already verified with same ID: **{already}**',
    f'- Conflicting pre-existing VERIFIED mappings left untouched: **{conflicts}**',
    f'- Identified but deliberately not forced: **{len(NO_FORCE)}**',
    f'- Probe IDs: **{probe}**',
]
for k, v in changed.items():
    lines.append(f'- {k}: **{v}** rows changed')
lines += ['', '## Exact targets', '']
for code, (fid, brand, name, reason) in APPROVED.items():
    state = 'IN_CORPUS' if int(fid) in url_ids else 'MISSING_FROM_CORPUS'
    lines.append(f'- `{code}` -> {brand} / {name} — ID {fid} — {state} — {reason}')
lines += ['', '## No-force identities', '']
for code, reason in NO_FORCE.items():
    lines.append(f'- `{code}` — {reason}')
OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'parsed_ids={len(url_ids)} reviewed={len(APPROVED)} in_corpus={len(present)} missing={len(missing)} promoted={promoted} already={already} conflicts={conflicts} no_force={len(NO_FORCE)}')
