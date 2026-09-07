#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database_complete.json"
CARD_DIR = ROOT / "fragrantica-scraper-archive" / "social-cards" / "images"
WORK = ROOT / ".social-card-notes-work"
TIFF = WORK / "social-note-panels.tiff"
MANIFEST = WORK / "manifest.json"
TSV = WORK / "ocr.tsv"
REPORT = ROOT / "social-card-main-notes-report.json"
OUT_JSON = ROOT / "social-card-main-notes.json"

# Social cards in the archive are 1200x1200.  The Fragrantica `notes` panel is
# the lower-left white card.  We deliberately crop ONLY that panel: no perfume
# pyramid or page text is consulted anywhere in this extractor.
CROP_1200 = (48, 738, 448, 1097)
SCALE = 2


def flatten_records(data):
    if isinstance(data, list) and data and isinstance(data[0], dict) and isinstance(data[0].get("perfumes"), list):
        out=[]
        for b in data:
            out.extend(b.get("perfumes", []))
        return out
    return data if isinstance(data, list) else []


def official(p):
    s=str(p.get("fragrantica_status") or p.get("fragranticaStatus") or "").upper()
    return not s.startswith("RESOLVED_NO_FORCE")


def frag_id(p):
    for k in ("fragranticaId","fragrantica_id","fragranticaID"):
        v=p.get(k)
        if v not in (None,""):
            try: return int(str(v))
            except Exception: pass
    for k in ("fragrantica_url","fragranticaLocalUrl","fragranticaUrl"):
        v=p.get(k)
        if v:
            m=re.search(r"-(\d+)\.html", str(v))
            if m: return int(m.group(1))
    return None


def code_of(p):
    return str(p.get("code") or p.get("shobiCode") or p.get("shobi_code") or "").strip()


def load_official():
    data=json.loads(DB.read_text(encoding="utf-8"))
    recs=[p for p in flatten_records(data) if official(p)]
    by_id={frag_id(p): p for p in recs if frag_id(p)}
    return data,recs,by_id


def cards_by_final_id(by_id):
    out={}
    if not CARD_DIR.exists(): return out
    for p in CARD_DIR.iterdir():
        if not p.is_file() or p.suffix.lower() not in {".jpg",".jpeg",".png",".webp"}: continue
        m=re.search(r"_(\d+)$", p.stem)
        if not m: continue
        fid=int(m.group(1))
        if fid in by_id and fid not in out:
            out[fid]=p
    return out


