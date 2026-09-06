import csv,re,unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict,Counter

URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
MATCH=Path('fragrantica-v2-local-url-match.csv')
OUT=Path('fragrantica-v2-brand-override-review.csv')
REPORT=Path('fragrantica-v2-brand-override-review.md')
STOP={'eau','de','parfum','perfume','toilette','edp','edt','for','men','women','man','woman','pour','homme','femme','the','by','and','limited','edition','cologne'}
OVERRIDES={
 'ESC':'Escada',
 'LAC':'Lacoste',
 'ROC':'Rochas',
 'ZEG':'Ermenegildo Zegna',
 'WID':'Widian',
 'RIT':'Rituals',
 'JES':'Jesus Del Pozo',
 'ANFAD':'Anfasic Dokhoon',
}

def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())
def toks(s): return [x for x in norm(s).split() if x not in STOP and len(x)>1]
def sim(a,b): return SequenceMatcher(None,norm(a),norm(b)).ratio()
def parse(u):
 m=re.search(r'/perfume/([^/]+)/([^/]+?)-(\d+)\.html',u.strip(),re.I)
 if not m:return None
 b,n,i=m.groups();return {'url':u.strip(),'id':i,'brand':b.replace('-',' '),'name':n.replace('-',' ')}
def metrics(q,c):
 qn=norm(q);cn=norm(c['name']);qt=set(toks(q));ct=set(toks(c['name']))
 if not qn or not cn:return 0,0,0,0
 inter=len(qt&ct);rc=inter/len(qt) if qt else 0;pr=inter/len(ct) if ct else 0
 f1=2*rc*pr/(rc+pr) if rc+pr else 0;sr=sim(qn,cn)
 short,longer=(qn,cn) if len(qn)<=len(cn) else (cn,qn);ratio=len(short)/len(longer) if longer else 0
 contain=.96 if min(len(qn),len(cn))>=4 and ratio>=.68 and short in longer else 0
 return max(sr,f1,contain,1.0 if qn==cn else 0),rc,pr,sr

def suffix(code):
 s=str(code or '').strip()
 return s.rsplit('-',1)[-1].upper().strip() if '-' in s else ''

urls=[];brands=defaultdict(list)
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
 c=parse(line)
 if not c:continue
 idx=len(urls);urls.append(c);brands[norm(c['brand'])].append(idx)

with MATCH.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
out=[];cnt=Counter()
for r in rows:
 suf=suffix(r.get('shobi_code'))
 if suf not in OVERRIDES:continue
 wanted=norm(OVERRIDES[suf]); pool=[];matched_brands=[]
 for bn,idxs in brands.items():
  if wanted==bn or wanted in bn or bn in wanted:
   pool.extend(idxs);matched_brands.append(bn)
 q=r.get('match_name') or r.get('shobi_name') or ''
 ranked=[]
 for idx in pool:
  c=urls[idx];sc,rc,pr,sr=metrics(q,c)
  if sc>=.50:ranked.append((sc,rc,pr,sr,c))
 ranked.sort(key=lambda x:(x[0],x[1],x[2],x[3]),reverse=True);top=ranked[:5]
 if not top:cls='OVERRIDE_NO_CANDIDATE'
 else:
  margin=top[0][0]-(top[1][0] if len(top)>1 else 0)
  if top[0][0]>=.96 and margin>=.02:cls='OVERRIDE_STRONG'
  elif top[0][0]>=.86 and margin>=.03:cls='OVERRIDE_GOOD'
  elif top[0][0]>=.74:cls='OVERRIDE_REVIEW'
  else:cls='OVERRIDE_WEAK'
 cnt[cls]+=1
 x={'shobi_code':r.get('shobi_code',''),'shobi_name':r.get('shobi_name',''),'suffix':suf,'override_brand':OVERRIDES[suf],'old_brand_hint':r.get('inferred_brand',''),'old_classification':r.get('classification',''),'override_classification':cls,'matched_corpus_brands':';'.join(sorted(set(matched_brands)))}
 for i,(sc,rc,pr,sr,c) in enumerate(top,1):x.update({f'cand{i}_id':c['id'],f'cand{i}_brand':c['brand'],f'cand{i}_name':c['name'],f'cand{i}_score':f'{sc:.4f}',f'cand{i}_url':c['url']})
 out.append(x)
fields=['shobi_code','shobi_name','suffix','override_brand','old_brand_hint','old_classification','override_classification','matched_corpus_brands']
for i in range(1,6):fields += [f'cand{i}_id',f'cand{i}_brand',f'cand{i}_name',f'cand{i}_score',f'cand{i}_url']
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
lines=['# Corrected local brand-override review','',f'- Rows inspected: **{len(out)}**']
for k in ['OVERRIDE_STRONG','OVERRIDE_GOOD','OVERRIDE_REVIEW','OVERRIDE_WEAK','OVERRIDE_NO_CANDIDATE']:lines.append(f'- {k}: **{cnt[k]}**')
lines += ['','Only repository-local `perfume_urls.txt` is searched. Overrides correct known false suffix/signature brand inference; this step promotes nothing.','','## Strong / good','']
for r in out:
 if r['override_classification'] in {'OVERRIDE_STRONG','OVERRIDE_GOOD'}:lines.append(f"- `{r['shobi_code']}` — {r['shobi_name']} -> {r.get('cand1_brand','')} / {r.get('cand1_name','')} — ID {r.get('cand1_id','')} — **{r['override_classification']}** (old hint `{r['old_brand_hint']}`)")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('rows',len(out),dict(cnt))
# Triggered as an explicit local-only corrected-brand review stage.
