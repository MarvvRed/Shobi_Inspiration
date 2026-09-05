from __future__ import annotations

import csv, json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'fragrantica-scraper-archive/corpus-match'
REPORT=OUT/'shobi-fragrantica-corpus-match.csv'
AMBIG=OUT/'ambiguous.csv'
UNMATCH=OUT/'unmatched.csv'
SUMMARY_JSON=OUT/'summary.json'
SUMMARY=OUT/'summary.md'

def read(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rows,fields):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

# Merge the historical curated file plus every explicit curated batch.
# Later files win for the same Shobi code, which lets us correct a prior mapping safely.
web={}
web_files=[]
for p in sorted(OUT.glob('web-confirmed*.csv')):
    web_files.append(p.name)
    for r in read(p):
        code=(r.get('shobi_code') or '').strip()
        if code:web[code]=r

rows=read(REPORT); fields=list(rows[0].keys()) if rows else []
merged=0; previous=Counter()
for row in rows:
    code=(row.get('shobi_code') or '').strip(); m=web.get(code)
    if not m:continue
    if row.get('status')!='FOUND':
        previous[row.get('status') or 'EMPTY']+=1;merged+=1
    row['status']='FOUND';row['match_type']='WEB_VERIFIED_FRAGRANTICA';row['score']='1.0000';row['candidate_count']='1'
    row['fragrantica_brand']=m.get('fragrantica_brand','');row['fragrantica_perfume']=m.get('fragrantica_perfume','')
    row['fragrantica_id']=m.get('fragrantica_id','');row['fragrantica_url']=m.get('fragrantica_url','')
    row['note']=m.get('verification_note','')

write(REPORT,rows,fields);write(AMBIG,[r for r in rows if r.get('status')=='AMBIGUOUS'],fields);write(UNMATCH,[r for r in rows if r.get('status') in {'NOT_FOUND','MAPPED_NOT_IN_CORPUS'}],fields)
summary=json.loads(SUMMARY_JSON.read_text(encoding='utf-8'));sc=Counter(r.get('status') or '' for r in rows);tc=Counter(r.get('match_type') or 'NONE' for r in rows)
summary['web_confirmed_files']=web_files;summary['web_confirmed_rows']=len(web);summary['web_confirmed_newly_merged']=merged;summary['web_confirmed_previous_statuses']=dict(previous)
summary['status_counts']=dict(sc);summary['match_type_counts']=dict(tc);summary['found_total']=sc.get('FOUND',0);summary['ambiguous_total']=sc.get('AMBIGUOUS',0);summary['not_found_total']=sc.get('NOT_FOUND',0);summary['mapped_not_in_corpus_total']=sc.get('MAPPED_NOT_IN_CORPUS',0)
SUMMARY_JSON.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
SUMMARY.write_text(f"# Shobi ↔ Fragrantica resolution\n\nFOUND: **{summary['found_total']}**\n\nAMBIGUOUS: **{summary['ambiguous_total']}**\n\nNOT_FOUND: **{summary['not_found_total']}**\n\nMAPPED_NOT_IN_CORPUS: **{summary['mapped_not_in_corpus_total']}**\n\nWeb verified: **{len(web)}**\n",encoding='utf-8')
print(json.dumps({'web_files':web_files,'web_rows':len(web),'newly_merged':merged,'found_total':summary['found_total'],'ambiguous':summary['ambiguous_total'],'not_found':summary['not_found_total'],'mapped_not_in_corpus':summary['mapped_not_in_corpus_total']},indent=2))
