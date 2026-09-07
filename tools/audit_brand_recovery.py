import csv, json, re
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import urlparse, unquote

DB=Path('database_complete.json')
AUDIT=Path('fragrantica-v2-identity-audit.csv')
CORPUS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
OUT=Path('brand-recovery-audit.md')
rows=json.loads(DB.read_text(encoding='utf-8'))

def designer_slug(url):
    if not url: return ''
    parts=[p for p in urlparse(url).path.split('/') if p]
    if len(parts)>=3 and parts[0] in {'perfume','parfem'}: return unquote(parts[1])
    return ''

def display_slug(slug):
    # Used only when an exact Fragrantica URL identifies the designer but the audit has no display spelling.
    s=unquote(slug).replace('-', ' ').strip()
    return ' '.join(w if (w.isupper() and len(w)<=4) else w.capitalize() for w in s.split())

def perfume_id(url):
    m=re.search(r'-(\d+)\.html(?:$|[?#])', str(url or ''))
    return m.group(1) if m else ''

def suffix(code):
    m=re.search(r'-([A-Za-z0-9]+)$', str(code or ''))
    return m.group(1).upper() if m else ''

by_code={}
slug_names=defaultdict(Counter)
with AUDIT.open(encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        code=(r.get('shobi_code') or '').strip()
        brand=(r.get('fragrantica_brand') or '').strip()
        url=(r.get('fragrantica_url') or '').strip()
        by_code[code]=(brand,url)
        sl=designer_slug(url)
        if sl and brand: slug_names[sl][brand]+=1

slug_brand={sl:c.most_common(1)[0][0] for sl,c in slug_names.items() if len(c)==1}

id_urls=defaultdict(list)
for line in CORPUS.read_text(encoding='utf-8',errors='ignore').splitlines():
    u=line.strip()
    fid=perfume_id(u)
    if fid: id_urls[fid].append(u)

source={}
method={}
for p in rows:
    code=str(p.get('code') or '')
    b,url=by_code.get(code,('',''))
    if b:
        source[code]=b; method[code]='audit_brand'; continue
    fid=str(p.get('fragranticaId') or p.get('fragrantica_id') or '').strip()
    candidates=[('verified_url',url),('verified_url',str(p.get('fragrantica_url') or '')),('local_url',str(p.get('fragranticaLocalUrl') or ''))]
    candidates += [('exact_corpus_id',u) for u in id_urls.get(fid,[])]
    slugs=[]
    for kind,u in candidates:
        sl=designer_slug(u)
        if sl: slugs.append((kind,sl))
    # Exact identity sources must agree on designer slug if more than one is present.
    unique={sl for _,sl in slugs}
    if len(unique)==1:
        kind,sl=slugs[0]
        source[code]=slug_brand.get(sl) or display_slug(sl)
        method[code]='exact_designer_path' if sl not in slug_brand else ('exact_corpus_id' if any(k=='exact_corpus_id' for k,_ in slugs) else 'verified_url_slug')

# One already web-verified record has no retained numeric ID/URL in the complete DB.
source.setdefault('pid:2688','Ajmal')
method.setdefault('pid:2688','prior_verified_identity')

suffix_brands=defaultdict(set)
for p in rows:
    code=str(p.get('code') or '')
    if code in source and suffix(code): suffix_brands[suffix(code)].add(source[code])
unanimous={s:next(iter(bs)) for s,bs in suffix_brands.items() if len(bs)==1}
conflicts={s:sorted(bs) for s,bs in suffix_brands.items() if len(bs)>1}

resolved={}
for p in rows:
    code=str(p.get('code') or '')
    current=str(p.get('brand') or '').strip()
    if current.lower() not in {'','unknown brand','unknown','n/a','na','none','null','-'}:
        resolved[code]=(current,'existing'); continue
    if code in source:
        resolved[code]=(source[code],method[code]); continue
    s=suffix(code)
    if s in unanimous:
        resolved[code]=(unanimous[s],'code_suffix_unanimous')

def status(p): return str(p.get('fragrantica_status') or p.get('fragranticaStatus') or '').upper()
official=[p for p in rows if not status(p).startswith('RESOLVED_NO_FORCE')]
unresolved=[p for p in official if str(p.get('code') or '') not in resolved]
methods=Counter(resolved[str(p.get('code'))][1] for p in official if str(p.get('code') or '') in resolved)
brands=Counter(resolved[str(p.get('code'))][0] for p in official if str(p.get('code') or '') in resolved)

lines=['# Deterministic brand recovery audit','',f'- Official records: **{len(official)}**',f'- Recoverable deterministically: **{len(official)-len(unresolved)}**',f'- Still unresolved: **{len(unresolved)}**',f'- Conflicting code suffixes: **{len(conflicts)}**','', '## Recovery methods','', '| Method | Records |','|---|---:|']
for m,n in methods.most_common(): lines.append(f'| {m} | {n} |')
lines += ['','## Conflicting suffix mappings','']
if conflicts:
    lines += ['| Suffix | Brands |','|---|---|']
    for s,bs in sorted(conflicts.items()): lines.append(f"| {s} | {' / '.join(bs)} |")
else: lines.append('None.')
lines += ['','## Still unresolved official records','']
if unresolved:
    lines += ['| Code | Inspired by | Fragrantica ID | Status |','|---|---|---:|---|']
    for p in unresolved:
        lines.append(f"| {p.get('code','')} | {str(p.get('inspiredBy') or '').replace('|','\\|')} | {p.get('fragranticaId','')} | {status(p)} |")
else: lines.append('None.')
lines += ['','## Top recovered brands','', '| Brand | Records |','|---|---:|']
for b,n in brands.most_common(50): lines.append(f'| {b} | {n} |')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('official',len(official),'resolved',len(official)-len(unresolved),'unresolved',len(unresolved),'conflicts',len(conflicts))
