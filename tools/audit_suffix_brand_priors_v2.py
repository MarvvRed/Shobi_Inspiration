#!/usr/bin/env python3
import csv,json,re,unicodedata
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DB=ROOT/'database_v2_clean.json';URLS=ROOT/'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt';OUT=ROOT/'fragrantica-v2-suffix-prior-audit.md'
def norm(s):return ' '.join(re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()))
def suffix(c):return norm(str(c or '').rsplit('-',1)[-1]).replace(' ','') if '-' in str(c or '') else ''
def walk(o):
 if isinstance(o,list):
  for x in o:yield from walk(x)
 elif isinstance(o,dict):
  if isinstance(o.get('perfumes'),list):
   for p in o['perfumes']:
    if isinstance(p,dict):yield p
  elif 'code' in o or 'inspiredBy' in o:yield o
byid={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
 m=re.search(r'/perfume/([^/]+)/[^/]+-(\d+)\.html',line,re.I)
 if m:byid[m.group(2)]=m.group(1).replace('-',' ')
perf=list(walk(json.loads(DB.read_text(encoding='utf-8-sig'))));priors=defaultdict(Counter);examples=defaultdict(list)
for p in perf:
 if not str(p.get('fragranticaStatus') or '').startswith('VERIFIED_'):continue
 fid=str(p.get('fragranticaId') or '').strip();s=suffix(p.get('code'));b=byid.get(fid)
 if s and b:priors[s][b]+=1;examples[(s,b)].append((str(p.get('code') or ''),str(p.get('inspiredBy') or p.get('perfume') or ''),fid))
# flag split priors, low dominance, and suspicious cases where suffix is not a prefix/signature of chosen brand
flags=[]
for s,cnt in priors.items():
 total=sum(cnt.values());top,n=cnt.most_common(1)[0];dom=n/total
 compact=norm(top).replace(' ','');susp=not (compact.startswith(s) or (len(s)>=3 and s in compact))
 if len(cnt)>1 or dom<0.85 or susp:flags.append((s,total,top,n,dom,susp,cnt))
flags.sort(key=lambda x:(not x[5],x[4],-x[1]))
lines=['# Suffix brand-prior audit','',f'- Learned suffixes: **{len(priors)}**',f'- Flagged suffixes: **{len(flags)}**','','## Flagged','']
for s,total,top,n,dom,susp,cnt in flags:
 lines.append(f"- `{s}` — top `{top}` {n}/{total} ({dom:.1%}) — suspicious-name={susp} — distribution: {dict(cnt)}")
 for code,name,fid in examples[(s,top)][:4]:lines.append(f"  - `{code}` — {name} — ID {fid}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('priors',len(priors),'flagged',len(flags))
