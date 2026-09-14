#!/usr/bin/env python3
import json, re, shutil, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'note-icons'
NEW = ROOT / 'public' / 'note-icons'
INDEX = NEW / 'index.json'
OLDMAP = OLD / 'map.js'
NEWMAP = NEW / 'map.js'

prefix='window.FRAGRANTICA_NOTE_ICON_MAP='
old_text=OLDMAP.read_text(encoding='utf-8').strip()
old_map=json.loads(old_text[len(prefix):].rstrip(';'))
idx=json.loads(INDEX.read_text(encoding='utf-8'))

def norm(s):
    s=str(s or '').lower().replace('™','')
    s=unicodedata.normalize('NFKD', s)
    s=''.join(ch for ch in s if not unicodedata.combining(ch))
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

by_norm={norm(x.get('slug')):x for x in idx if x.get('status')=='ok' and x.get('file')}
aliases={
 'almonds':'almond',
 'aloe':'aloe vera',
 'amalfi lemon':'lemon',
 'ambrofix':'ambrofix',
 'aqual':'aqual',
 'cedarwood':'cedar',
 'cocoa':'cacao pod',
 'fruits':'fruity notes',
 'frosting glace':'frosting',
 'meringue':'sugar',
 'poplar populus':'cottonwood poplar',
 'strawberry s mores':'strawberry',
 'tiare and oud':'tiare flower',
 'verbena':'lemon verbena',
 'white ginger':'ginger',
}

new_map={}
unresolved=[]
resolved_aliases={}
for key in old_map:
    nk=norm(key)
    rec=by_norm.get(nk)
    if not rec:
        target=aliases.get(nk)
        rec=by_norm.get(norm(target)) if target else None
        if rec: resolved_aliases[key]=rec['slug']
    if not rec:
        unresolved.append(key); continue
    new_map[key]=f"public/note-icons/{rec['file']}"

if unresolved:
    raise SystemExit('Unresolved note icons: '+', '.join(unresolved))
if len(new_map)!=len(old_map):
    raise SystemExit(f'Map size mismatch {len(new_map)} != {len(old_map)}')
for p in new_map.values():
    if not (ROOT/p).is_file(): raise SystemExit('Missing new icon '+p)

NEWMAP.write_text(prefix+json.dumps(new_map,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')

repls={
 'src="note-icons/map.js"':'src="public/note-icons/map.js"',
 "src='note-icons/map.js'":"src='public/note-icons/map.js'",
 'ROOT / "note-icons" / "map.js"':'ROOT / "public" / "note-icons" / "map.js"',
 "ROOT / 'note-icons' / 'map.js'":"ROOT / 'public' / 'note-icons' / 'map.js'",
}
changed=[]
for path in ROOT.rglob('*'):
    if not path.is_file() or '.git' in path.parts or path == NEWMAP: continue
    if OLD in path.parents: continue
    if path.suffix.lower() not in {'.py','.js','.html','.yml','.yaml','.md'}: continue
    try: text=path.read_text(encoding='utf-8')
    except Exception: continue
    new=text
    for a,b in repls.items(): new=new.replace(a,b)
    if new!=text:
        path.write_text(new,encoding='utf-8'); changed.append(str(path.relative_to(ROOT)))

if 'public/note-icons/map.js' not in (ROOT/'index.html').read_text(encoding='utf-8'):
    raise SystemExit('index.html not migrated')
validator=(ROOT/'tools'/'build_validation_audit.py').read_text(encoding='utf-8')
if 'ROOT / "public" / "note-icons" / "map.js"' not in validator:
    raise SystemExit('validator not migrated')

shutil.rmtree(OLD)

report = [
 '# Note icon migration report','',
 f'- New library icons available: **{sum(1 for x in idx if x.get("status")=="ok" and x.get("file"))}**',
 f'- Site map keys preserved: **{len(new_map)}**',
 f'- Alias mappings required: **{len(resolved_aliases)}**',
 '- Legacy `note-icons/` directory removed: **yes**',
 '- Site now loads: `public/note-icons/map.js`','',
 '## Alias mappings',
]
for k,v in sorted(resolved_aliases.items()): report.append(f'- {k} → {v}')
report += ['', '## Updated references'] + [f'- {x}' for x in changed]
(ROOT/'note-icon-migration-report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
print(f'migrated {len(new_map)} keys; aliases {len(resolved_aliases)}; files {len(changed)}')