def prepare():
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter
    _, recs, by_id=load_official()
    cards=cards_by_final_id(by_id)
    WORK.mkdir(exist_ok=True)
    pages=[]
    frames=[]
    for fid,p in sorted(cards.items()):
        im=Image.open(p).convert("L")
        if im.size != (1200,1200):
            # Normalize coordinates for rare non-1200 variants.
            x1,y1,x2,y2=CROP_1200
            sx=im.width/1200.0; sy=im.height/1200.0
            box=(round(x1*sx),round(y1*sy),round(x2*sx),round(y2*sy))
        else:
            box=CROP_1200
        panel=im.crop(box)
        panel=ImageOps.autocontrast(panel)
        panel=ImageEnhance.Contrast(panel).enhance(1.35)
        panel=panel.resize((panel.width*SCALE,panel.height*SCALE), Image.Resampling.LANCZOS)
        panel=panel.filter(ImageFilter.SHARPEN)
        frames.append(panel)
        rec=by_id[fid]
        pages.append({"page":len(pages)+1,"fragranticaId":fid,"code":code_of(rec),"card":str(p.relative_to(ROOT))})
    if not frames:
        raise SystemExit("No matching archived social cards found")
    frames[0].save(TIFF, save_all=True, append_images=frames[1:], compression="tiff_deflate", dpi=(300,300))
    MANIFEST.write_text(json.dumps(pages,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Prepared {len(frames)} social-card note panels -> {TIFF}")
    print(f"Official records: {len(recs)} | exact archived cards by Fragrantica ID: {len(cards)}")


def clean_token(s):
    s=s.replace("|","").replace("©","").strip()
    s=re.sub(r"^[^\wÀ-ž&+\-™'’]+|[^\wÀ-ž&+\-™'’]+$", "", s)
    return s


def parse_tsv():
    pages=json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_page={int(p["page"]):p for p in pages}
    words={n:[] for n in by_page}
    with TSV.open(encoding="utf-8",errors="replace",newline="") as f:
        rd=csv.DictReader(f,delimiter="\t")
        for r in rd:
            try:
                pg=int(r.get("page_num") or 0); conf=float(r.get("conf") or -1)
                text=clean_token(r.get("text") or "")
                if pg not in words or conf < 25 or not text: continue
                left=int(r["left"]); top=int(r["top"]); width=int(r["width"]); height=int(r["height"])
                words[pg].append((left,top,width,height,conf,text))
            except Exception:
                continue

    # Coordinates below refer to the 400x359 source crop, then are scaled x2.
    # Three visual columns, two visual rows.  This preserves the social-card
    # reading order exactly: row 1 left->right, then row 2 left->right.
    col_ranges=[(10,135),(135,270),(270,400)]
    row_ranges=[(135,255),(285,359)]
    results=[]
    low_conf=[]
    for pg,meta in by_page.items():
        slots=[]
        page_words=words.get(pg,[])
        for ry,(y1,y2) in enumerate(row_ranges):
            for cx,(x1,x2) in enumerate(col_ranges):
                zone=[]
                for left,top,w,h,conf,text in page_words:
                    ox=left/SCALE; oy=top/SCALE
                    center=(left+w/2)/SCALE
                    if x1 <= center < x2 and y1 <= oy < y2:
                        # Ignore panel heading and obvious OCR debris.
                        if text.lower() in {"notes","note"}: continue
                        zone.append((top,left,conf,text))
                if not zone:
                    continue
                zone.sort(key=lambda z:(z[0],z[1]))
                label=" ".join(z[3] for z in zone)
                label=re.sub(r"\s+"," ",label).strip()
                # Common OCR punctuation normalization only; never substitute a
                # different note from pyramid/database data.
                label=label.replace("TM","™") if label.endswith(" TM") else label
                conf=sum(z[2] for z in zone)/len(zone)
                if label and len(label) <= 60:
                    slots.append({"slot":ry*3+cx+1,"name":label,"ocrConfidence":round(conf,1)})
        names=[s["name"] for s in slots]
        avg=round(sum(s["ocrConfidence"] for s in slots)/len(slots),1) if slots else 0.0
        item={**meta,"mainNotes":names,"slots":slots,"ocrConfidence":avg}
        results.append(item)
        if not names or avg < 55:
            low_conf.append(item)

    OUT_JSON.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report={
        "rule":"mainNotes come ONLY from the archived Fragrantica social-card notes panel; pyramid is never used",
        "processed_cards":len(results),
        "with_notes":sum(bool(x["mainNotes"]) for x in results),
        "empty":sum(not x["mainNotes"] for x in results),
        "low_confidence_lt55":len(low_conf),
        "note_count_distribution":{},
        "low_confidence_sample":[{"code":x["code"],"fragranticaId":x["fragranticaId"],"mainNotes":x["mainNotes"],"ocrConfidence":x["ocrConfidence"]} for x in low_conf[:50]],
        "sample":[{"code":x["code"],"fragranticaId":x["fragranticaId"],"mainNotes":x["mainNotes"],"ocrConfidence":x["ocrConfidence"]} for x in results[:30]],
    }
    for x in results:
        k=str(len(x["mainNotes"])); report["note_count_distribution"][k]=report["note_count_distribution"].get(k,0)+1
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("mode",choices=["prepare","parse"])
    args=ap.parse_args()
    prepare() if args.mode=="prepare" else parse_tsv()

if __name__=="__main__": main()
