#!/usr/bin/env python3
import csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'fragrantica-v2-local-id-reconciliation.csv';MATCH=ROOT/'fragrantica-v2-local-url-match.csv';OUT=ROOT/'fragrantica-v2-remaining-historical-residuals.md'
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
res={r['shobi_code'].strip():r for r in rows(MATCH)}
out=[]
for r in rows(REC):
 c=(r.get('shobi_code') or '').strip()
 if c not in res:continue
 hid=(r.get('historical_id') or '').strip()
 if not hid or r.get('historical_in_local')!='yes':continue
 m=res[c]
 out.append({
  'code':c,'name':r.get('shobi_name',''),'class':r.get('classification',''),'hid':hid,'hbrand':r.get('historical_local_brand',''),'hname':r.get('historical_local_name',''),'hscore':r.get('historical_score',''),'hcov':r.get('historical_coverage',''),
  'topid':r.get('top_local_id',''),'topbrand':r.get('top_local_brand',''),'topname':r.get('top_local_name',''),'topscore':r.get('top_score',''),'topcov':r.get('top_coverage',''),'inferred':m.get('inferred_brand',''),'matchclass':m.get('classification','')})
out.sort(key=lambda x:(x['class'],x['code']))
lines=['# Remaining historical residual review','',f'- Residual rows with historical ID still present in local corpus: **{len(out)}**','','## Candidates','']
for x in out:
 lines.append(f"- `{x['code']}` [{x['matchclass']} / {x['class']}] — {x['name']} — inferred `{x['inferred']}` — HIST {x['hbrand']} / {x['hname']} — ID {x['hid']} — score {x['hscore']} cov {x['hcov']} — TOP {x['topbrand']} / {x['topname']} — ID {x['topid']} — score {x['topscore']} cov {x['topcov']}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('historical_residuals',len(out))
