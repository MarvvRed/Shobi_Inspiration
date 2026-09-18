#!/usr/bin/env python3
"""Non-destructive pilot: read Social Card note labels one cell at a time.

Goal: improve first-pass note assignment without weakening acceptance.
- Detect label components from card geometry/OCR, never from catalog note count.
- Re-OCR each label crop independently with several PSM/preprocessing variants.
- Accept a label only when multiple independent reads agree on one Fragrantica note.
- Compare to catalog only after the image-derived ordered sequence is fixed.
"""
from __future__ import annotations

import csv, io, json, os, re, subprocess, unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from audit_social_card_order_from_images import ROOT, DB, OUT, CROP, code, find_card

LEXICON = ROOT / "database/audits/fragrantica-note-lexicon.txt"
PILOT_OUT = ROOT / "database/audits/label-ocr-pilot.json"
SCALE = 3
MIN_VOTES = 2
MIN_EXACT_OR_FUZZY = 0.84
MIN_FUZZY_MARGIN = 0.08


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


def tsv(im, psm):
    b = io.BytesIO(); im.save(b, format="PNG")
    run = subprocess.run(
        ["tesseract","stdin","stdout","--psm",str(psm),"-l","eng","tsv"],
        input=b.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=10, check=True, env={**os.environ,"OMP_THREAD_LIMIT":"1"})
    return list(csv.DictReader(io.StringIO(run.stdout.decode("utf-8","replace")), delimiter="\t"))


def locate_header(panel):
    scaled = panel.resize((panel.width*SCALE,panel.height*SCALE), Image.Resampling.LANCZOS)
    hits=[]
    for r in tsv(scaled, 11):
        if norm(r.get("text")) != "notes": continue
        try:
            x=float(r["left"])/SCALE; y=float(r["top"])/SCALE; conf=float(r.get("conf") or -1)
        except Exception: continue
        if x < 180 and y < 150 and conf >= 30: hits.append(y)
    return min(hits) if hits else None


