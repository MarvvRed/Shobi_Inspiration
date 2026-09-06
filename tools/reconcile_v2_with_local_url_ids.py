import csv,re,unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from collections import Counter

URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
IDENT=Path('fragrantica-v2-identity-audit.csv')
LOCAL=Path('fragrantica-v2-local-url-match.csv')
OUT=Path('fragrantica-v2-local-id-reconciliation.csv')
REPORT=Path('fragrantica-v2-local-id-reconciliation.md')

STOP={'eau','de','parfum','perfume','toilette','edp','edt','for','men','women','man','woman','pour','homme','femme','the','by','and','limited','edition','fragrance'}

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    s=s.replace('&',' and ')
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def toks(s): return [x for x in norm(s).split() if x not in STOP and len(x)>1]

def similarity(a,b):
    ta=set(toks(a)); tb=set(toks(b))
    if not ta or not tb: return 0.0,0.0,0.0
    inter=len(ta&tb); cov=inter/len(ta); jac=inter/len(ta|tb)
    seq=SequenceMatcher(None,' '.join(toks(a)),' '.join(toks(b))).ratio()
    return max((cov+jac)/2,seq),cov,jac

def parse_url(u):
    m=re.search(r'/perfume/([^/]+)/([^/]+?)-(\d+)\.html(?:\?.*)?$',u.strip(),re.I)
    if not m: return None
    brand,name,fid=m.groups()
    return fid,brand.replace('-',' '),name.replace('-',' '),u.strip()

by_id={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    p=parse_url(line)
    if p and p[0] not in by_id: by_id[p[0]]=p[1:]

ident={}
with IDENT.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f): ident[r['shobi_code'] or '[no-code]']=r
local={}
with LOCAL.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f): local[r['shobi_code'] or '[no-code]']=r

rows=[]; counts=Counter()
for code,l in local.items():
    i=ident.get(code,{})
    shobi=l.get('shobi_name','')
    hist=(i.get('fragrantica_id') or '').strip()
    top=(l.get('cand1_id') or '').strip()
    hist_url=by_id.get(hist)
    top_url=by_id.get(top)
    hs=hc=hj=0.0
    if hist_url:
        hb,hn,hu=hist_url; hs,hc,hj=similarity(shobi,hb+' '+hn)
    ts=tc=tj=0.0
    if top_url:
        tb,tn,tu=top_url; ts,tc,tj=similarity(shobi,tb+' '+tn)
    if hist and hist_url and (hs>=0.72 or hc>=0.80):
        cls='HIST_ID_CONFIRMED_LOCAL'
    elif hist and hist_url and top and top!=hist and ts>=0.80 and tc>=0.80 and ts-hs>=0.15:
        cls='HIST_ID_CONFLICT_LOCAL_BETTER'
    elif hist and hist_url:
        cls='HIST_ID_PRESENT_NEEDS_REVIEW'
    elif hist and not hist_url:
        cls='HIST_ID_ABSENT_FROM_LOCAL'
    elif not hist and top and (ts>=0.82 and tc>=0.80):
        cls='NEW_LOCAL_STRONG'
    elif not hist and top:
        cls='NEW_LOCAL_REVIEW'
    else:
        cls='NO_LOCAL_CANDIDATE'
    counts[cls]+=1
    rec={
        'shobi_code':code,'shobi_name':shobi,'classification':cls,
        'historical_id':hist,'historical_in_local':'yes' if hist_url else 'no',
        'historical_local_brand':hist_url[0] if hist_url else '',
        'historical_local_name':hist_url[1] if hist_url else '',
        'historical_local_url':hist_url[2] if hist_url else '',
        'historical_score':f'{hs:.4f}','historical_coverage':f'{hc:.4f}',
        'top_local_id':top,
        'top_local_brand':top_url[0] if top_url else '',
        'top_local_name':top_url[1] if top_url else '',
        'top_local_url':top_url[2] if top_url else '',
        'top_score':f'{ts:.4f}','top_coverage':f'{tc:.4f}'
    }
    rows.append(rec)

fields=list(rows[0].keys())
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

order=['HIST_ID_CONFIRMED_LOCAL','HIST_ID_CONFLICT_LOCAL_BETTER','HIST_ID_PRESENT_NEEDS_REVIEW','HIST_ID_ABSENT_FROM_LOCAL','NEW_LOCAL_STRONG','NEW_LOCAL_REVIEW','NO_LOCAL_CANDIDATE']
lines=['# Fragrantica v2 local-ID reconciliation','',f'- Residual rows: **{len(rows)}**',f'- Local Fragrantica URLs indexed by ID: **{len(by_id)}**']
for k in order: lines.append(f'- {k}: **{counts[k]}**')
lines += ['','No web access. This reconciliation uses only perfume_urls.txt + repository audit files.','','## Conflicts where local URL suggests a better ID','']
for r in rows:
    if r['classification']=='HIST_ID_CONFLICT_LOCAL_BETTER':
        lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} — old ID {r['historical_id']} => {r['historical_local_brand']} / {r['historical_local_name']} (score {r['historical_score']}); local candidate ID {r['top_local_id']} => {r['top_local_brand']} / {r['top_local_name']} (score {r['top_score']})")
lines += ['','## Newly strong local candidates without historical ID','']
for r in rows:
    if r['classification']=='NEW_LOCAL_STRONG':
        lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} -> {r['top_local_brand']} / {r['top_local_name']} — ID {r['top_local_id']} — score {r['top_score']}")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(dict(counts))
