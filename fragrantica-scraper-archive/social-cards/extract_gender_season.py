#!/usr/bin/env python3
"""Extract gender and dominant season from archived Fragrantica social cards."""
from __future__ import annotations
import argparse, csv, re
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

try:
    import pytesseract
except ImportError:
    pytesseract = None

ROOT = Path(__file__).resolve().parents[2]
SOCIAL = ROOT / "fragrantica-scraper-archive" / "social-cards"
MANIFEST = SOCIAL / "manifest.csv"
OUT = SOCIAL / "gender-season.csv"
CROPS = SOCIAL / "calibration-crops"
SEASONS = ("winter", "spring", "summer", "fall")
SEASON_ROIS = {
    "winter": (0.416, 0.835, 0.650, 0.885),
    "spring": (0.680, 0.835, 0.915, 0.885),
    "summer": (0.416, 0.900, 0.650, 0.950),
    "fall":   (0.680, 0.900, 0.915, 0.950),
}
GENDER_ROI = (0.015, 0.015, 0.985, 0.255)
GENDER_ROI_WIDE = (0.005, 0.005, 0.995, 0.340)


def crop_frac(im, box):
    w, h = im.size
    return im.crop(tuple(int(v * (w if i % 2 == 0 else h)) for i, v in enumerate(box)))


def saturation(rgb):
    r, g, b = rgb
    hi, lo = max(rgb), min(rgb)
    return 0.0 if hi == 0 else (hi - lo) / hi


def filled_fraction(im, season):
    roi = crop_frac(im.convert("RGB"), SEASON_ROIS[season])
    w, h = roi.size
    if w < 4 or h < 4: return 0.0
    x0, x1 = max(1, int(w*.02)), max(2, int(w*.98))
    ys = range(max(1,int(h*.18)), max(2,int(h*.82)))
    active=[]
    for x in range(x0,x1):
        vals=[saturation(roi.getpixel((x,y)))>.10 for y in ys]
        active.append(sum(vals)/max(1,len(vals))>=.22)
    first=next((i for i,on in enumerate(active[:max(8,len(active)//4)]) if on),None)
    if first is None: return 0.0
    last, gap=first,0
    for i in range(first,len(active)):
        if active[i]: last,gap=i,0
        else:
            gap+=1
            if gap>8: break
    return min(1.0,(last+1)/max(1,len(active)))


def season_result(im):
    scores={s:filled_fraction(im,s) for s in SEASONS}
    ordered=sorted(scores.items(), key=lambda kv:kv[1], reverse=True)
    best,second=ordered[0],ordered[1]
    margin=best[1]-second[1]
    # Shobi rule: the numerically longest Fragrantica season bar ALWAYS wins.
    main=best[0]
    confidence="HIGH" if margin>=.10 else ("MEDIUM" if margin>.02 else "CLOSE")
    return scores,main,confidence,margin


def normalize_ocr(text):
    text=text.lower().replace("\n"," ")
    text=re.sub(r"[^a-z ]+"," ",text)
    return re.sub(r"\s+"," ",text).strip()


def parse_gender(t):
    # Conservative exact phrases first, then OCR-tolerant variants.
    if re.search(r"(?:for )?(?:women|woman)\s+(?:and|&|ancl|anci)\s+(?:men|man)",t) or re.search(r"(?:for )?(?:men|man)\s+(?:and|&|ancl|anci)\s+(?:women|woman)",t):
        return "unisex"
    if re.search(r"\bfor\s+wom[ae]n\b",t): return "female"
    if re.search(r"\bfor\s+m[ae]n\b",t): return "male"
    return ""


def ocr_variant(crop, scale, contrast, threshold=None):
    c=crop.convert("L")
    c=ImageOps.autocontrast(c)
    c=ImageEnhance.Contrast(c).enhance(contrast)
    c=c.resize((c.width*scale,c.height*scale),Image.Resampling.LANCZOS)
    c=c.filter(ImageFilter.SHARPEN)
    if threshold is not None:
        c=c.point(lambda p:255 if p>threshold else 0)
    return c


def gender_from_card(im):
    if pytesseract is None: return "","OCR_UNAVAILABLE",""
    attempts=[]
    specs=[
        (GENDER_ROI,2,2.2,None,(6,11)),
        (GENDER_ROI_WIDE,3,2.8,None,(6,11,12)),
        (GENDER_ROI_WIDE,3,2.5,170,(6,11)),
        (GENDER_ROI_WIDE,3,2.5,205,(6,11)),
    ]
    for box,scale,contrast,threshold,psms in specs:
        crop=ocr_variant(crop_frac(im,box),scale,contrast,threshold)
        for psm in psms:
            try:
                raw=pytesseract.image_to_string(crop,config=f"--psm {psm}",lang="eng")
            except Exception:
                continue
            t=normalize_ocr(raw)
            if t: attempts.append(t)
            gender=parse_gender(t)
            if gender: return gender,"SOCIAL_CARD_OCR",t
    return "","OCR_UNRESOLVED"," | ".join(dict.fromkeys(attempts))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--calibrate",action="store_true"); ap.add_argument("--limit",type=int,default=0); args=ap.parse_args()
    with MANIFEST.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    rows=[r for r in rows if r.get("card_status") in {"EXISTS","DOWNLOADED"} and r.get("local_path")]
    if args.limit: rows=rows[:args.limit]
    if args.calibrate:
        CROPS.mkdir(exist_ok=True)
        for r in rows[:24]:
            p=ROOT/r["local_path"]
            if not p.exists(): continue
            with Image.open(p) as im:
                crop_frac(im,(.39,.80,.94,.97)).save(CROPS/f'{r["fragrantica_id"]}_seasons.png')
                crop_frac(im,GENDER_ROI_WIDE).save(CROPS/f'{r["fragrantica_id"]}_title.png')
        print(f"calibration_crops={CROPS}"); return
    out=[]; genders={"male":0,"female":0,"unisex":0,"unresolved":0}; close=0
    for i,r in enumerate(rows,1):
        p=ROOT/r["local_path"]
        if not p.exists(): continue
        try:
            with Image.open(p) as im:
                scores,main_season,conf,margin=season_result(im)
                gender,gsource,ocr_text=gender_from_card(im)
            if conf=="CLOSE": close+=1
            genders[gender or "unresolved"]+=1
            out.append({"prestashop_product_id":r.get("prestashop_product_id",""),"shobi_code":r.get("shobi_code",""),"fragrantica_id":r.get("fragrantica_id",""),"gender":gender,"gender_source":gsource,"gender_ocr_text":ocr_text,"winter":f'{scores["winter"]:.4f}',"spring":f'{scores["spring"]:.4f}',"summer":f'{scores["summer"]:.4f}',"fall":f'{scores["fall"]:.4f}',"main_season":main_season,"season_confidence":conf,"season_margin":f"{margin:.4f}","local_path":r.get("local_path","")})
        except Exception as e: print(f"ERROR {p}: {e}")
        if i%250==0: print(f"processed={i}/{len(rows)}")
    fields=list(out[0]) if out else []
    with OUT.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)
    print(f"cards={len(rows)} extracted={len(out)} close_seasons={close} genders={genders} output={OUT}")

if __name__=="__main__": main()
