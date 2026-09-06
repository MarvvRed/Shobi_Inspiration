#!/usr/bin/env python3
import csv,re,unicodedata
from difflib import SequenceMatcher
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MATCH=ROOT/'fragrantica-v2-local-url-match.csv'; OUTCSV=ROOT/'fragrantica-v2-brand-abbreviation-review.csv'; OUTMD=ROOT/'fragrantica-v2-brand-abbreviation-review.md'
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def norm(s):return ' '.join(re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()))
def compact(s):return norm(s).replace(' ','')
def strip_brand(name,brand):
 n=norm(name);b=norm(brand)
 if not b:return n
 bt=set(b.split());return ' '.join(x for x in n.split() if x not in bt)
def score(q,c):
 nq=norm(q);nc=norm(c);cq=compact(q);cc=compact(c)
 seq=SequenceMatcher(None,cq,cc).ratio() if cq and cc else 0
 containment=1.0 if cq and (cq in cc or cc in cq) else 0
 qt=nq.split();ct=nc.split();abbr=0
 if qt and ct:
  hit=0
  for a in qt:
   if any(b.startswith(a) or a.startswith(b) for b in ct):hit+=1
  abbr=hit/len(qt)
 return max(seq,0.88*containment+0.12*seq,0.70*abbr+0.30*seq),seq,containment,abbr
out=[]
for r in rows(MATCH):
 cls=r.get('classification') or ''
 if cls not in ('WEAK_REVIEW','NO_CANDIDATE'):continue
 brand=r.get('inferred_brand') or r.get('shobi_brand') or ''
 if not brand:continue
 q=r.get('match_name') or r.get('shobi_name') or ''
 cands=[]
 for i in range(1,6):
  cb=r.get(f'cand{i}_brand') or '';cn=r.get(f'cand{i}_name') or ''
  if not cb or not cn:continue
  nb=norm(brand);ncb=norm(cb)
  if not (nb==ncb or nb in ncb or ncb in nb):continue
  s,seq,cont,abbr=score(strip_brand(q,brand),strip_brand(cn,cb))
  cands.append((s,seq,cont,abbr,i,r.get(f'cand{i}_id') or '',cb,cn,r.get(f'cand{i}_url') or ''))
 if not cands:continue
 cands.sort(reverse=True)
 best=cands[0];second=cands[1][0] if len(cands)>1 else 0;margin=best[0]-second
 if best[0]>=0.58:
  out.append({'classification':cls,'shobi_code':r.get('shobi_code',''),'shobi_name':r.get('shobi_name',''),'brand':brand,'candidate_id':best[5],'candidate_brand':best[6],'candidate_name':best[7],'rank':best[4],'abbr_score':f'{best[0]:.4f}','seq':f'{best[1]:.4f}','containment':f'{best[2]:.4f}','prefix_coverage':f'{best[3]:.4f}','margin':f'{margin:.4f}','url':best[8]})
out.sort(key=lambda x:(-float(x['abbr_score']),-float(x['margin']),x['shobi_code']))
fields=['classification','shobi_code','shobi_name','brand','candidate_id','candidate_brand','candidate_name','rank','abbr_score','seq','containment','prefix_coverage','margin','url']
with OUTCSV.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
counts={k:sum(1 for x in out if x['classification']==k) for k in ('WEAK_REVIEW','NO_CANDIDATE')}
lines=['# Brand-locked abbreviation review','',f'- Surfaced candidates: **{len(out)}**',f"- WEAK_REVIEW: **{counts['WEAK_REVIEW']}**",f"- NO_CANDIDATE: **{counts['NO_CANDIDATE']}**",'','## Top candidates','']
for x in out[:100]:lines.append(f"- `{x['shobi_code']}` [{x['classification']}] — {x['shobi_name']} -> {x['candidate_brand']} / {x['candidate_name']} — ID {x['candidate_id']} — rank {x['rank']} — score {x['abbr_score']} — margin {x['margin']}")
OUTMD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('surfaced',len(out),counts)
