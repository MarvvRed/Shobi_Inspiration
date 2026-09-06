import csv,json,re,unicodedata,itertools
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
def code_key(code):
    s=str(code or '').strip()
    if '-' in s:return norm(s.rsplit('-',1)[-1]).replace(' ','')
    m=re.match(r'([A-Za-z ]+)',s)
    return norm(m.group(1)).replace(' ','') if m else ''
def split_name(s):
    s=str(s or '').strip(); parts=re.split(r'\s+-\s+',s,maxsplit=1)
    core=parts[0].strip(); tail=parts[1].strip() if len(parts)>1 else ''
    core=re.sub(r'\s*\([^)]*\)\s*',' ',core).strip()
    return ' '.join(core.split()),tail
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
    if min(len(h),len(b))>=4 and (h in b or b in h):return .92
    return sim(h,b)*.75

def name_metrics(q,c):
    qn=norm(q); cn=c['nn']; qt=set(toks(q)); ct=c['nt']
    if not qn or not cn:return 0,0,0,0
    inter=len(qt&ct); recall=inter/len(qt) if qt else 0; precision=inter/len(ct) if ct else 0
    f1=(2*precision*recall/(precision+recall)) if precision+recall else 0
    sr=sim(qn,cn); short,longer=(qn,cn) if len(qn)<=len(cn) else (cn,qn)
    ratio=len(short)/len(longer) if longer else 0
    contain=.96 if min(len(qn),len(cn))>=4 and ratio>=.72 and short in longer else 0
    return max(sr,contain,1.0 if qn==cn else 0,f1),recall,precision,sr

def walk(o):
    if isinstance(o,list):
        for x in o: yield from walk(x)
    elif isinstance(o,dict):
        if isinstance(o.get('perfumes'),list):
            for p in o['perfumes']:
                if isinstance(p,dict): yield p
        elif 'code' in o or 'inspiredBy' in o: yield o

def brand_signatures(bn):
    ts=[t for t in bn.split() if len(t)>1 and t not in {'perfumes','parfums','fragrances','beauty','maison'}]
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

urls=[]; byid={}; inv=defaultdict(set); brand_idx=defaultdict(set); exact_name_idx=defaultdict(set)
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    c=parse(line)
    if not c or c['id'] in byid:continue
    byid[c['id']]=c; idx=len(urls); urls.append(c); brand_idx[c['bn']].add(idx); exact_name_idx[c['nn']].add(idx)
    for t in c['nt']:inv[t].add(idx)

sig_brands=defaultdict(set)
for bn in brand_idx:
    for sig in brand_signatures(bn):sig_brands[sig].add(bn)

def infer_code_brand(code):
    k=code_key(code)
    if len(k)<2:return ''
    hits=sig_brands.get(k,set())
    if len(hits)==1:
        bn=next(iter(hits)); return urls[next(iter(brand_idx[bn]))]['brand']
    return ''

