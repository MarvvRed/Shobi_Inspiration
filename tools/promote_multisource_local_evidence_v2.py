#!/usr/bin/env python3
import csv,json,re,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MATCH=ROOT/'fragrantica-v2-local-url-match.csv'; MEGA=ROOT/'fragrantica-v2-mega-local-evidence.csv'
DBS=[ROOT/'database_v2_clean.json',ROOT/'database_complete.json']; OUT=ROOT/'fragrantica-v2-multisource-promotion.md'
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def norm(s):return ' '.join(re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()))
def code_of(x):return str(x.get('code') or x.get('id') or '').strip()
def verified(x):return str(x.get('fragranticaStatus') or '').startswith('VERIFIED_')
def shape(p):
 d=json.loads(p.read_text(encoding='utf-8-sig'))
 if isinstance(d,list):return d,lambda xs:xs
 for k in ('perfumes','items','products','data'):
  if isinstance(d.get(k),list):return d[k],lambda xs,dd=d,kk=k:{**dd,kk:xs}
 raise RuntimeError('unsupported')
match={r['shobi_code'].strip():r for r in rows(MATCH)}; mega=rows(MEGA); selected={}; blocked=[]
for e in mega:
 c=e.get('shobi_code','').strip()
 if c not in match:continue
 try:src=int(e.get('independent_sources') or 0)
 except:src=0
 if src<3:continue
 m=match[c]; fid=e.get('candidate_id','').strip(); brand_hint=norm(e.get('brand_hint') or m.get('inferred_brand') or m.get('shobi_brand'))
 found=None
 for i in range(1,6):
  if (m.get(f'cand{i}_id') or '').strip()==fid:
   found=i;break
 if not found:continue
 cb=norm(m.get(f'cand{found}_brand')); cn=norm(m.get(f'cand{found}_name'))
 try:ns=float(m.get(f'cand{found}_name_score') or 0);bs=float(m.get(f'cand{found}_brand_score') or 0);rc=float(m.get(f'cand{found}_recall') or 0);pr=float(m.get(f'cand{found}_precision') or 0)
 except:continue
 brand_ok=bool(brand_hint and (brand_hint==cb or brand_hint in cb or cb in brand_hint))
 # Strict multi-source rule: 3+ source agreement, learned/explicit brand agrees, and name identity is strong.
 safe=brand_ok and ns>=0.78 and rc>=0.66 and pr>=0.50
 # Exact-name records can pass with slightly lower token recall if sequence/name score is essentially exact.
 if brand_ok and ns>=0.94:safe=True
 # Avoid generic one-token names unless essentially exact and brand score is perfect.
 qtokens=norm(m.get('match_name') or m.get('shobi_name')).split()
 if len(qtokens)<=1 and not (ns>=0.97 and bs>=0.90):safe=False
 if safe:
  url=m.get(f'cand{found}_url','').strip(); selected[c]={'id':fid,'url':url,'brand':m.get(f'cand{found}_brand',''),'name':m.get(f'cand{found}_name',''),'sources':src,'name_score':ns,'brand_score':bs,'rank':found}
 else:blocked.append((c,fid,src,brand_ok,ns,rc,pr))
changed={}
for p in DBS:
 items,wrap=shape(p);n=0
 for x in items:
  c=code_of(x)
  if c not in selected or verified(x):continue
  s=selected[c];x['fragranticaId']=s['id'];x['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2';x['fragranticaLocalUrl']=s['url'];x['fragranticaVerificationSource']='3+ local evidence sources with brand/name agreement';n+=1
 p.write_text(json.dumps(wrap(items),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');changed[p.name]=n
lines=['# Multi-source local residual promotion','',f'- Residual queue: **{len(match)}**',f'- Safe multi-source mappings: **{len(selected)}**',f'- Blocked multi-source candidates: **{len(blocked)}**']+[f'- {k}: **{v}** promoted' for k,v in changed.items()]+['','## Promoted mappings','']
for c,s in sorted(selected.items()):lines.append(f"- `{c}` -> {s['brand']} / {s['name']} — ID {s['id']} — sources {s['sources']} — matcher rank {s['rank']} — name {s['name_score']:.4f} — brand {s['brand_score']:.4f}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('residual',len(match),'safe',len(selected),'blocked',len(blocked),'changed',changed)
