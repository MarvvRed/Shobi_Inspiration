#!/usr/bin/env python3
import csv,json,re,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REC=ROOT/'fragrantica-v2-local-id-reconciliation.csv';MATCH=ROOT/'fragrantica-v2-local-url-match.csv';DBS=[ROOT/'database_v2_clean.json',ROOT/'database_complete.json'];OUT=ROOT/'fragrantica-v2-historical-local-bulk-promotion.md'
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def norm(s):return ' '.join(re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()))
def toks(s):return set(norm(s).split())
def code_of(x):return str(x.get('code') or x.get('shobi_code') or x.get('sku') or x.get('id') or '').strip()
def verified(x):return any(str(x.get(k) or '').startswith('VERIFIED_') for k in ('fragranticaStatus','fragrantica_status','verification_status','status'))
def items_shape(p):
 d=json.loads(p.read_text(encoding='utf-8-sig'))
 if isinstance(d,list):return d,lambda xs:xs
 for k in ('perfumes','items','products','data'):
  if isinstance(d.get(k),list):return d[k],lambda xs,dd=d,kk=k:{**dd,kk:xs}
 raise RuntimeError('unsupported DB shape')
match={r['shobi_code'].strip():r for r in rows(MATCH)};residual=set(match);selected={};rejected=[]
for r in rows(REC):
 c=r.get('shobi_code','').strip()
 if c not in residual or r.get('classification') not in ('HIST_ID_CONFIRMED_LOCAL','HIST_ID_PRESENT_NEEDS_REVIEW'):continue
 hid=(r.get('historical_id') or '').strip()
 if not hid or r.get('historical_in_local')!='yes':continue
 try:score=float(r.get('historical_score') or 0);cov=float(r.get('historical_coverage') or 0)
 except:continue
 m=match[c];inferred=norm(m.get('inferred_brand'));hbrand=norm(r.get('historical_local_brand'));hname=norm(r.get('historical_local_name'));q=norm(r.get('shobi_name'));brand_ok=bool(inferred and (inferred==hbrand or inferred in hbrand or hbrand in inferred));qt=toks(q);ct=toks(hname);token_cov=len(qt&ct)/max(1,len(qt));topid=(r.get('top_local_id') or '').strip();topbrand=norm(r.get('top_local_brand'));topscore=float(r.get('top_score') or 0)
 # Tier A: same learned brand + exact/near-exact historical identity. This safely handles cases where generic global ranking picked another brand.
 tier_a=brand_ok and cov>=1.0 and score>=0.66 and token_cov>=0.60
 # Tier B: partial wording still needs stronger score and coverage.
 tier_b=brand_ok and cov>=0.66 and score>=0.72 and token_cov>=0.60
 # Tier C: no learned brand only when identity is exceptionally strong and top candidate agrees.
 tier_c=(not inferred) and cov>=1.0 and score>=0.85 and token_cov>=0.75 and (not topid or topid==hid)
 safe=tier_a or tier_b or tier_c
 # Conflicting candidate from SAME brand can indicate a flanker: require historical to be at least as convincing.
 if safe and topid and topid!=hid and topbrand==hbrand and topscore>score+0.05:safe=False
 if safe:selected[c]={'id':hid,'url':r.get('historical_local_url','').strip(),'brand':r.get('historical_local_brand','').strip(),'name':r.get('historical_local_name','').strip(),'score':score,'coverage':cov,'brand_ok':brand_ok,'tier':'A' if tier_a else ('B' if tier_b else 'C')}
 else:rejected.append(c)
changed={};cleaned={}
for p in DBS:
 items,wrap=items_shape(p);n=0;cl=0
 for x in items:
  if str(x.get('fragranticaStatus') or '').startswith('VERIFIED_'):
   for k in ('fragrantica_id','fragrantica_url','fragrantica_status','fragrantica_verification_source'):
    if k in x:del x[k];cl+=1
  c=code_of(x)
  if c not in selected or verified(x):continue
  s=selected[c];x['fragranticaId']=s['id'];x['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2';x['fragranticaLocalUrl']=s['url'];x['fragranticaVerificationSource']='same-brand historical ID confirmed in local perfume_urls corpus';n+=1
 p.write_text(json.dumps(wrap(items),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');changed[p.name]=n;cleaned[p.name]=cl
lines=['# Same-brand historical/local residual promotion','',f'- Current residual queue: **{len(residual)}**',f'- Safe eligible mappings: **{len(selected)}**']+[f'- {k}: **{v}** promoted; **{cleaned[k]}** redundant snake fields removed' for k,v in changed.items()]+['','## Promoted mappings','']
for c,s in sorted(selected.items()):lines.append(f"- `{c}` -> {s['brand']} / {s['name']} — ID {s['id']} — tier {s['tier']} — score {s['score']:.4f} — coverage {s['coverage']:.4f}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('residual',len(residual),'eligible',len(selected),'changed',changed,'rejected',len(rejected))