brand_names=list(brand_idx)
def infer_tail_brand(tail):
    tn=norm(tail)
    if len(tn)<3:return ''
    tt=set(toks(tail)); scores=[]
    for bn in brand_names:
        bt=set(toks(bn)); inter=len(tt&bt); rec=inter/len(tt) if tt else 0
        sc=max(1.0 if tn==bn else 0,sim(tn,bn),rec if inter else 0)
        if sc>=.70:scores.append((sc,bn))
    scores.sort(reverse=True)
    if not scores:return ''
    margin=scores[0][0]-(scores[1][0] if len(scores)>1 else 0)
    if scores[0][0]>=.90 and margin>=.08:return urls[next(iter(brand_idx[scores[0][1]]))]['brand']
    return ''

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
    code=str(p.get('code') or '').strip() or '[no-code]'; raw_name=str(p.get('inspiredBy') or p.get('perfume') or '').strip(); qname,tail=split_name(raw_name)
    explicit=str(p.get('brand') or '').strip(); prior=brand_by_suffix.get(suffix(code),''); code_hint=infer_code_brand(code) if not explicit and not prior else ''; tail_hint=infer_tail_brand(tail) if not explicit and not prior and not code_hint else ''
    hint=explicit or prior or code_hint or tail_hint
    hint_source='field' if explicit else ('verified_suffix' if prior else ('code_signature' if code_hint else ('name_tail' if tail_hint else '')))
    brand_pool=set(brand_idx.get(norm(hint),set())) if hint else set(); ids=set()
    for t in toks(qname):ids.update(inv.get(t,set()))
    pool=brand_pool if brand_pool else (ids if ids else range(len(urls))); ranked=[]
    for idx in pool:
        c=urls[idx]; ns,recall,precision,sr=name_metrics(qname,c); bs=brand_sim(hint,c); total=.78*ns+.22*bs if hint else ns
        if hint and bs<.35:total*=.70
        if total>=.40 or ns>=.60:ranked.append((total,ns,bs,recall,precision,sr,c))
    ranked.sort(key=lambda x:(x[0],x[1],x[3],x[4],x[5]),reverse=True); top=ranked[:5]
    exact_global=list(exact_name_idx.get(norm(qname),set())); exact_unique=len(exact_global)==1
    exact_brand_ok=exact_unique and bool(hint) and exact_global[0] in brand_pool
    if exact_brand_ok:
        ei=exact_global[0]
        if not top or top[0][6]['id']!=urls[ei]['id']:
            c=urls[ei]; bs=brand_sim(hint,c); top=[(.78+.22*bs,1.0,bs,1.0,1.0,1.0,c)]+top; top=top[:5]
    if not top:cls='NO_CANDIDATE'
    else:
        margin=top[0][0]-(top[1][0] if len(top)>1 else 0); brand_ok=bool(hint) and top[0][2]>=.78
        strong_name=top[0][1]>=.94 and (top[0][5]>=.86 or (top[0][3]>=.90 and top[0][4]>=.70))
        if exact_brand_ok and top[0][6]['id']==urls[exact_global[0]]['id']:cls='STRONG_EXACT_BRAND'
        elif strong_name and brand_ok and margin>=.025:cls='STRONG_UNIQUE'
        elif exact_unique and not hint:cls='EXACT_NAME_NO_BRAND'
        elif top[0][0]>=.80 and top[0][1]>=.82 and brand_ok and margin>=.012:cls='GOOD_REVIEW'
        elif top[0][0]>=.62 or top[0][1]>=.70:cls='WEAK_REVIEW'
        else:cls='NO_CANDIDATE'
    r={'shobi_code':code,'shobi_name':raw_name,'match_name':qname,'shobi_brand':explicit,'inferred_brand':hint,'brand_source':hint_source,'classification':cls,'candidate_count':len(ranked)}
    for i,(sc,ns,bs,rc,pr,sr,c) in enumerate(top,1):r.update({f'cand{i}_id':c['id'],f'cand{i}_brand':c['brand'],f'cand{i}_name':c['name'],f'cand{i}_url':c['url'],f'cand{i}_score':f'{sc:.4f}',f'cand{i}_name_score':f'{ns:.4f}',f'cand{i}_brand_score':f'{bs:.4f}',f'cand{i}_recall':f'{rc:.4f}',f'cand{i}_precision':f'{pr:.4f}',f'cand{i}_seq':f'{sr:.4f}'})
    rows.append(r)
fields=['shobi_code','shobi_name','match_name','shobi_brand','inferred_brand','brand_source','classification','candidate_count']
for i in range(1,6):fields += [f'cand{i}_id',f'cand{i}_brand',f'cand{i}_name',f'cand{i}_url',f'cand{i}_score',f'cand{i}_name_score',f'cand{i}_brand_score',f'cand{i}_recall',f'cand{i}_precision',f'cand{i}_seq']
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
cnt=Counter(r['classification'] for r in rows); inferred=sum(bool(r['inferred_brand']) for r in rows)
lines=['# Fragrantica v2 match against local perfume_urls.txt','',f'- URLs parsed: **{len(urls)}**',f'- Residual rows scanned: **{len(rows)}**',f'- Residuals with local brand hint: **{inferred}**',f'- Suffix brand priors learned: **{len(brand_by_suffix)}**']
for k in ['STRONG_EXACT_BRAND','STRONG_UNIQUE','GOOD_REVIEW','EXACT_NAME_NO_BRAND','WEAK_REVIEW','NO_CANDIDATE']:lines.append(f'- {k}: **{cnt[k]}**')
lines += ['','No Fragrantica web access is used. Matching uses only repository-local `perfume_urls.txt` plus local Shobi code/verified metadata. Exact-name matches without brand agreement are NOT classified strong. Code abbreviations are accepted as brand hints only when their generated signature maps to exactly one corpus brand. No mapping is promoted automatically.','','## Strong candidates','']
for r in rows:
    if r['classification'] in {'STRONG_EXACT_BRAND','STRONG_UNIQUE'}:lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} -> {r.get('cand1_brand','')} / {r.get('cand1_name','')} — ID {r.get('cand1_id','')} — {r['classification']} — brand-source {r['brand_source']}")
lines += ['','## Good review candidates','']
for r in rows:
    if r['classification']=='GOOD_REVIEW':lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} -> {r.get('cand1_brand','')} / {r.get('cand1_name','')} — ID {r.get('cand1_id','')} — score {r.get('cand1_score','')}")
lines += ['','## Exact local name but no brand agreement','']
for r in rows:
    if r['classification']=='EXACT_NAME_NO_BRAND':lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} -> {r.get('cand1_brand','')} / {r.get('cand1_name','')} — ID {r.get('cand1_id','')} — NOT promoted")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('urls',len(urls),'residuals',len(rows),'priors',len(brand_by_suffix),dict(cnt))
