import csv,re,unicodedata,itertools
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict

URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
CSV=Path('fragrantica-v2-local-url-match.csv')
OUT=Path('fragrantica-v2-local-disambiguation.md')

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())

def code_key(code):
    s=str(code or '').strip()
    if '-' in s:return norm(s.rsplit('-',1)[-1]).replace(' ','')
    m=re.match(r'([A-Za-z ]+)',s)
    return norm(m.group(1)).replace(' ','') if m else ''

def parse_url(u):
    m=re.search(r'/perfume/([^/]+)/([^/]+?)-(\d+)\.html',u.strip(),re.I)
    if not m:return None
    b,n,fid=m.groups()
    return {'brand':b.replace('-',' '),'name':n.replace('-',' '),'id':fid,'url':u.strip()}

def sigs(brand):
    ts=[t for t in norm(brand).split() if len(t)>1 and t not in {'perfumes','parfums','fragrances','beauty','maison'}]
    out=set(); joined=''.join(ts)
    for n in range(2,min(7,len(joined))+1):out.add(joined[:n])
    for t in ts:
        for n in range(2,min(6,len(t))+1):out.add(t[:n])
    for take in (ts[:2],ts[:3]):
        if len(take)<2:continue
        ranges=[range(1,min(4,len(t))+1) for t in take]
        for lens in itertools.product(*ranges):
            x=''.join(t[:n] for t,n in zip(take,lens))
            if 2<=len(x)<=7:out.add(x)
    return out

def score(a,b):
    a=norm(a); b=norm(b)
    if not a or not b:return 0
    if a==b:return 1
    seq=SequenceMatcher(None,a,b).ratio()
    at=set(a.split()); bt=set(b.split()); inter=len(at&bt)
    f1=2*inter/(len(at)+len(bt)) if at and bt else 0
    return max(seq,f1)

urls=[]; by_brand=defaultdict(list); sig_brands=defaultdict(set)
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    x=parse_url(line)
    if not x:continue
    urls.append(x); by_brand[norm(x['brand'])].append(x)
for bn,items in by_brand.items():
    for s in sigs(items[0]['brand']):sig_brands[s].add(bn)

rows=list(csv.DictReader(CSV.open(encoding='utf-8-sig')))
targets=[r for r in rows if r.get('classification') in {'EXACT_NAME_NO_BRAND','WEAK_REVIEW','NO_CANDIDATE'} and not r.get('inferred_brand')]
resolved=[]; ambiguous=[]
for r in targets:
    k=code_key(r.get('shobi_code')); q=r.get('match_name') or r.get('shobi_name') or ''
    brands=sig_brands.get(k,set()) if len(k)>=2 else set()
    ranked=[]
    for bn in brands:
        best=None
        for x in by_brand[bn]:
            sc=score(q,x['name'])
            if best is None or sc>best[0]:best=(sc,x)
        if best:ranked.append(best)
    ranked.sort(key=lambda z:z[0],reverse=True)
    if ranked:
        margin=ranked[0][0]-(ranked[1][0] if len(ranked)>1 else 0)
        if ranked[0][0]>=0.90 and margin>=0.08:
            resolved.append((r,ranked[0][0],margin,ranked[0][1],len(brands)))
        elif ranked[0][0]>=0.80:
            ambiguous.append((r,ranked[:3],len(brands)))

lines=['# Local code-brand disambiguation','',f'- Residual no-brand rows inspected: **{len(targets)}**',f'- Resolved with code signature + perfume name: **{len(resolved)}**',f'- Ambiguous but useful: **{len(ambiguous)}**','', 'No web access. Evidence comes only from repository-local `perfume_urls.txt` and Shobi codes/names.','', '## Resolved','']
for r,sc,margin,x,nbrands in resolved:
    lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} -> {x['brand']} / {x['name']} — ID {x['id']} — score {sc:.4f}, margin {margin:.4f}, code-brand candidates {nbrands}")
lines += ['', '## Ambiguous','']
for r,top,nbrands in ambiguous:
    cand='; '.join(f"{x['brand']} / {x['name']} (ID {x['id']}, {sc:.4f})" for sc,x in top)
    lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} — code-brand candidates {nbrands} — {cand}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('targets',len(targets),'resolved',len(resolved),'ambiguous',len(ambiguous))
