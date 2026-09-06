#!/usr/bin/env python3
import csv, json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'database_complete.json'
EX=ROOT/'fragrantica-scraper-archive/social-cards/gender-season.csv'
CORP=ROOT/'fragrantica-scraper-archive/corpus-match/shobi-fragrantica-corpus-match.csv'
TERM=ROOT/'fragrantica-scraper-archive/corpus-match/resolved-terminal.csv'
PEND=ROOT/'fragrantica-scraper-archive/corpus-match/pending-review.csv'
OUT=ROOT/'fragrantica-scraper-archive/social-cards/catalog-unmatched-classification.csv'
REP=ROOT/'fragrantica-scraper-archive/social-cards/catalog-unmatched-classification.md'
def code(x): return str(x or '').strip().upper()
def readcsv(p):
    if not p.exists(): return []
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
cat=json.loads(CAT.read_text(encoding='utf-8-sig'))
perf=cat['perfumes'] if isinstance(cat,dict) else cat
ex_codes={code(r.get('shobi_code')) for r in readcsv(EX) if code(r.get('shobi_code'))}
corpus={code(r.get('shobi_code')):r for r in readcsv(CORP) if code(r.get('shobi_code'))}
terminal={code(r.get('shobi_code')):r for r in readcsv(TERM) if code(r.get('shobi_code'))}
pending={code(r.get('shobi_code')):r for r in readcsv(PEND) if code(r.get('shobi_code'))}
rows=[]
for p in perf:
    c=code(p.get('code'))
    if not c or c in ex_codes: continue
    cr=corpus.get(c,{})
    status=str(cr.get('status','')).strip()
    fid=str(cr.get('fragrantica_id','')).strip()
    if c in terminal: cls='TERMINAL_NON_MAPPABLE'
    elif c in pending: cls='UNRESOLVED_SOURCE_IDENTITY'
    elif status=='FOUND' and fid: cls='FOUND_ID_NO_SOCIAL_CARD'
    elif cr: cls='CORPUS_NON_FOUND_OR_NO_ID'
    else: cls='CATALOG_ONLY_NOT_IN_2343_CORPUS'
    rows.append({'shobi_code':c,'prestashop_product_id':p.get('id',''),'name':p.get('name',''),'brand':p.get('brand',''),'current_gender':p.get('genderAffinity',''),'current_seasons':'|'.join(p.get('seasons') or []),'classification':cls,'corpus_status':status,'fragrantica_id':fid,'corpus_note':cr.get('note','')})
fields=list(rows[0]) if rows else []
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
cnt=Counter(r['classification'] for r in rows)
lines=['# Catalog Gender + Season unmatched classification','',f'- unmatched catalog rows: **{len(rows)}**',f'- unmatched unique codes: **{len({r["shobi_code"] for r in rows})}**','']
for k,v in sorted(cnt.items()):lines.append(f'- {k}: **{v}**')
lines += ['','## Recoverable priority','', 'Start with `FOUND_ID_NO_SOCIAL_CARD`, then inspect `CATALOG_ONLY_NOT_IN_2343_CORPUS`. Terminal cases must not be force-mapped.','']
REP.write_text('\n'.join(lines),encoding='utf-8')
print('rows',len(rows),'unique',len({r['shobi_code'] for r in rows}),'classes',dict(cnt))
