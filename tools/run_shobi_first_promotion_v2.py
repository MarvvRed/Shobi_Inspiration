#!/usr/bin/env python3
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'tools/promote_shobi_first_residuals_v2.py'
ADD_SPEC = ROOT / 'tools/shobi_first_additional_v2.py'
BATCH_SPECS = [
    (ROOT / 'tools/shobi_first_batch_large_01_v2.py', 'APPROVED_BATCH_LARGE_01'),
    (ROOT / 'tools/shobi_first_batch_large_02_v2.py', 'APPROVED_BATCH_LARGE_02'),
    (ROOT / 'tools/shobi_first_batch_large_03_v2.py', 'APPROVED_BATCH_LARGE_03'),
    (ROOT / 'tools/shobi_first_batch_large_04_v2.py', 'APPROVED_BATCH_LARGE_04'),
    (ROOT / 'tools/shobi_first_batch_large_05_v2.py', 'APPROVED_BATCH_LARGE_05'),
]
DBS = [ROOT / 'database_v2_clean.json', ROOT / 'database_complete.json']
URLS = ROOT / 'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
OUT = ROOT / 'fragrantica-v2-shobi-first-promotion.md'

def load_literal(path, name):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise RuntimeError(f'{name} not found in {path}')

APPROVED = load_literal(SPEC, 'APPROVED')
if ADD_SPEC.exists():
    APPROVED.update(load_literal(ADD_SPEC, 'APPROVED_ADDITIONAL'))
for batch_path, batch_name in BATCH_SPECS:
    if batch_path.exists():
        APPROVED.update(load_literal(batch_path, batch_name))
NO_FORCE = load_literal(SPEC, 'NO_FORCE')

def walk(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from walk(item)
    elif isinstance(obj, dict):
        if isinstance(obj.get('perfumes'), list):
            for perfume in obj['perfumes']:
                if isinstance(perfume, dict):
                    yield perfume
        elif 'code' in obj or 'inspiredBy' in obj:
            yield obj

need = {str(value[0]) for value in APPROVED.values()}
urls = {}
parsed_ids = set()
for raw in URLS.read_text(encoding='utf-8', errors='ignore').splitlines():
    line = raw.strip()
    matches = re.findall(r'-(\d+)\.html(?:\?[^\s]*)?', line, re.I)
    if not matches:
        continue
    for fid in matches:
        fid = str(fid).strip()
        parsed_ids.add(fid)
        if fid in need and fid not in urls:
            url_match = re.search(r'https?://\S*-' + re.escape(fid) + r'\.html(?:\?\S*)?', line, re.I)
            urls[fid] = url_match.group(0) if url_match else line

promoted = set()
already_verified = set()
conflicts = set()
changed = {}

for path in DBS:
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    count = 0
    for perfume in walk(data):
        code = str(perfume.get('code') or '').strip()
        if code not in APPROVED:
            continue
        fid, brand, name, rationale = APPROVED[code]
        fid = str(fid).strip()
        if fid not in urls:
            continue
        current_status = str(perfume.get('fragranticaStatus') or '')
        current_id = str(perfume.get('fragranticaId') or '').strip()
        if current_status.startswith('VERIFIED_') and current_id == fid:
            already_verified.add(code)
            continue
        if current_status.startswith('VERIFIED_') and current_id and current_id != fid:
            conflicts.add(code)
            continue
        perfume['fragranticaId'] = fid
        perfume['fragranticaStatus'] = 'VERIFIED_LOCAL_CORPUS_V2'
        perfume['fragranticaLocalUrl'] = urls[fid]
        perfume['fragranticaVerificationSource'] = 'Shobi-first reviewed identity + local Fragrantica corpus'
        count += 1
        promoted.add(code)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    changed[path.name] = count

in_corpus = {code for code, value in APPROVED.items() if str(value[0]).strip() in urls}
missing = set(APPROVED) - in_corpus
probe_ids = ['200','204','456','520','719','905','925','970','993','1014','1061','1365','1499','2068','12201']
probe = {fid: (fid in parsed_ids) for fid in probe_ids}
lines = [
    '# Shobi-first residual promotion', '',
    f'- Local corpus numeric IDs parsed: **{len(parsed_ids)}**',
    f'- Reviewed exact identities with Fragrantica target: **{len(APPROVED)}**',
    f'- Target IDs present in local corpus: **{len(in_corpus)}**',
    f'- Target IDs missing from local corpus: **{len(missing)}**',
    f'- Promoted this run: **{len(promoted)}**',
    f'- Already verified with same ID: **{len(already_verified)}**',
    f'- Conflicting pre-existing VERIFIED mappings left untouched: **{len(conflicts)}**',
    f'- Identified but deliberately not forced: **{len(NO_FORCE)}**',
    f'- Probe IDs: **{probe}**',
]
for name, count in changed.items():
    lines.append(f'- {name}: **{count}** rows changed')
lines += ['', '## Exact targets', '']
for code, (fid, brand, name, rationale) in APPROVED.items():
    state = 'IN_CORPUS' if code in in_corpus else 'MISSING_FROM_CORPUS'
    if code in conflicts:
        state = 'VERIFIED_CONFLICT_NOT_OVERWRITTEN'
    elif code in already_verified:
        state = 'ALREADY_VERIFIED_SAME_ID'
    elif code in promoted:
        state = 'PROMOTED'
    lines.append(f'- `{code}` -> {brand} / {name} — ID {fid} — {state} — {rationale}')
lines += ['', '## Identified but not forced', '']
for code, (brand, name, reason) in NO_FORCE.items():
    lines.append(f'- `{code}` -> {brand} / {name} — NO_FORCE — {reason}')
OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')

print('parsed_ids', len(parsed_ids))
print('probe', probe)
print('sample_min', sorted(parsed_ids, key=lambda x: int(x))[:20])
print('reviewed', len(APPROVED))
print('in_corpus', len(in_corpus))
print('missing_from_corpus', len(missing))
print('promoted', len(promoted))
print('already_verified', len(already_verified))
print('conflicts', len(conflicts))
print('no_force', len(NO_FORCE))
print('changed', changed)
