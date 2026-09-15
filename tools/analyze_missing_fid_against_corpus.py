#!/usr/bin/env python3
import json,re,unicodedata
from pathlib import Path
from difflib import SequenceMatcher
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database/catalog/database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'database/catalog/catalog_site.json').read_text(encoding='utf-8-sig'))
CORPUS=ROOT/'database/fragrantica'/'perfume_urls.txt'
OUT=ROOT/'database/audits/missing-fid-corpus-analysis.json'
ID_RE=re.compile(r'-(\d+)\.html(?:[?#].*)?$',re.I)

def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower().replace('&',' and ')
 s=re.sub(r'\b(eau de parfum|eau de toilette|edp|edt|perfume|parfum|fragrance)\b',' ',s)
 return ' '.join(re.findall(r'[a-z0-9]+',s))
def parse(u):
 m=ID_RE.search(u);parts=u.split('/perfume/',1)[-1].split('/')
 if not m or len(parts)<2:return None
 return {'url':u.strip(),'fid':m.group(1),'brand':norm(parts[0].replace('-',' ')),'name':norm(parts[1].rsplit('-',1)[0].replace('-',' '))}
urls=[parse(x) for x in CORPUS.read_text(encoding='utf-8',errors='ignore').splitlines()];urls=[x for x in urls if x]
rows=[]
for db,site in zip(DB,SITE):
 if str(site.get('validationStatus') or '').lower()!='yellow' or (site.get('validationChecks') or {}).get('fid',False):continue
 b=norm(db.get('brand'));n=norm(db.get('inspiredBy'));cand=[]
 for x in urls:
  bs=SequenceMatcher(None,b,x['brand']).ratio() if b else 0;ns=SequenceMatcher(None,n,x['name']).ratio() if n else 0
  if bs>=.86 and ns>=.55:cand.append({**x,'brandScore':round(bs,4),'nameScore':round(ns,4),'exactBrand':b==x['brand'],'exactName':n==x['name']})
 cand=sorted(cand,key=lambda x:(x['exactBrand'] and x['exactName'],x['brandScore']+x['nameScore'],x['nameScore']),reverse=True)[:20]
 exact=[x for x in cand if x['exactBrand'] and x['exactName']]
 strong=[x for x in cand if x['exactBrand'] and x['nameScore']>=.94]
 rows.append({'code':db.get('code'),'brand':db.get('brand'),'inspiredBy':db.get('inspiredBy'),'normalizedBrand':b,'normalizedName':n,'exactCandidates':exact,'strongCandidates':strong,'topCandidates':cand[:8]})
out={'targets':len(rows),'uniqueExact':sum(len(r['exactCandidates'])==1 for r in rows),'uniqueStrongNoExact':sum(not r['exactCandidates'] and len(r['strongCandidates'])==1 for r in rows),'rows':rows}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Missing FID corpus analysis','',f"- Targets: **{out['targets']}**",f"- Unique exact brand+name: **{out['uniqueExact']}**",f"- Unique strong same-brand candidate (no exact): **{out['uniqueStrongNoExact']}**",'','## Rows','']
for r in rows:
 ex=r['exactCandidates'];st=r['strongCandidates'];best=(ex[0] if len(ex)==1 else (st[0] if not ex and len(st)==1 else None))
 lines.append(f"- `{r['code']}` — {r['brand']} · {r['inspiredBy']} — "+(f"candidate FID {best['fid']} {best['url']}" if best else 'no unique deterministic candidate'))
(ROOT/'database/audits/missing-fid-corpus-analysis.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:out[k] for k in ('targets','uniqueExact','uniqueStrongNoExact')},indent=2))
