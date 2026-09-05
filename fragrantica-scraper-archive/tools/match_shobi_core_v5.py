from __future__ import annotations

import csv, json, os, re, unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[2]
CATALOG=Path(os.environ.get("SHOBI_MATCH_CATALOG", str(ROOT/"perfume-database/catalog/shobi-master-v1.csv")))
CONFIRMED=ROOT/"perfume-database/confirmed/shobi-fragrantica-mapping.csv"
URLS=ROOT/"fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt"
OUT=ROOT/"fragrantica-scraper-archive/corpus-match"
REPORT,AMBIG,UNMATCH=OUT/"shobi-fragrantica-corpus-match.csv",OUT/"ambiguous.csv",OUT/"unmatched.csv"
SUMMARY,SUMMARY_JSON=OUT/"summary.md",OUT/"summary.json"

QUALIFIERS={"absolu","absolute","absolue","elixir","essence","extreme","extrait","intense","intensely","intensivo","intenso","noir","parfum","perfume","rouge","sport","edp","edt","edc","limited","edition","collector"}
GENERIC_BRAND={"by","parfum","parfums","perfume","perfumes","fragrance","fragrances","parfumeur","parfumerie","parfumer","createur","prive","prives","the"}
TYPO={"intensenly":"intensely","intensley":"intensely","graffity":"graffiti","grafitty":"graffiti"}


def norm(s:str)->str:
    s=unquote((s or "").strip()).replace("&"," and ").replace("’","'").replace("®","")
    s=unicodedata.normalize("NFKD",s); s="".join(c for c in s if not unicodedata.combining(c)).lower().replace("'"," ")
    return " ".join(re.sub(r"[^a-z0-9]+"," ",s).split())


def name_norm(s:str)->str:
    n=norm(s)
    n=re.sub(r"\beau de parfum\b","edp",n); n=re.sub(r"\beau de toilette\b","edt",n); n=re.sub(r"\beau de cologne\b","edc",n)
    toks=[TYPO.get(t,t) for t in n.split()]
    return " ".join(toks)


def code_suffix(code:str)->str:
    code=(code or "").strip().upper(); return code.rsplit("-",1)[-1] if "-" in code else ""


def brand_core(s:str)->str:return " ".join(t for t in norm(s).split() if t not in GENERIC_BRAND)
def qtokens(s:str):return frozenset(t for t in name_norm(s).split() if t in QUALIFIERS)
def no_conc(s:str)->str:return " ".join(t for t in name_norm(s).split() if t not in {"edp","edt","edc"})


def read_csv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def write_csv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)


def parse_url(u):
    m=re.match(r"^https?://(?:www\.)?fragrantica\.com/perfume/([^/]+)/(.+)-(\d+)\.html$",u.strip(),re.I)
    if not m:return None
    bs,ps,fid=m.groups();b=unquote(bs).replace("-"," ").strip();p=unquote(ps).replace("-"," ").strip()
    return {"brand":b,"perfume":p,"brand_norm":norm(b),"brand_core":brand_core(b),"perfume_norm":name_norm(p),"id":fid,"url":u.strip()}


def uniq(rs):
    vals=list({(r["brand_norm"],r["perfume_norm"],r["id"]):r for r in rs}.values());return vals[0] if len(vals)==1 else None


def name_variants(name,brand=""):
    n=name_norm(name);out={n} if n else set()
    if not n:return []
    if brand:
        nt=n.split();bt=set(brand_core(brand).split());forms={name_norm(brand),name_norm(brand_core(brand))}-{""}
        for f in forms:
            if n.endswith(" "+f):out.add(n[:-(len(f)+1)].strip())
            if n.startswith(f+" "):out.add(n[len(f)+1:].strip())
        for k in range(1,min(6,len(nt)-1)+1):
            tail=nt[-k:];tc=[t for t in tail if t not in GENERIC_BRAND];ts=" ".join(tc);bc=brand_core(brand)
            if tc and set(tc).issubset(bt):out.add(" ".join(nt[:-k]))
            if ts and bc and SequenceMatcher(None,ts,bc).ratio()>=.82:out.add(" ".join(nt[:-k]))
            if len(tc)==1 and len(tc[0])>=5 and any(SequenceMatcher(None,tc[0],x).ratio()>=.88 for x in bt):out.add(" ".join(nt[:-k]))
    # harmless catalogue descriptors as alternate strings
    for tail in (" type"," for women"," for men"," woman"," women"," man"," men"):
        if n.endswith(tail) and len(n)>len(tail)+2:out.add(n[:-len(tail)].strip())
    return sorted((x for x in out if x),key=len)


