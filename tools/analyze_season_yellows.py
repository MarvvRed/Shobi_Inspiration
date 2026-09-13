#!/usr/bin/env python3
"""Diagnose every yellow row failing season validation. Read-only."""
import csv,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'catalog_site.json').read_text(encoding='utf-8-sig'))
GS=ROOT/'fragrantica-scraper-archive'/'social-cards'/'gender-season.csv'
with GS.open(encoding='utf-8-sig',newline='') as f:
    evidence={str(x.get('shobi_code') or '').strip().upper():x for x in csv.DictReader(f)}
rows=[]; kinds=Counter()
for db,s in zip(DB,SITE):
    if str(s.get('validationStatus') or '').lower()!='yellow':continue
    if (s.get('validationChecks') or {}).get('season',True):continue
    c=str(db.get('code') or '').strip().upper(); fid=str(db.get('fragranticaId') or '').strip(); e=evidence.get(c)
    if not e:k='no_csv_row'
    elif str(e.get('fragrantica_id') or '').strip()!=fid:k='fid_mismatch'
    elif not str(e.get('main_season') or '').strip():k='missing_main_season'
    elif str(e.get('main_season') or '').strip().lower() not in {str(x).lower() for x in (db.get('seasons') or [])}:k='season_value_mismatch'
    elif not (ROOT/str(e.get('local_path') or '')).is_file():k='card_file_missing'
    else:k='other'
    kinds[k]+=1
    rows.append({'code':c,'brand':db.get('brand'),'inspiredBy':db.get('inspiredBy'),'fid':fid,'currentSeasons':db.get('seasons') or [],'kind':k,'csv':e})
out={'count':len(rows),'kinds':dict(kinds),'rows':rows}
(ROOT/'season-yellow-analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Season yellow analysis','',f'- Rows: **{len(rows)}**']+[f'- `{k}`: **{v}**' for k,v in kinds.most_common()]+['','## Rows','']
for r in rows:
    e=r['csv'] or {}; lines.append(f"- `{r['code']}` — {r['brand']} · {r['inspiredBy']} — {r['kind']} — current={r['currentSeasons']} — csv={e.get('main_season','')} — csvFID={e.get('fragrantica_id','')}")
(ROOT/'season-yellow-analysis.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('season_yellows',len(rows),dict(kinds))
