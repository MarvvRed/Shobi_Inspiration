import csv,re,unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict,Counter

URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
MATCH=Path('fragrantica-v2-local-url-match.csv')
OUT=Path('fragrantica-v2-global-fallback-review.csv')
REPORT=Path('fragrantica-v2-global-fallback-review.md')
STOP={'eau','de','parfum','perfume','toilette','edp','edt','for','men','women','man','woman','pour','homme','femme','the','by','and','limited','edition','cologne'}

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())
def toks(s): return [x for x in norm(s).split() if x not in STOP and len(x)>1]
def sim(a,b): return SequenceMatcher(None,norm(a),norm(b)).ratio()
def parse(u):
    m=re.search(r'/perfume/([^/]+)/([^/]+?)-(\d+)\.html',u.strip(),re.I)
    if not m:return None
    b,n,i=m.groups(); return {'url':u.strip(),'id':i,'brand':b.replace('-',' '),'name':n.replace('-',' ')}
def metrics(q,c):
    qn=norm(q); cn=norm(c['name']); qt=set(toks(q)); ct=set(toks(c['name']))
    if not qn or not cn:return 0,0,0,0
    inter=len(qt&ct); recall=inter/len(qt) if qt else 0; precision=inter/len(ct) if ct else 0
    f1=2*recall*precision/(recall+precision) if recall+precision else 0
    sr=sim(qn,cn); short,longer=(qn,cn) if len(qn)<=len(cn) else (cn,qn); ratio=len(short)/len(longer) if longer else 0
    contain=.96 if min(len(qn),len(cn))>=4 and ratio>=.72 and short in longer else 0
    return max(sr,f1,contain,1.0 if qn==cn else 0),recall,precision,sr

urls=[]; inv=defaultdict(set)
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    c=parse(line)
    if not c:continue
    idx=len(urls); urls.append(c)
    for t in set(toks(c['name'])):inv[t].add(idx)

with MATCH.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
out=[]; counts=Counter()
for r in rows:
    if r.get('classification') not in {'WEAK_REVIEW','NO_CANDIDATE','GOOD_REVIEW'}:continue
    q=r.get('match_name') or r.get('shobi_name') or ''
    ids=set()
    for t in toks(q): ids.update(inv.get(t,set()))
    if not ids:continue
    ranked=[]
    for idx in ids:
        c=urls[idx]; ns,rc,pr,sr=metrics(q,c)
        if ns>=.64:ranked.append((ns,rc,pr,sr,c))
    ranked.sort(key=lambda x:(x[0],x[1],x[2],x[3]),reverse=True); top=ranked[:5]
    if not top:continue
    margin=top[0][0]-(top[1][0] if len(top)>1 else 0)
    old_id=r.get('cand1_id',''); changed=old_id and top[0][4]['id']!=old_id
    if top[0][0]>=.94 and margin>=.03: cls='GLOBAL_STRONG'
    elif top[0][0]>=.84 and margin>=.04: cls='GLOBAL_GOOD'
    elif changed and top[0][0]>=.78 and margin>=.025: cls='GLOBAL_ALTERNATIVE'
    else: cls='GLOBAL_WEAK'
    counts[cls]+=1
    x={'shobi_code':r.get('shobi_code',''),'shobi_name':r.get('shobi_name',''),'old_classification':r.get('classification',''),'old_brand_hint':r.get('inferred_brand',''),'old_brand_source':r.get('brand_source',''),'old_cand1_id':old_id,'fallback_classification':cls,'fallback_margin':f'{margin:.4f}'}
    for i,(sc,rc,pr,sr,c) in enumerate(top,1):
        x.update({f'cand{i}_id':c['id'],f'cand{i}_brand':c['brand'],f'cand{i}_name':c['name'],f'cand{i}_score':f'{sc:.4f}',f'cand{i}_url':c['url']})
    out.append(x)

fields=['shobi_code','shobi_name','old_classification','old_brand_hint','old_brand_source','old_cand1_id','fallback_classification','fallback_margin']
for i in range(1,6): fields += [f'cand{i}_id',f'cand{i}_brand',f'cand{i}_name',f'cand{i}_score',f'cand{i}_url']
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
lines=['# Global local-corpus fallback review','',f'- Input residual candidates inspected: **{len(out)}**']
for k in ['GLOBAL_STRONG','GLOBAL_GOOD','GLOBAL_ALTERNATIVE','GLOBAL_WEAK']:lines.append(f'- {k}: **{counts[k]}**')
lines += ['','This pass ignores inferred brand restrictions and searches only the repository-local `perfume_urls.txt`. It is review-only and promotes nothing.','','## Strong / good / changed alternatives','']
for r in out:
    if r['fallback_classification']!='GLOBAL_WEAK': lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} -> {r.get('cand1_brand','')} / {r.get('cand1_name','')} — ID {r.get('cand1_id','')} — **{r['fallback_classification']}** — old hint `{r['old_brand_hint']}` ({r['old_brand_source']})")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('reviewed',len(out),dict(counts))