def label_components(panel, header_y):
    """Use a permissive whole-panel OCR only to localize text labels."""
    prep = ImageOps.autocontrast(panel.convert("L"))
    prep = ImageEnhance.Contrast(prep).enhance(1.8)
    scaled = prep.resize((panel.width*SCALE,panel.height*SCALE), Image.Resampling.LANCZOS)
    words=[]
    bands=((header_y+105,header_y+200),(header_y+265,header_y+395))
    for r in tsv(scaled, 11):
        text=" ".join(str(r.get("text") or "").split())
        if not text or sum(c.isalpha() for c in text)<2: continue
        try:
            conf=float(r.get("conf") or -1)
            x=float(r["left"])/SCALE; y=float(r["top"])/SCALE
            w=float(r["width"])/SCALE; h=float(r["height"])/SCALE
        except Exception: continue
        if conf < 18: continue
        cy=y+h/2
        row=next((i for i,(lo,hi) in enumerate(bands) if lo<=cy<hi),None)
        if row is None: continue
        words.append(dict(text=text,x=x,y=y,right=x+w,bottom=y+h,cy=cy,row=row,conf=conf))

    # Join nearby words into one physical label; conservative across wide gaps.
    parent=list(range(len(words)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    def union(a,b):
        a,b=root(a),root(b)
        if a!=b: parent[b]=a
    for i,a in enumerate(words):
        for j in range(i):
            b=words[j]
            if a["row"]!=b["row"]: continue
            same_line=abs(a["cy"]-b["cy"])<=12
            hgap=max(0,max(a["x"],b["x"])-min(a["right"],b["right"]))
            overlap=min(a["right"],b["right"])-max(a["x"],b["x"])
            vgap=max(0,max(a["y"],b["y"])-min(a["bottom"],b["bottom"]))
            if (same_line and hgap<=13) or (overlap>=-4 and vgap<=24):
                union(i,j)
    groups=defaultdict(list)
    for i,w in enumerate(words): groups[root(i)].append(w)
    out=[]
    for g in groups.values():
        x1=min(w["x"] for w in g); x2=max(w["right"] for w in g)
        y1=min(w["y"] for w in g); y2=max(w["bottom"] for w in g)
        if x2-x1 < 8 or y2-y1 < 5: continue
        out.append({"row":g[0]["row"],"x1":x1,"x2":x2,"y1":y1,"y2":y2,
                    "locatorText":" ".join(w["text"] for w in sorted(g,key=lambda q:(q["y"],q["x"])))})
    out.sort(key=lambda z:(z["row"],z["x1"]))
    return out


def candidate(raw, lexicon):
    t=norm(raw)
    if not t: return None,0.0,0.0,False
    exact=[n for n in lexicon if norm(n)==t]
    if len(exact)==1: return exact[0],1.0,1.0,True
    ranked=sorted(((SequenceMatcher(None,t,norm(n)).ratio(),n) for n in lexicon),reverse=True)
    if not ranked: return None,0.0,0.0,False
    score,name=ranked[0]; second=ranked[1][0] if len(ranked)>1 else 0
    return name,score,score-second,False


def read_crop(panel, comp, lexicon):
    pad_x,pad_y=10,7
    box=(max(0,int(comp["x1"])-pad_x),max(0,int(comp["y1"])-pad_y),
         min(panel.width,int(comp["x2"])+pad_x),min(panel.height,int(comp["y2"])+pad_y))
    crop=panel.crop(box).convert("L")
    variants=[]
    a=ImageOps.autocontrast(crop); variants.append(("auto",a))
    b=ImageEnhance.Contrast(a).enhance(2.2); variants.append(("contrast",b))
    c=b.point(lambda p: 255 if p>178 else 0); variants.append(("binary",c))
    votes=[]; raw_reads=[]
    lname,lscore,lmargin,lexact=candidate(comp.get("locatorText",""),lexicon)
    locator_ok=bool(lname and (lexact or (lscore>=MIN_EXACT_OR_FUZZY and lmargin>=MIN_FUZZY_MARGIN)))
    raw_reads.append({"variant":"locator","psm":11,"raw":comp.get("locatorText",""),
                      "candidate":lname,"score":round(lscore,3),"margin":round(lmargin,3),
                      "exact":lexact,"eligible":locator_ok})
    if locator_ok: votes.append(lname)
    for vname,im in variants:
        big=im.resize((im.width*4,im.height*4), Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
        for psm in (6,7,8,13):
            try:
                rows=tsv(big,psm)
            except Exception:
                continue
            text=" ".join(" ".join(str(r.get("text") or "").split()) for r in rows)
            text=" ".join(text.split())
            if not text: continue
            name,score,margin,exact=candidate(text,lexicon)
            accepted=bool(name and (exact or (score>=MIN_EXACT_OR_FUZZY and margin>=MIN_FUZZY_MARGIN)))
            raw_reads.append({"variant":vname,"psm":psm,"raw":text,"candidate":name,
                              "score":round(score,3),"margin":round(margin,3),"exact":exact,
                              "eligible":accepted})
            if accepted: votes.append(name)
    counts=Counter(votes)
    winner,nvotes=(counts.most_common(1)[0] if counts else (None,0))
    tie = len(counts)>1 and counts.most_common(2)[0][1]==counts.most_common(2)[1][1]
    confident=bool(winner and nvotes>=MIN_VOTES and not tie)
    return {"note":winner if confident else None,"votes":nvotes,"confident":confident,
            "box":list(box),"reads":raw_reads}


def inspect(row, lexicon):
    base={"code":code(row.get("code")),"fid":str(row.get("fragranticaId") or "")}
    card=find_card(row)
    if not card: return {**base,"result":"NO_CARD"}
    try:
        with Image.open(card) as src:
            if src.width<800 or src.height<800 or src.height/src.width<0.85:
                return {**base,"result":"UNSUPPORTED_GEOMETRY","size":[src.width,src.height]}
            sx,sy=src.width/1200,src.height/1200
            x1,y1,x2,y2=CROP
            panel=src.crop((round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))).convert("RGB").resize((420,380),Image.Resampling.LANCZOS)
    except Exception as e:
        return {**base,"result":"IMAGE_ERROR","error":str(e)}
    try:
        hy=locate_header(panel)
    except Exception as e:
        return {**base,"result":"OCR_ERROR","error":str(e)}
    if hy is None: return {**base,"result":"NO_NOTES_HEADER"}
    comps=label_components(panel,hy)
    if not comps: return {**base,"result":"NO_LABEL_COMPONENTS","headerY":round(hy,1)}
    details=[]
    for c in comps:
        hit=read_crop(panel,c,lexicon)
        details.append({"row":c["row"],"x":round(c["x1"],1),"locatorText":c["locatorText"],**hit})
    complete=all(d["confident"] for d in details)
    observed=[d["note"] for d in details] if complete else []
    catalog=list(row.get("fragranticaSocialCardNotes") or [])
    if complete and observed==catalog:
        result="EXACT_LABEL_SEQUENCE"
    elif complete:
        result="COMPLETE_LABEL_SEQUENCE_DIFFERENT"
    else:
        result="LABEL_OCR_AMBIGUOUS"
    return {**base,"result":result,"headerY":round(hy,1),"detectedCount":len(details),
            "observed":observed,"catalog":catalog,"details":details}


def main():
    rows=json.loads(DB.read_text(encoding="utf-8-sig"))
    audit=json.loads(OUT.read_text(encoding="utf-8"))
    by={code(r.get("code")):r for r in rows}
    targets=[by[code(x.get("code"))] for x in audit.get("rows",[])
             if x.get("result")=="READING_NOT_STRICT_ENOUGH" and code(x.get("code")) in by]
    limit=int(os.environ.get("LABEL_OCR_PILOT_LIMIT","80"))
    if limit>0: targets=targets[:limit]
    lex=[x.strip() for x in LEXICON.read_text(encoding="utf-8").splitlines() if x.strip()]
    results=[]
    for i,row in enumerate(targets,1):
        results.append(inspect(row,lex))
        if i%20==0: print(f"processed {i}/{len(targets)}",flush=True)
    counts=Counter(r["result"] for r in results)
    payload={"mode":"NON_DESTRUCTIVE_PER_LABEL_MULTI_OCR_PILOT_V2",
             "targets":len(targets),
             "acceptance":{"minVotes":MIN_VOTES,"fuzzyScore":MIN_EXACT_OR_FUZZY,"fuzzyMargin":MIN_FUZZY_MARGIN},
             "counts":dict(sorted(counts.items())),"rows":results}
    PILOT_OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"targets":len(targets),"counts":payload["counts"],"output":str(PILOT_OUT)}),flush=True)

if __name__=="__main__":
    main()
