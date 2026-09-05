#!/usr/bin/env python3
from __future__ import annotations
import csv
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOCIAL = ROOT / "fragrantica-scraper-archive" / "social-cards"
MANIFEST = SOCIAL / "manifest.csv"
OUT = SOCIAL / "season-bar-diagnostics.csv"


def sat(rgb):
    r,g,b=rgb
    hi=max(rgb); lo=min(rgb)
    return 0.0 if hi==0 else (hi-lo)/hi


def runs_for_image(im: Image.Image):
    im=im.convert("RGB")
    w,h=im.size
    rows=[]
    # Scan lower 65% of card. For each y band, find contiguous x runs where
    # a strong majority of pixels are saturated enough to be a colored vote bar.
    for y0 in range(int(h*0.30), int(h*0.98), max(2,h//220)):
        y1=min(h,y0+max(3,h//120))
        active=[]
        for x in range(int(w*0.10), int(w*0.98)):
            vals=[sat(im.getpixel((x,y))) for y in range(y0,y1)]
            active.append(sum(v>0.20 for v in vals) >= max(2,int(len(vals)*0.60)))
        start=None
        for i,on in enumerate(active+[False]):
            if on and start is None: start=i
            elif not on and start is not None:
                ln=i-start
                if ln >= max(8,int(w*0.025)):
                    x0=int(w*0.10)+start; x1=int(w*0.10)+i
                    rows.append((y0,y1,x0,x1,ln))
                start=None
    # Merge nearby detections that refer to same horizontal bar.
    rows=sorted(rows,key=lambda r:(r[0],r[2],-r[4]))
    merged=[]
    for r in rows:
        cy=(r[0]+r[1])//2
        found=False
        for j,m in enumerate(merged):
            mcy=(m[0]+m[1])//2
            if abs(cy-mcy)<=max(5,h//80) and abs(r[2]-m[2])<=max(10,w//40):
                if r[4]>m[4]: merged[j]=r
                found=True; break
        if not found: merged.append(r)
    merged=sorted(merged,key=lambda r:(-r[4],r[0]))[:16]
    return merged


def main():
    with MANIFEST.open(encoding="utf-8-sig",newline="") as f:
        rows=[r for r in csv.DictReader(f) if r.get("card_status") in {"EXISTS","DOWNLOADED"} and r.get("local_path")][:24]
    out=[]
    for r in rows:
        p=ROOT/r["local_path"]
        if not p.exists(): continue
        with Image.open(p) as im:
            w,h=im.size
            runs=runs_for_image(im)
        for rank,(y0,y1,x0,x1,ln) in enumerate(runs,1):
            out.append({
                "fragrantica_id":r.get("fragrantica_id",""),"rank":rank,
                "x0":x0,"x1":x1,"y0":y0,"y1":y1,"length":ln,
                "x0_frac":f"{x0/w:.4f}","x1_frac":f"{x1/w:.4f}",
                "y_mid_frac":f"{((y0+y1)/2)/h:.4f}","length_frac":f"{ln/w:.4f}"
            })
    fields=list(out[0]) if out else ["fragrantica_id","rank","x0","x1","y0","y1","length","x0_frac","x1_frac","y_mid_frac","length_frac"]
    with OUT.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)
    print(f"diagnostic_cards={len(rows)} candidate_runs={len(out)} output={OUT}")

if __name__=="__main__": main()
