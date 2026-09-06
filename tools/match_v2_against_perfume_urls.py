import csv,json,re,unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from collections import Counter,defaultdict

URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
DB=Path('database_v2_clean.json')
OUT=Path('fragrantica-v2-local-url-match.csv')
REPORT=Path('fragrantica-v2-local-url-match.md')
STOP={'eau','de','parfum','perfume','toilette','edp','edt','for','men','women','man','woman','pour','homme','femme','the','by','and','limited','edition','cologne'}

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())
def toks(s): return [x for x in norm(s).split() if x not in STOP and len(x)>1]
def suffix(code): return norm(str(code or '').rsplit('-',1)[-1]).replace(' ','') if '-' in str(code or '') else ''
def parse(u):
    m=re.search(r'/perfume/([^/]+)/([^/]+?)-(\d+)\.html',u.strip(),re.I)
    if not m:return None
    b,n,i=m.groups(); b=b.replace('-',' '); n=n.replace('-',' ')
    return {'url':u.strip(),'id':i,'brand':b,'name':n,'bn':norm(b),'nn':norm(n),'nt':set(toks(n))}
def sim(a,b): return SequenceMatcher(None,norm(a),norm(b)).ratio()
def brand_sim(h,c):
    if not h:return 0
    h=norm(h); b=c['bn']
    if h==b:return 1
    if len(h)>3 and (h in b or b in h):return .92
    return sim(h,b)*.75

def walk(o):
    if isinstance(o,list):
        for x in o: yield from walk(x)
    elif isinstance(o,dict):
        if isinstance(o.get('perfumes'),list):
            for p in o['perfumes']:
                if isinstance(p,dict): yield p
        elif 'code' in o or 'inspiredBy' in o: yield o

urls=[]; byid={}; inv=defaultdict(set)
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    c=parse(line)
    if not c or c['id'] in byid:continue
    byid[c['id']]=c; idx=len(urls); urls.append(c)
    for t in c['nt']:inv[t].add(idx)

perf=list(walk(json.loads(DB.read_text(encoding='utf-8-sig'))))
priors=defaultdict(Counter)
for p in perf:
    if not str(p.get('fragranticaStatus') or '').startswith('VERIFIED_'):continue
    c=byid.get(str(p.get('fragranticaId') or '').strip()); s=suffix(p.get('code'))
    if c and s:priors[s][c['brand']]+=1
brand_by_suffix={s:c.most_common(1)[0][0] for s,c in priors.items() if c.most_common(1)[0][1]/sum(c.values())>=.6}

rows=[]
for p in perf:
    if str(p.get('fragranticaStatus') or '').startswith('VERIFIED_'):continue
    code=str(p.get('code') or '').strip() or '[no-code]'; name=str(p.get('inspiredBy') or p.get('perfume') or '').strip()
    explicit=str(p.get('brand') or '').strip(); hint=explicit or brand_by_suffix.get(suffix(code),'')
    ids=set()
    for t in toks(name):ids.update(inv.get(t,set()))
    pool=ids or range(len(urls)); ranked=[]; qt=set(toks(name)); qn=norm(name)
    for idx in pool:
        c=urls[idx]; inter=len(qt&c['nt']); cov=inter/len(qt) if qt else 0
        ns=max(sim(qn,c['nn']),1 if qn==c['nn'] else (.96 if len(qn)>=5 and (qn in c['nn'] or c['nn'] in qn) else 0),cov)
        bs=brand_sim(hint,c); total=.74*ns+.26*bs if hint else ns
        if hint and bs<.35:total*=.72
        if total>=.4 or ns>=.62:ranked.append((total,ns,bs,cov,c))
    ranked.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True); top=ranked[:5]
    if not top:cls='NO_CANDIDATE'
    else:
        margin=top[0][0]-(top[1][0] if len(top)>1 else 0); ok=(not hint) or top[0][2]>=.78
        if top[0][1]>=.94 and ok and margin>=.035:cls='STRONG_UNIQUE'
        elif top[0][0]>=.78 and top[0][1]>=.8 and ok and margin>=.015:cls='GOOD_REVIEW'
        elif top[0][0]>=.62 or top[0][1]>=.72:cls='WEAK_REVIEW'
        else:cls='NO_CANDIDATE'
    r={'shobi_code':code,'shobi_name':name,'shobi_brand':explicit,'inferred_brand':hint,'classification':cls,'candidate_count':len(ranked)}
    for i,(sc,ns,bs,cov,c) in enumerate(top,1):
        r.update({f'cand{i}_id':c['id'],f'cand{i}_brand':c['brand'],f'cand{i}_name':c['name'],f'cand{i}_url':c['url'],f'cand{i}_score':f'{sc:.4f}',f'cand{i}_name_score':f'{ns:.4f}',f'cand{i}_brand_score':f'{bs:.4f}',f'cand{i}_coverage':f'{cov:.4f}'})
    rows.append(r)
fields=['shobi_code','shobi_name','shobi_brand','inferred_brand','classification','candidate_count']
for i in range(1,6):fields += [f'cand{i}_id',f'cand{i}_brand',f'cand{i}_name',f'cand{i}_url',f'cand{i}_score',f'cand{i}_name_score',f'cand{i}_brand_score',f'cand{i}_coverage']
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
cnt=Counter(r['classification'] for r in rows); inferred=sum(bool(r['inferred_brand']) for r in rows)
lines=['# Fragrantica v2 match against local perfume_urls.txt','',f'- URLs parsed: **{len(urls)}**',f'- Residual rows scanned: **{len(rows)}**',f'- Residuals with local brand hint: **{inferred}**',f'- Suffix brand priors learned: **{len(brand_by_suffix)}**']
for k in ['STRONG_UNIQUE','GOOD_REVIEW','WEAK_REVIEW','NO_CANDIDATE']:lines.append(f'- {k}: **{cnt[k]}**')
lines += ['','No Fragrantica web access is used. Matching uses only repository-local `perfume_urls.txt` plus already-verified rows for brand priors. No mapping is promoted automatically.','','## Strong unique candidates','']
for r in rows:
    if r['classification']=='STRONG_UNIQUE':lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} -> {r.get('cand1_brand','')} / {r.get('cand1_name','')} — ID {r.get('cand1_id','')} — score {r.get('cand1_score','')}")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('urls',len(urls),'residuals',len(rows),'priors',len(brand_by_suffix),dict(cnt))
