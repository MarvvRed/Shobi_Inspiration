#!/usr/bin/env python3
import csv,re
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]; MATCH=ROOT/'fragrantica-v2-local-url-match.csv'; SOURCES=['source-recovery.csv','online-resolution-v8.csv','resolution-audit-batch69.csv','resolution-audit-batch72.csv','fragrantica-v2-local-id-reconciliation.csv']
def first(d,*ks):
 for k in ks:
  if d.get(k) not in (None,''): return str(d[k])
 return ''
def rows(p):
 if not p.exists(): return []
 try:
  with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
 except:return []
res=rows(MATCH); codes={first(r,'shobi_code','code') for r in res}; ev=defaultdict(lambda:defaultdict(list)); files=[MATCH]+[ROOT/x for x in SOURCES]
for p in files:
 for r in rows(p):
  c=first(r,'shobi_code','code','sku','product_code').strip()
  if c not in codes: continue
  for k,v in r.items():
   if not v: continue
   if 'id' in k.lower() and re.fullmatch(r'\d{2,7}',str(v).strip()):ev[c][str(v).strip()].append(f'{p.name}:{k}')
   for m in re.findall(r'-(\d{2,7})\.html',str(v)):ev[c][m].append(f'{p.name}:{k}:url')
out=[]
for r in res:
 c=first(r,'shobi_code','code'); n=first(r,'shobi_name','name'); b=first(r,'brand_hint','shobi_brand','brand')
 for fid,orig in ev[c].items():
  src=sorted(set(x.split(':')[0] for x in orig));out.append({'shobi_code':c,'shobi_name':n,'brand_hint':b,'candidate_id':fid,'independent_sources':len(src),'evidence_score':len(src)*3,'sources':' | '.join(src),'origins':' | '.join(sorted(set(orig)))})
out.sort(key=lambda x:(-x['evidence_score'],x['shobi_code'],x['candidate_id'])); fields=['shobi_code','shobi_name','brand_hint','candidate_id','independent_sources','evidence_score','sources','origins']
with (ROOT/'fragrantica-v2-mega-local-evidence.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
strong=[x for x in out if x['independent_sources']>=2]; lines=['# Mega local residual evidence','',f'- Residual rows: **{len(codes)}**',f'- Local evidence files scanned: **{len(files)}**',f'- Candidate ID records: **{len(out)}**',f'- Candidates supported by >=2 independent local files: **{len(strong)}**','','## Multi-source candidates','']+[f"- `{x['shobi_code']}` — {x['shobi_name']} -> ID {x['candidate_id']} — sources {x['independent_sources']} — {x['sources']}" for x in strong]
(ROOT/'fragrantica-v2-mega-local-evidence.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print('residuals',len(codes),'candidate_records',len(out),'multi_source',len(strong))
