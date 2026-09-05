from __future__ import annotations

import csv, os, runpy
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CATALOG=ROOT/"perfume-database/catalog/shobi-master-v1.csv"
TMP=Path("/tmp/shobi-master-enhanced.csv")
RECOVERY=ROOT/"fragrantica-scraper-archive/corpus-match/source-recovery.csv"
V4=HERE/"match_shobi_to_url_corpus_v4.py"
CORE=HERE/"match_shobi_core_v5.py"

lib=runpy.run_path(str(V4),run_name="v4lib")
derive=lib["derive"]
clean_candidate=lib["clean_candidate"]

with CATALOG.open("r",encoding="utf-8-sig",newline="") as f:
    reader=csv.DictReader(f); fields=reader.fieldnames or []; rows=list(reader)

recovered=[]
for row in rows:
    old=row.get("inspired_by","") or ""
    new,src=derive(row)
    if new!=clean_candidate(old):
        recovered.append({"prestashop_product_id":row.get("prestashop_product_id",""),"shobi_code":row.get("shobi_code",""),"old_inspired_by":old,"recovered_inspired_by":new,"source":src,"url":row.get("url","")})
    row["inspired_by"]=new

with TMP.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
RECOVERY.parent.mkdir(parents=True,exist_ok=True)
with RECOVERY.open("w",encoding="utf-8-sig",newline="") as f:
    fs=["prestashop_product_id","shobi_code","old_inspired_by","recovered_inspired_by","source","url"]
    w=csv.DictWriter(f,fieldnames=fs);w.writeheader();w.writerows(recovered)

os.environ["SHOBI_MATCH_CATALOG"]=str(TMP)
runpy.run_path(str(CORE),run_name="__main__")
