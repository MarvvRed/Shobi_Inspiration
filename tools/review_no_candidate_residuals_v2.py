#!/usr/bin/env python3
import csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MATCH=ROOT/'fragrantica-v2-local-url-match.csv'; OUT=ROOT/'fragrantica-v2-no-candidate-review.md'
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
rr=[r for r in rows(MATCH) if r.get('classification')=='NO_CANDIDATE']
with_brand=[r for r in rr if r.get('inferred_brand') or r.get('shobi_brand')]
lines=['# NO_CANDIDATE residual review','',f'- Total NO_CANDIDATE: **{len(rr)}**',f'- With local brand hint: **{len(with_brand)}**',f'- Without brand hint: **{len(rr)-len(with_brand)}**','','## Brand-hinted residuals','']
for r in with_brand:
 cs=[]
 for i in range(1,6):
  if r.get(f'cand{i}_id'):
   cs.append(f"#{i} {r.get(f'cand{i}_brand','')} / {r.get(f'cand{i}_name','')} [ID {r.get(f'cand{i}_id','')}; score {r.get(f'cand{i}_score','')}; name {r.get(f'cand{i}_name_score','')}]")
 lines.append(f"- `{r.get('shobi_code','')}` — {r.get('shobi_name','')} — brand `{r.get('inferred_brand') or r.get('shobi_brand')}` ({r.get('brand_source','')}) — " + (' | '.join(cs) if cs else 'no local candidates'))
lines += ['','## No brand hint','']
for r in rr:
 if r.get('inferred_brand') or r.get('shobi_brand'):continue
 cs=[]
 for i in range(1,4):
  if r.get(f'cand{i}_id'):cs.append(f"#{i} {r.get(f'cand{i}_brand','')} / {r.get(f'cand{i}_name','')} [ID {r.get(f'cand{i}_id','')}; score {r.get(f'cand{i}_score','')}]")
 lines.append(f"- `{r.get('shobi_code','')}` — {r.get('shobi_name','')} — " + (' | '.join(cs) if cs else 'no local candidates'))
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('no_candidate',len(rr),'brand_hinted',len(with_brand))
