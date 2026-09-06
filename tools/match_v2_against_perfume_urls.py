import csv,json,re,unicodedata
from pathlib import Path
from difflib import SequenceMatcher

URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
DB=Path('database_v2_clean.json')
OUT=Path('fragrantica-v2-local-url-match.csv')
REPORT=Path('fragrantica-v2-local-url-match.md')

STOP={'eau','de','parfum','perfume','toilette','edp','edt','for','men','women','man','woman','pour','homme','femme','the','by','and','limited','edition'}

def ascii_norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def toks(s):
    return [x for x in ascii_norm(s).split() if x not in STOP and len(x)>1]

def parse_url(u):
    u=u.strip()
    m=re.search(r'/perfume/([^/]+)/([^/]+?)-(\d+)\.html(?:\?.*)?$',u,re.I)
    if not m: return None
    brand_slug,name_slug,fid=m.groups()
    brand=brand_slug.replace('-',' ')
    name=name_slug.replace('-',' ')
    return {'url':u,'id':fid,'brand':brand,'name':name,'full':brand+' '+name}

def score(query,c):
    q=toks(query); qt=set(q)
    ct=set(toks(c['full']))
    if not q or not ct: return 0.0,0.0,0.0
    inter=len(qt&ct); union=len(qt|ct)
    jac=inter/union if union else 0
    cov=inter/len(qt)
    seq=SequenceMatcher(None,' '.join(q),' '.join(toks(c['full']))).ratio()
    return max((jac+cov)/2,seq*0.85),cov,jac

urls=[]
seen=set()
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    c=parse_url(line)
    if c and c['id'] not in seen:
        urls.append(c); seen.add(c['id'])

raw=json.loads(DB.read_text(encoding='utf-8-sig'))
rows=[]
def walk(o):
    if isinstance(o,list):
        for x in o: yield from walk(x)
    elif isinstance(o,dict):
        if 'perfumes' in o and isinstance(o['perfumes'],list):
            for p in o['perfumes']:
                if isinstance(p,dict): yield p
        elif 'code' in o or 'inspiredBy' in o: yield o

for p in walk(raw):
    status=str(p.get('fragranticaStatus') or '')
    if status.startswith('VERIFIED_'): continue
    code=str(p.get('code') or '').strip() or '[no-code]'
    name=str(p.get('inspiredBy') or p.get('perfume') or '').strip()
    brand=str(p.get('brand') or '').strip()
    query=(name+' '+brand).strip()
    ranked=[]
    for c in urls:
        sc,cov,jac=score(query,c)
        if sc>=0.42 or cov>=0.60:
            ranked.append((sc,cov,jac,c))
    ranked.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
    top=ranked[:5]
    # conservative classification only; no promotion here
    if not top:
        cls='NO_CANDIDATE'
    elif top[0][0]>=0.86 and top[0][1]>=0.80 and (len(top)==1 or top[0][0]-top[1][0]>=0.08):
        cls='STRONG_UNIQUE'
    elif top[0][0]>=0.72 and top[0][1]>=0.70:
        cls='GOOD_REVIEW'
    else:
        cls='WEAK_REVIEW'
    rec={'shobi_code':code,'shobi_name':name,'shobi_brand':brand,'classification':cls,'candidate_count':len(ranked)}
    for i,(sc,cov,jac,c) in enumerate(top,1):
        rec[f'cand{i}_id']=c['id']; rec[f'cand{i}_brand']=c['brand']; rec[f'cand{i}_name']=c['name']; rec[f'cand{i}_url']=c['url']; rec[f'cand{i}_score']=f'{sc:.4f}'; rec[f'cand{i}_coverage']=f'{cov:.4f}'
    rows.append(rec)

fields=['shobi_code','shobi_name','shobi_brand','classification','candidate_count']
for i in range(1,6):
    fields += [f'cand{i}_id',f'cand{i}_brand',f'cand{i}_name',f'cand{i}_url',f'cand{i}_score',f'cand{i}_coverage']
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

from collections import Counter
cnt=Counter(r['classification'] for r in rows)
lines=['# Fragrantica v2 match against local perfume_urls.txt','',f'- URLs parsed: **{len(urls)}**',f'- Residual rows scanned: **{len(rows)}**']
for k in ['STRONG_UNIQUE','GOOD_REVIEW','WEAK_REVIEW','NO_CANDIDATE']:
    lines.append(f'- {k}: **{cnt[k]}**')
lines += ['','No web access is used by this matcher. No mapping is promoted automatically.','','## Strong unique candidates','']
for r in rows:
    if r['classification']=='STRONG_UNIQUE':
        lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} -> {r.get('cand1_brand','')} / {r.get('cand1_name','')} — ID {r.get('cand1_id','')} — score {r.get('cand1_score','')}")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('urls',len(urls),'residuals',len(rows),dict(cnt))
