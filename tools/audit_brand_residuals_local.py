import json, re, unicodedata
from pathlib import Path
from urllib.parse import urlparse, unquote

DB=Path('database_complete.json')
CORPUS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
OUT=Path('brand-residual-local-audit.md')
rows=json.loads(DB.read_text(encoding='utf-8'))

TARGET_CODES={
'118-HAM','166-AZ','171-DUP','254-JOM','287-JOM','304-KIE','307-LOC','309-LOC',
'325-PECK','327-PECK','523-DRC','534-DRC','637-EST','992-ZAD','993-ZAD','994-ZAD',
'1118-FAB','2016-PARELM'
}

def norm(s):
    s=unicodedata.normalize('NFKD', str(s or '')).encode('ascii','ignore').decode('ascii').lower()
    s=s.replace('&',' and ')
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def perfume_id(url):
    m=re.search(r'-(\d+)\.html(?:$|[?#])',url)
    return m.group(1) if m else ''

def parts(url):
    ps=[unquote(p) for p in urlparse(url).path.split('/') if p]
    if len(ps)>=3 and ps[0] in {'perfume','parfem'}:
        return ps[1], ps[2]
    return '',''

urls=[u.strip() for u in CORPUS.read_text(encoding='utf-8',errors='ignore').splitlines() if u.strip()]
by_id={}
name_index=[]
for u in urls:
    fid=perfume_id(u)
    if fid: by_id.setdefault(fid,[]).append(u)
    brand_slug, perf_slug=parts(u)
    if brand_slug and perf_slug:
        base=re.sub(r'-\d+\.html$','',perf_slug)
        name_index.append((norm(base.replace('-',' ')),u))

lines=['# Residual brand lookup in local Fragrantica corpus','']
for p in rows:
    code=str(p.get('code') or '')
    if code not in TARGET_CODES: continue
    fid=str(p.get('fragranticaId') or p.get('fragrantica_id') or '').strip()
    name=str(p.get('inspiredBy') or '')
    exact=by_id.get(fid,[])
    q=norm(name)
    exact_name=[u for n,u in name_index if n==q]
    token_name=[u for n,u in name_index if q and (q in n or n in q)][:20]
    lines += [f'## {code} — {name}', f'- Fragrantica ID: `{fid}`', f'- Exact ID hits: **{len(exact)}**']
    for u in exact[:10]: lines.append(f'  - {u}')
    lines.append(f'- Exact normalized-name hits: **{len(exact_name)}**')
    for u in exact_name[:10]: lines.append(f'  - {u}')
    if not exact and not exact_name:
        lines.append(f'- Containment-name candidates: **{len(token_name)}**')
        for u in token_name[:10]: lines.append(f'  - {u}')
    lines.append('')

OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('audited residuals',len(TARGET_CODES))
