import json,re
from pathlib import Path
DB=Path('database_complete.json'); OUT=Path('catalog-residual-reconciliation.md')
data=json.loads(DB.read_text(encoding='utf-8'))
rows=[]
for g in data:
 b=(g.get('brandInfo') or {}).get('name','')
 for p in g.get('perfumes',[]): rows.append((b,p))
bycode={str(p.get('code') or '').strip().upper():(b,p) for b,p in rows if str(p.get('code') or '').strip()}
empty=[(b,p) for b,p in rows if not str(p.get('code') or '').strip()]
def urlcode(u):
 m=re.search(r'/([0-9]+-[a-z0-9 ]+)(?:-[a-z]+)?(?:$|[/?#])',str(u or '').lower())
 return m.group(1).upper() if m else ''
lines=['# Residual catalog reconciliation','',f'- Empty-code rows: **{len(empty)}**','']
for b,p in empty:
 uc=urlcode(p.get('shobiUrl')); existing=bycode.get(uc) if uc else None
 lines.append(f"- {b} — {p.get('inspiredBy','')} | pid={p.get('prestashopProductId') or '-'} | url_code=`{uc or '-'}` | existing_code_row={'YES' if existing else 'NO'}" + (f" ({existing[0]} — {existing[1].get('inspiredBy','')})" if existing else ''))
lines+=['','## Non-empty code vs URL conflicts','']
conf=[]
for b,p in rows:
 c=str(p.get('code') or '').strip().upper(); uc=urlcode(p.get('shobiUrl'))
 if c and uc and c!=uc:
  conf.append((b,p,c,uc)); lines.append(f"- {b} — {p.get('inspiredBy','')} | code=`{c}` | url_code=`{uc}` | {p.get('shobiUrl','')}")
lines+=['',f'- Conflict count: **{len(conf)}**']
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('empty',len(empty),'conflicts',len(conf))