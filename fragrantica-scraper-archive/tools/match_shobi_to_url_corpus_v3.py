from __future__ import annotations

import csv, json, re, unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "perfume-database/catalog/shobi-master-v1.csv"
CONFIRMED = ROOT / "perfume-database/confirmed/shobi-fragrantica-mapping.csv"
URLS = ROOT / "fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt"
OUT = ROOT / "fragrantica-scraper-archive/corpus-match"
REPORT, AMBIG, UNMATCH = OUT/"shobi-fragrantica-corpus-match.csv", OUT/"ambiguous.csv", OUT/"unmatched.csv"
SUMMARY, SUMMARY_JSON = OUT/"summary.md", OUT/"summary.json"

QUALIFIERS = {"absolu","absolute","absolue","elixir","essence","extreme","extrait","intense","intensely","intensivo","intenso","noir","parfum","perfume","rouge","sport","edp","edt","edc","limited","edition","collector"}
GENERIC_BRAND = {"by","parfum","parfums","perfume","perfumes","fragrance","fragrances","parfumeur","parfumerie","parfumer","createur","prive","prives","the"}
DESCRIPTOR_TAILS = {"type","women","woman","men","man"}


def norm(s: str) -> str:
    s = unquote((s or "").strip()).replace("&"," and ").replace("’", "'").replace("®","")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("'"," ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def suffix(code: str) -> str:
    code=(code or "").strip().upper(); return code.rsplit("-",1)[-1] if "-" in code else ""


def core_brand(s: str) -> str:
    return " ".join(t for t in norm(s).split() if t not in GENERIC_BRAND)


def qtokens(s: str): return frozenset(t for t in norm(s).split() if t in QUALIFIERS)


def read_csv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def parse_url(url):
    m=re.match(r"^https?://(?:www\.)?fragrantica\.com/perfume/([^/]+)/(.+)-(\d+)\.html$",url.strip(),re.I)
    if not m:return None
    bs,ps,fid=m.groups(); b=unquote(bs).replace("-"," ").strip(); p=unquote(ps).replace("-"," ").strip()
    return {"brand":b,"perfume":p,"brand_norm":norm(b),"brand_core":core_brand(b),"perfume_norm":norm(p),"id":fid,"url":url.strip()}


def uniq(rs):
    vals=list({(r["brand_norm"],r["perfume_norm"],r["id"]):r for r in rs}.values())
    return vals[0] if len(vals)==1 else None


def partial_brand_variants(name: str, brand: str):
    n=norm(name); out={n} if n else set()
    if not n or not brand:return sorted(out,key=len)
    nt=n.split(); bf={norm(brand),core_brand(brand)}-{""}; bt=set(core_brand(brand).split())
    for form in bf:
        if n.endswith(" "+form): out.add(n[:-(len(form)+1)].strip())
        if n.startswith(form+" "): out.add(n[len(form)+1:].strip())
    # Shobi often appends only part of a brand: Jo Malone vs Jo Malone London,
    # Crivelli vs Maison Crivelli, Rodriguez vs Narciso Rodriguez, etc.
    maxk=min(6,len(nt)-1)
    for k in range(1,maxk+1):
        tail=nt[-k:]; tail_core=[t for t in tail if t not in GENERIC_BRAND]
        if tail_core and set(tail_core).issubset(bt): out.add(" ".join(nt[:-k]))
        tail_s=" ".join(tail_core); bc=core_brand(brand)
        if tail_s and bc and SequenceMatcher(None,tail_s,bc).ratio()>=0.82: out.add(" ".join(nt[:-k]))
        # typo in a one-word brand suffix, e.g. Amouagee
        if len(tail_core)==1:
            for btoken in bt:
                if len(tail_core[0])>=5 and SequenceMatcher(None,tail_core[0],btoken).ratio()>=0.88:
                    out.add(" ".join(nt[:-k])); break
    # remove harmless catalogue descriptors only as an alternate candidate
    toks=n.split()
    if toks and toks[-1] in DESCRIPTOR_TAILS and len(toks)>1: out.add(" ".join(toks[:-1]))
    if len(toks)>2 and toks[-2:]==["for","women"]: out.add(" ".join(toks[:-2]))
    if len(toks)>2 and toks[-2:]==["for","men"]: out.add(" ".join(toks[:-2]))
    return sorted((x for x in out if x),key=len)


def token_relation(a: str,b: str):
    A=a.split(); B=b.split(); sa,sb=set(A),set(B)
    if not A or not B:return 0.0
    if sa==sb and len(sa)>=2:return 0.985
    # contiguous containment is strong within a known brand
    short,long=(A,B) if len(A)<=len(B) else (B,A)
    if len(short)>=2:
        for i in range(len(long)-len(short)+1):
            if long[i:i+len(short)]==short:
                return 0.975 if len(short)>=3 else 0.955
    inter=len(sa&sb); union=len(sa|sb)
    j=inter/union if union else 0
    cov=inter/min(len(sa),len(sb)) if min(len(sa),len(sb)) else 0
    if inter>=2 and cov==1 and j>=0.55:return 0.94
    if inter>=2 and j>=0.72:return 0.93
    return 0.0


def main():
    catalog=read_csv(CATALOG); confirmed=read_csv(CONFIRMED) if CONFIRMED.exists() else []
    parsed=[]; invalid=[]; total=blank=0
    with URLS.open("r",encoding="utf-8-sig",errors="replace") as f:
        for ln,raw in enumerate(f,1):
            total+=1; u=raw.strip()
            if not u: blank+=1; continue
            r=parse_url(u)
            if r:r["line"]=ln; parsed.append(r)
            else:invalid.append((ln,u))

    by_id,by_name,by_brand,by_bn,by_combo=(defaultdict(list) for _ in range(5))
    for r in parsed:
        by_id[r["id"]].append(r); by_name[r["perfume_norm"]].append(r); by_brand[r["brand_norm"]].append(r); by_bn[(r["brand_norm"],r["perfume_norm"])].append(r)
        combos={norm(r["perfume"]+" "+r["brand"]),norm(r["brand"]+" "+r["perfume"])}
        if r["brand_core"]: combos|={norm(r["perfume"]+" "+r["brand_core"]),norm(r["brand_core"]+" "+r["perfume"])}
        for c in combos:
            if c:by_combo[c].append(r)

    confirmed_by_code={}; votes=defaultdict(Counter); displays=defaultdict(Counter)
    for row in confirmed:
        code=(row.get("shobi_code") or "").strip(); b=(row.get("original_brand") or "").strip()
        if code:confirmed_by_code[code]=row
        if suffix(code) and b:
            nb=norm(b); votes[suffix(code)][nb]+=1000; displays[nb][b]+=1

    # Teach suffix brands from two kinds of strong corpus evidence before the main pass:
    # exact perfume+brand text and globally unique exact perfume names.
    learned_combo=learned_unique=0
    for row in catalog:
        code=(row.get("shobi_code") or "").strip(); n=norm(row.get("inspired_by") or ""); s=suffix(code)
        strong=None
        if n: strong=uniq(by_combo.get(n,[]))
        if strong:
            votes[s][strong["brand_norm"]]+=2; displays[strong["brand_norm"]][strong["brand"]]+=1; learned_combo+=1
        elif n:
            strong=uniq(by_name.get(n,[]))
            if strong:
                votes[s][strong["brand_norm"]]+=1; displays[strong["brand_norm"]][strong["brand"]]+=1; learned_unique+=1

    s2b={}; s2d={}
    for s,v in votes.items():
        ranked=v.most_common();
        if not ranked:continue
        top,score=ranked[0]; second=ranked[1][1] if len(ranked)>1 else 0
        # confirmed or fully unanimous learned evidence; otherwise require clear dominance
        if score>=1000 or second==0 or (score>=4 and score>=second*3):
            s2b[s]=top; s2d[s]=displays[top].most_common(1)[0][0]

    rows=[]; sc=Counter(); tc=Counter()
    for row in catalog:
        code=(row.get("shobi_code") or "").strip(); inspired=(row.get("inspired_by") or "").strip(); n=norm(inspired); s=suffix(code); ib=s2b.get(s,""); ibd=s2d.get(s,"")
        status="NOT_FOUND"; typ=score=""; count=0; matched=None; note=""
        existing=confirmed_by_code.get(code)
        if existing:
            eid=(existing.get("fragrantica_id") or "").strip(); eb=(existing.get("original_brand") or "").strip(); ep=(existing.get("original_perfume") or inspired).strip()
            if eid and eid in by_id:
                ch=by_id[eid]; matched=ch[0]; count=len(ch); status,typ,score="FOUND","CONFIRMED_ID_IN_CORPUS","1.0000"
            else:
                ch=by_bn.get((norm(eb),norm(ep)),[]); sel=uniq(ch); count=len(ch)
                if sel:matched=sel; status,typ,score="FOUND","CONFIRMED_NAME_IN_CORPUS","1.0000"
                elif ch:status,typ="AMBIGUOUS","CONFIRMED_NAME_MULTIPLE_IDS"
                else:status,typ="MAPPED_NOT_IN_CORPUS","CONFIRMED_MAPPING_ONLY"
        else:
            ch=by_combo.get(n,[]) if n else []; sel=uniq(ch); count=len(ch)
            if sel:matched=sel; status,typ,score="FOUND","EXACT_PERFUME_BRAND_TEXT","1.0000"
            elif ch:status,typ="AMBIGUOUS","EXACT_COMBINED_MULTIPLE_IDS"

            variants=partial_brand_variants(inspired,ibd) if ib else ([n] if n else [])
            if status=="NOT_FOUND" and ib:
                ch=[x for v in variants for x in by_bn.get((ib,v),[])]; sel=uniq(ch); count=len(ch)
                if sel:matched=sel; status,typ,score="FOUND","EXACT_BRAND_CLEAN_NAME","1.0000"
                elif ch:status,typ="AMBIGUOUS","EXACT_BRAND_NAME_MULTIPLE_IDS"

            if status=="NOT_FOUND":
                ch=[x for v in variants for x in by_name.get(v,[])]; sel=uniq(ch); count=len(ch)
                if sel:matched=sel; status,typ,score="FOUND","EXACT_UNIQUE_NAME","1.0000"
                elif ch and len({(x["brand_norm"],x["id"]) for x in ch})>1:status,typ="AMBIGUOUS","EXACT_NAME_MULTIPLE_CANDIDATES"

            # Token-order/containment matching within known brand. This catches line prefixes,
            # reordered titles and abbreviated brand tails without discarding variant words.
            if status=="NOT_FOUND" and ib and variants:
                candidates=[]
                for cand in by_brand.get(ib,[]):
                    best=0.0
                    for v in variants:
                        if qtokens(v)!=qtokens(cand["perfume_norm"]):continue
                        best=max(best,token_relation(v,cand["perfume_norm"]))
                    if best>=0.93:candidates.append((best,cand))
                candidates.sort(key=lambda x:x[0],reverse=True)
                if candidates:
                    bs,best=candidates[0]; runner=candidates[1][0] if len(candidates)>1 else 0; near=[x for x in candidates if bs-x[0]<0.02]; count=len(candidates)
                    if len(near)==1 and bs-runner>=0.02:matched=best; status,typ,score="FOUND","SAFE_TOKEN_SAME_BRAND",f"{bs:.4f}"
                    else:status,typ,score="AMBIGUOUS","TOKEN_MULTIPLE_CANDIDATES",f"{bs:.4f}"

            if status=="NOT_FOUND" and ib and variants:
                candidates=[]
                for cand in by_brand.get(ib,[]):
                    best=0.0
                    for v in variants:
                        if qtokens(v)!=qtokens(cand["perfume_norm"]):continue
                        ratio=SequenceMatcher(None,v,cand["perfume_norm"]).ratio()
                        # Fuzzy lower bound is still conservative because brand and qualifier set are fixed.
                        if ratio>=0.86:best=max(best,ratio)
                    if best:candidates.append((best,cand))
                candidates.sort(key=lambda x:x[0],reverse=True)
                if candidates:
                    bs,best=candidates[0]; runner=candidates[1][0] if len(candidates)>1 else 0; near=[x for x in candidates if bs-x[0]<0.035]; count=len(candidates)
                    if bs>=0.88 and len(near)==1 and bs-runner>=0.035:matched=best; status,typ,score="FOUND","SAFE_FUZZY_SAME_BRAND",f"{bs:.4f}"
                    else:status,typ,score="AMBIGUOUS","FUZZY_MULTIPLE_CANDIDATES",f"{bs:.4f}"

        out={"prestashop_product_id":row.get("prestashop_product_id",""),"shobi_code":code,"inspired_by":inspired,"code_suffix":s,"inferred_brand":ibd,"status":status,"match_type":typ,"score":score,"candidate_count":count,"fragrantica_brand":matched["brand"] if matched else "","fragrantica_perfume":matched["perfume"] if matched else "","fragrantica_id":matched["id"] if matched else "","fragrantica_url":matched["url"] if matched else "","note":note}
        rows.append(out); sc[status]+=1; tc[typ or "NONE"]+=1

    fields=["prestashop_product_id","shobi_code","inspired_by","code_suffix","inferred_brand","status","match_type","score","candidate_count","fragrantica_brand","fragrantica_perfume","fragrantica_id","fragrantica_url","note"]
    write_csv(REPORT,rows,fields); write_csv(AMBIG,[r for r in rows if r["status"]=="AMBIGUOUS"],fields); write_csv(UNMATCH,[r for r in rows if r["status"] in {"NOT_FOUND","MAPPED_NOT_IN_CORPUS"}],fields)
    uu=len({r["url"] for r in parsed}); ui=len(by_id)
    summary={"catalog_rows":len(catalog),"fragrantica_lines_total":total,"fragrantica_blank_lines":blank,"fragrantica_valid_url_rows":len(parsed),"fragrantica_invalid_url_rows":len(invalid),"fragrantica_unique_urls":uu,"fragrantica_duplicate_url_rows":len(parsed)-uu,"fragrantica_unique_ids":ui,"fragrantica_extra_rows_sharing_an_id":len(parsed)-ui,"confirmed_mapping_rows":len(confirmed),"learned_exact_combined_rows":learned_combo,"learned_exact_unique_name_rows":learned_unique,"safe_code_suffix_brand_mappings":len(s2b),"catalog_rows_with_inferred_brand":sum(1 for r in catalog if suffix(r.get("shobi_code","")) in s2b),"status_counts":dict(sc),"match_type_counts":dict(tc),"found_total":sc.get("FOUND",0),"ambiguous_total":sc.get("AMBIGUOUS",0),"not_found_total":sc.get("NOT_FOUND",0),"mapped_not_in_corpus_total":sc.get("MAPPED_NOT_IN_CORPUS",0),"invalid_url_examples":[{"line":n,"value":v} for n,v in invalid[:20]]}
    OUT.mkdir(parents=True,exist_ok=True); SUMMARY_JSON.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    SUMMARY.write_text("# Shobi ↔ Fragrantica URL corpus match\n\n"+f"FOUND: **{summary['found_total']}**\n\nAMBIGUOUS: **{summary['ambiguous_total']}**\n\nNOT_FOUND: **{summary['not_found_total']}**\n\nMAPPED_NOT_IN_CORPUS: **{summary['mapped_not_in_corpus_total']}**\n",encoding="utf-8")
    print(json.dumps(summary,indent=2,ensure_ascii=False))

if __name__=="__main__":main()
