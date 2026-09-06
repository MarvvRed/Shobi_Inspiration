#!/usr/bin/env python3
import csv,json,re,unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
URLS=ROOT/'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
DB=ROOT/'database_v2_clean.json'; MATCH=ROOT/'fragrantica-v2-local-url-match.csv'
OUT=ROOT/'fragrantica-v2-simple-brand-first.csv'; REPORT=ROOT/'fragrantica-v2-simple-brand-first.md'
STOP={'eau','de','parfum','perfume','toilette','edp','edt','for','men','women','man','woman','pour','homme','femme','the','by','and','limited','edition','cologne','spray','natural'}

def norm(s): return ' '.join(re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()).split())
def tok(s): return [x for x in norm(s).split() if x not in STOP and len(x)>1]
def compact(s): return ''.join(tok(s))
def sim(a,b): return SequenceMatcher(None,compact(a),compact(b)).ratio() if compact(a) and compact(b) else 0
def parse(u):
 m=re.search(r'/perfume/([^/]+)/([^/]+?)-(\d+)\.html',u.strip(),re.I)
 if not m:return None
 b,n,i=m.groups();return {'brand':b.replace('-',' '),'name':n.replace('-',' '),'id':i,'url':u.strip()}
def verified(x): return str(x.get('fragranticaStatus') or x.get('fragrantica_status') or '').startswith('VERIFIED_')
def suffix(c): return norm(str(c or '').rsplit('-',1)[-1]).replace(' ','') if '-' in str(c or '') else ''
def walk(o):
 if isinstance(o,list):
  for x in o: yield from walk(x)
 elif isinstance(o,dict):
  if isinstance(o.get('perfumes'),list):
   for x in o['perfumes']: yield x
  elif 'code' in o or 'inspiredBy' in o: yield o
urls=[];bybrand=defaultdict(list);byid={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
 c=parse(line)
 if c and c['id'] not in byid: byid[c['id']]=c;urls.append(c);bybrand[norm(c['brand'])].append(c)
items=list(walk(json.loads(DB.read_text(encoding='utf-8-sig'))))
# Learn suffix->brand only from verified rows, requiring two examples.
pri=defaultdict(Counter)
for x in items:
 if verified(x):
  fid=str(x.get('fragranticaId') or x.get('fragrantica_id') or '').strip(); c=byid.get(fid); s=suffix(x.get('code'))
  if c and s: pri[s][norm(c['brand'])]+=1
brands={}
for s,c in pri.items():
 b,n=c.most_common(1)[0]
 if n>=2 and n/sum(c.values())>=.6: brands[s]=b
# Reuse current matcher's explicit/tail/prior hint when present, but search the entire brand catalog ourselves.
with MATCH.open(encoding='utf-8-sig',newline='') as f: old={r['shobi_code']:r for r in csv.DictReader(f)}
rows=[]
for x in items:
 if verified(x):continue
 code=str(x.get('code') or '').strip() or '[no-code]'; name=str(x.get('inspiredBy') or x.get('perfume') or '').strip(); o=old.get(code,{})
 hint=norm(x.get('brand') or o.get('inferred_brand') or brands.get(suffix(code),'')).strip(); pool=bybrand.get(hint,[]) if hint else urls
 ranked=[]
 for c in pool:
  s=sim(name,c['name']); qt=set(tok(name));ct=set(tok(c['name'])); inter=len(qt&ct); recall=inter/len(qt) if qt else 0; precision=inter/len(ct) if ct else 0
  # Simple score: spelling similarity plus token identity. No historical/multi-source machinery.
  score=.62*s+.23*recall+.15*precision
  ranked.append((score,s,recall,precision,c))
 ranked.sort(key=lambda z:(z[0],z[1],z[2],z[3]),reverse=True); top=ranked[:10]; margin=top[0][0]-top[1][0] if len(top)>1 else (top[0][0] if top else 0)
 cls='NO_MATCH'
 if top:
  best=top[0]
  if hint and best[0]>=.90 and margin>=.035: cls='AUTO_STRONG'
  elif hint and best[0]>=.80 and margin>=.025: cls='STRONG_REVIEW'
  elif best[0]>=.68: cls='REVIEW'
  else: cls='WEAK'
 r={'shobi_code':code,'shobi_name':name,'brand_hint':hint,'brand_catalog_size':len(pool),'classification':cls,'margin':f'{margin:.4f}'}
 for i,z in enumerate(top,1):
  sc,ss,rc,pr,c=z;r.update({f'cand{i}_id':c['id'],f'cand{i}_brand':c['brand'],f'cand{i}_name':c['name'],f'cand{i}_score':f'{sc:.4f}',f'cand{i}_spell':f'{ss:.4f}',f'cand{i}_recall':f'{rc:.4f}',f'cand{i}_precision':f'{pr:.4f}',f'cand{i}_url':c['url']})
 rows.append(r)
fields=['shobi_code','shobi_name','brand_hint','brand_catalog_size','classification','margin']
for i in range(1,11):fields += [f'cand{i}_id',f'cand{i}_brand',f'cand{i}_name',f'cand{i}_score',f'cand{i}_spell',f'cand{i}_recall',f'cand{i}_precision',f'cand{i}_url']
with OUT.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
cnt=Counter(r['classification'] for r in rows)
lines=['# Simple exhaustive brand-first matcher','',f'- Residuals: **{len(rows)}**',f'- Local URLs: **{len(urls)}**',f'- With brand hint: **{sum(bool(r["brand_hint"]) for r in rows)}**']+[f'- {k}: **{v}**' for k,v in cnt.items()]+['','## Strong results','']
for r in rows:
 if r['classification'] in {'AUTO_STRONG','STRONG_REVIEW'}:lines.append(f"- `{r['shobi_code']}` {r['shobi_name']} -> {r.get('cand1_brand','')} / {r.get('cand1_name','')} — ID {r.get('cand1_id','')} — {r['classification']} — score {r.get('cand1_score','')} — margin {r['margin']}")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('residuals',len(rows),'brand_hints',sum(bool(r['brand_hint']) for r in rows),dict(cnt))