def token_relation(a,b):
    A=a.split();B=b.split();sa,sb=set(A),set(B)
    if not A or not B:return 0.0
    if sa==sb and len(sa)>=2:return .986
    short,long=(A,B) if len(A)<=len(B) else (B,A)
    if len(short)>=2:
        for i in range(len(long)-len(short)+1):
            if long[i:i+len(short)]==short:return .976 if len(short)>=3 else .956
    inter=len(sa&sb);union=len(sa|sb);j=inter/union if union else 0;cov=inter/min(len(sa),len(sb))
    if inter>=2 and cov==1 and j>=.52:return .944
    if inter>=2 and j>=.70:return .934
    return 0.0


def detect_tail_brand(text,alias_unique):
    toks=norm(text).split();best=None
    for k in range(1,min(6,len(toks)-1)+1):
        tail=" ".join(toks[-k:])
        b=alias_unique.get(tail)
        if b:best=(k,b)
    if best:return best[1]
    return ""


def main():
    catalog=read_csv(CATALOG);confirmed=read_csv(CONFIRMED) if CONFIRMED.exists() else []
    parsed=[];invalid=[];total=blank=0
    with URLS.open("r",encoding="utf-8-sig",errors="replace") as f:
        for ln,raw in enumerate(f,1):
            total+=1;u=raw.strip()
            if not u:blank+=1;continue
            r=parse_url(u)
            if r:r["line"]=ln;parsed.append(r)
            else:invalid.append((ln,u))

    by_id,by_name,by_brand,by_bn,by_combo,by_brand_noconc=(defaultdict(list) for _ in range(6))
    brand_displays=defaultdict(Counter);alias_to_brands=defaultdict(set)
    for r in parsed:
        by_id[r["id"]].append(r);by_name[r["perfume_norm"]].append(r);by_brand[r["brand_norm"]].append(r);by_bn[(r["brand_norm"],r["perfume_norm"])].append(r);by_brand_noconc[(r["brand_norm"],no_conc(r["perfume_norm"]))].append(r)
        brand_displays[r["brand_norm"]][r["brand"]]+=1
        combos={name_norm(r["perfume"]+" "+r["brand"]),name_norm(r["brand"]+" "+r["perfume"])}
        if r["brand_core"]:combos|={name_norm(r["perfume"]+" "+r["brand_core"]),name_norm(r["brand_core"]+" "+r["perfume"])}
        for c in combos:
            if c:by_combo[c].append(r)
    # unique brand aliases from full/core/last-token/last-two tokens
    for bn,disp in brand_displays.items():
        bc=brand_core(disp.most_common(1)[0][0]); toks=bc.split();aliases={bn,bc}
        if toks and len(toks[-1])>=4:aliases.add(toks[-1])
        if len(toks)>=2:aliases.add(" ".join(toks[-2:]))
        for a in aliases:
            if len(a)>=4:alias_to_brands[a].add(bn)
    alias_unique={a:next(iter(bs)) for a,bs in alias_to_brands.items() if len(bs)==1}

    confirmed_by_code={};votes=defaultdict(Counter);displays=defaultdict(Counter);row_detected={}
    for row in confirmed:
        code=(row.get("shobi_code") or "").strip();b=(row.get("original_brand") or "").strip();s=code_suffix(code)
        if code:confirmed_by_code[code]=row
        if s and b:
            nb=norm(b);votes[s][nb]+=1000;displays[nb][b]+=1

    learned_combo=learned_unique=learned_tail=0
    for row in catalog:
        code=(row.get("shobi_code") or "").strip();s=code_suffix(code);text=(row.get("inspired_by") or "").strip();n=name_norm(text)
        strong=uniq(by_combo.get(n,[])) if n else None
        if strong:
            votes[s][strong["brand_norm"]]+=3;displays[strong["brand_norm"]][strong["brand"]]+=1;learned_combo+=1
        else:
            strong=uniq(by_name.get(n,[])) if n else None
            if strong:votes[s][strong["brand_norm"]]+=1;displays[strong["brand_norm"]][strong["brand"]]+=1;learned_unique+=1
        db=detect_tail_brand(text,alias_unique) if text else ""
        if db:
            row_detected[code]=db;votes[s][db]+=2;displays[db][brand_displays[db].most_common(1)[0][0]]+=1;learned_tail+=1

    s2b={};s2d={}
    for s,v in votes.items():
        ranked=v.most_common();
        if not ranked:continue
        top,score=ranked[0];second=ranked[1][1] if len(ranked)>1 else 0
        if score>=1000 or second==0 or (score>=5 and score>=second*3):
            s2b[s]=top;s2d[s]=(displays[top] or brand_displays[top]).most_common(1)[0][0]

    rows=[];sc=Counter();tc=Counter()
    for row in catalog:
        code=(row.get("shobi_code") or "").strip();text=(row.get("inspired_by") or "").strip();n=name_norm(text);s=code_suffix(code)
        ib=s2b.get(s,"") or row_detected.get(code,"");ibd=s2d.get(s,"") if s2b.get(s) else (brand_displays[ib].most_common(1)[0][0] if ib else "")
        status="NOT_FOUND";typ=score=note="";count=0;matched=None
        existing=confirmed_by_code.get(code)
        if existing:
            eid=(existing.get("fragrantica_id") or "").strip();eb=(existing.get("original_brand") or "").strip();ep=(existing.get("original_perfume") or text).strip()
            if eid and eid in by_id:
                ch=by_id[eid];matched=ch[0];count=len(ch);status,typ,score="FOUND","CONFIRMED_ID_IN_CORPUS","1.0000"
            else:
                ch=by_bn.get((norm(eb),name_norm(ep)),[]);sel=uniq(ch);count=len(ch)
                if sel:matched=sel;status,typ,score="FOUND","CONFIRMED_NAME_IN_CORPUS","1.0000"
                elif ch:status,typ="AMBIGUOUS","CONFIRMED_NAME_MULTIPLE_IDS"
                else:status,typ="MAPPED_NOT_IN_CORPUS","CONFIRMED_MAPPING_ONLY"
        else:
            ch=by_combo.get(n,[]) if n else [];sel=uniq(ch);count=len(ch)
            if sel:matched=sel;status,typ,score="FOUND","EXACT_PERFUME_BRAND_TEXT","1.0000"
            elif ch:status,typ="AMBIGUOUS","EXACT_COMBINED_MULTIPLE_IDS"
            variants=name_variants(text,ibd) if ib else ([n] if n else [])
            if status=="NOT_FOUND" and ib:
                ch=[x for v in variants for x in by_bn.get((ib,v),[])];sel=uniq(ch);count=len(ch)
                if sel:matched=sel;status,typ,score="FOUND","EXACT_BRAND_CLEAN_NAME","1.0000"
                elif ch:status,typ="AMBIGUOUS","EXACT_BRAND_NAME_MULTIPLE_IDS"
            if status=="NOT_FOUND" and ib:
                # EDP/EDT spelling or omitted concentration; only accept a unique corpus candidate.
                ch=[x for v in variants for x in by_brand_noconc.get((ib,no_conc(v)),[])];sel=uniq(ch);count=len(ch)
                if sel:matched=sel;status,typ,score="FOUND","SAFE_CONCENTRATION_EQUIVALENT","0.9950"
                elif ch:status,typ="AMBIGUOUS","CONCENTRATION_MULTIPLE_IDS"
            if status=="NOT_FOUND":
                ch=[x for v in variants for x in by_name.get(v,[])];sel=uniq(ch);count=len(ch)
                if sel:matched=sel;status,typ,score="FOUND","EXACT_UNIQUE_NAME","1.0000"
                elif ch and len({(x["brand_norm"],x["id"]) for x in ch})>1:status,typ="AMBIGUOUS","EXACT_NAME_MULTIPLE_CANDIDATES"
            if status=="NOT_FOUND" and ib and variants:
                cand=[]
                for c in by_brand.get(ib,[]):
                    best=0
                    for v in variants:
                        if qtokens(v)!=qtokens(c["perfume_norm"]):continue
                        best=max(best,token_relation(v,c["perfume_norm"]))
                    if best>=.93:cand.append((best,c))
                cand.sort(key=lambda x:x[0],reverse=True)
                if cand:
                    bs,best=cand[0];runner=cand[1][0] if len(cand)>1 else 0;near=[x for x in cand if bs-x[0]<.02];count=len(cand)
                    if len(near)==1 and bs-runner>=.02:matched=best;status,typ,score="FOUND","SAFE_TOKEN_SAME_BRAND",f"{bs:.4f}"
                    else:status,typ,score="AMBIGUOUS","TOKEN_MULTIPLE_CANDIDATES",f"{bs:.4f}"
            if status=="NOT_FOUND" and ib and variants:
                cand=[]
                for c in by_brand.get(ib,[]):
                    best=0
                    for v in variants:
                        if qtokens(v)!=qtokens(c["perfume_norm"]):continue
                        rr=SequenceMatcher(None,v,c["perfume_norm"]).ratio()
                        if rr>=.85:best=max(best,rr)
                    if best:cand.append((best,c))
                cand.sort(key=lambda x:x[0],reverse=True)
                if cand:
                    bs,best=cand[0];runner=cand[1][0] if len(cand)>1 else 0;near=[x for x in cand if bs-x[0]<.035];count=len(cand)
                    if bs>=.875 and len(near)==1 and bs-runner>=.035:matched=best;status,typ,score="FOUND","SAFE_FUZZY_SAME_BRAND",f"{bs:.4f}"
                    else:status,typ,score="AMBIGUOUS","FUZZY_MULTIPLE_CANDIDATES",f"{bs:.4f}"
        out={"prestashop_product_id":row.get("prestashop_product_id",""),"shobi_code":code,"inspired_by":text,"code_suffix":s,"inferred_brand":ibd,"status":status,"match_type":typ,"score":score,"candidate_count":count,"fragrantica_brand":matched["brand"] if matched else "","fragrantica_perfume":matched["perfume"] if matched else "","fragrantica_id":matched["id"] if matched else "","fragrantica_url":matched["url"] if matched else "","note":note}
        rows.append(out);sc[status]+=1;tc[typ or "NONE"]+=1

    fields=["prestashop_product_id","shobi_code","inspired_by","code_suffix","inferred_brand","status","match_type","score","candidate_count","fragrantica_brand","fragrantica_perfume","fragrantica_id","fragrantica_url","note"]
    write_csv(REPORT,rows,fields);write_csv(AMBIG,[r for r in rows if r["status"]=="AMBIGUOUS"],fields);write_csv(UNMATCH,[r for r in rows if r["status"] in {"NOT_FOUND","MAPPED_NOT_IN_CORPUS"}],fields)
    uu=len({r["url"] for r in parsed});ui=len(by_id)
    summary={"catalog_rows":len(catalog),"fragrantica_lines_total":total,"fragrantica_blank_lines":blank,"fragrantica_valid_url_rows":len(parsed),"fragrantica_invalid_url_rows":len(invalid),"fragrantica_unique_urls":uu,"fragrantica_duplicate_url_rows":len(parsed)-uu,"fragrantica_unique_ids":ui,"fragrantica_extra_rows_sharing_an_id":len(parsed)-ui,"confirmed_mapping_rows":len(confirmed),"learned_exact_combined_rows":learned_combo,"learned_exact_unique_name_rows":learned_unique,"learned_tail_brand_rows":learned_tail,"safe_code_suffix_brand_mappings":len(s2b),"catalog_rows_with_inferred_brand":sum(1 for r in catalog if s2b.get(code_suffix(r.get("shobi_code",""))) or row_detected.get((r.get("shobi_code") or "").strip())),"status_counts":dict(sc),"match_type_counts":dict(tc),"found_total":sc.get("FOUND",0),"ambiguous_total":sc.get("AMBIGUOUS",0),"not_found_total":sc.get("NOT_FOUND",0),"mapped_not_in_corpus_total":sc.get("MAPPED_NOT_IN_CORPUS",0),"invalid_url_examples":[{"line":n,"value":v} for n,v in invalid[:20]]}
    OUT.mkdir(parents=True,exist_ok=True);SUMMARY_JSON.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");SUMMARY.write_text("# Shobi ↔ Fragrantica URL corpus match\n\n"+f"FOUND: **{summary['found_total']}**\n\nAMBIGUOUS: **{summary['ambiguous_total']}**\n\nNOT_FOUND: **{summary['not_found_total']}**\n\nMAPPED_NOT_IN_CORPUS: **{summary['mapped_not_in_corpus_total']}**\n",encoding="utf-8")
    print(json.dumps(summary,indent=2,ensure_ascii=False))

if __name__=="__main__":main()
