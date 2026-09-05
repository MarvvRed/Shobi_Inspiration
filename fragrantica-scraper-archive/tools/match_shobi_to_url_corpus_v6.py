from __future__ import annotations

import csv, json, runpy
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V5=HERE/"match_shobi_to_url_corpus_v5.py"
LEGACY=ROOT/"data/shobi-fragrantica-mapping.csv"
OUT=ROOT/"fragrantica-scraper-archive/corpus-match"
REPORT=OUT/"shobi-fragrantica-corpus-match.csv"
AMBIG=OUT/"ambiguous.csv"
UNMATCH=OUT/"unmatched.csv"
SUMMARY_JSON=OUT/"summary.json"
SUMMARY=OUT/"summary.md"

# First exhaust the local 55k URL corpus with the v5 high-precision matcher.
runpy.run_path(str(V5),run_name="__main__")


def read_csv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def write_csv(p,rows,fields):
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)

legacy_rows=read_csv(LEGACY) if LEGACY.exists() else []
verified={}
for r in legacy_rows:
    code=(r.get("shobi_code") or "").strip()
    identity=(r.get("identity_status") or "").strip().upper()
    fstatus=(r.get("fragrantica_status") or "").strip().upper()
    fid=(r.get("fragrantica_id") or "").strip()
    if code and identity=="CONFIRMED" and fstatus=="FOUND" and fid:
        verified[code]=r

rows=read_csv(REPORT)
fields=list(rows[0].keys()) if rows else []
rescued=0
rescued_from_not_found=Counter()
for row in rows:
    if row.get("status")=="FOUND":
        continue
    code=(row.get("shobi_code") or "").strip()
    m=verified.get(code)
    if not m:
        continue
    old=row.get("status") or ""
    row["status"]="FOUND"
    row["match_type"]="CONFIRMED_EXISTING_MAPPING"
    row["score"]="1.0000"
    row["candidate_count"]="1"
    row["fragrantica_brand"]=(m.get("original_brand") or "").strip()
    row["fragrantica_perfume"]=(m.get("original_perfume") or m.get("inspired_by") or "").strip()
    row["fragrantica_id"]=(m.get("fragrantica_id") or "").strip()
    row["fragrantica_url"]=(m.get("fragrantica_url") or "").strip()
    row["note"]="Existing CONFIRMED+FOUND mapping from data/shobi-fragrantica-mapping.csv"
    rescued+=1
    rescued_from_not_found[old]+=1

write_csv(REPORT,rows,fields)
write_csv(AMBIG,[r for r in rows if r.get("status")=="AMBIGUOUS"],fields)
write_csv(UNMATCH,[r for r in rows if r.get("status") in {"NOT_FOUND","MAPPED_NOT_IN_CORPUS"}],fields)

summary=json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
status_counts=Counter(r.get("status") or "" for r in rows)
type_counts=Counter(r.get("match_type") or "NONE" for r in rows)
summary["legacy_mapping_rows"]=len(legacy_rows)
summary["legacy_verified_found_rows"]=len(verified)
summary["rescued_by_existing_verified_mapping"]=rescued
summary["rescued_previous_statuses"]=dict(rescued_from_not_found)
summary["status_counts"]=dict(status_counts)
summary["match_type_counts"]=dict(type_counts)
summary["found_total"]=status_counts.get("FOUND",0)
summary["ambiguous_total"]=status_counts.get("AMBIGUOUS",0)
summary["not_found_total"]=status_counts.get("NOT_FOUND",0)
summary["mapped_not_in_corpus_total"]=status_counts.get("MAPPED_NOT_IN_CORPUS",0)
SUMMARY_JSON.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
SUMMARY.write_text(
    "# Shobi ↔ Fragrantica resolution\n\n"
    f"FOUND: **{summary['found_total']}**\n\n"
    f"AMBIGUOUS: **{summary['ambiguous_total']}**\n\n"
    f"NOT_FOUND: **{summary['not_found_total']}**\n\n"
    f"MAPPED_NOT_IN_CORPUS: **{summary['mapped_not_in_corpus_total']}**\n\n"
    f"Recovered from existing verified mapping: **{rescued}**\n",
    encoding="utf-8"
)
print(json.dumps(summary,indent=2,ensure_ascii=False))
