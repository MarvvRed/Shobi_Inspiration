#!/usr/bin/env python3
"""Extract gender and dominant season from archived Fragrantica social cards.

The extractor deliberately avoids OCR. Gender is read from the stable subtitle area
using simple image-template classification once templates are calibrated; season is
measured from the four colored vote bars in the lower-right season panel. The longest
filled season bar wins. Exact/near ties are kept as TIE instead of guessed.

Run with --calibrate first to generate crops for a small sample. After crop geometry is
verified, run normally to produce gender-season.csv.
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[2]
SOCIAL = ROOT / "fragrantica-scraper-archive" / "social-cards"
MANIFEST = SOCIAL / "manifest.csv"
OUT = SOCIAL / "gender-season.csv"
CROPS = SOCIAL / "calibration-crops"
SEASONS = ("winter", "spring", "summer", "fall")

# Fragrantica social cards are square; coordinates are fractions of width/height.
# Season bars occupy the bottom-right panel in a 2x2 grid.
SEASON_ROIS = {
    "winter": (0.505, 0.790, 0.745, 0.850),
    "spring": (0.755, 0.790, 0.985, 0.850),
    "summer": (0.505, 0.855, 0.745, 0.920),
    "fall":   (0.755, 0.855, 0.985, 0.920),
}


def crop_frac(im, box):
    w, h = im.size
    return im.crop(tuple(int(v * (w if i % 2 == 0 else h)) for i, v in enumerate(box)))


def saturation(rgb):
    r, g, b = rgb
    hi, lo = max(rgb), min(rgb)
    return 0.0 if hi == 0 else (hi - lo) / hi


def filled_fraction(im, season):
    """Estimate colored fill length. Gray remainder has low saturation; fill is colored."""
    roi = crop_frac(im.convert("RGB"), SEASON_ROIS[season])
    w, h = roi.size
    # Ignore label/icon area at left and borders; score columns by median saturation.
    start = max(1, int(w * 0.12))
    ys = range(max(1, int(h * .20)), max(2, int(h * .80)))
    active = []
    for x in range(start, w):
        sats = sorted(saturation(roi.getpixel((x, y))) for y in ys)
        med = sats[len(sats)//2] if sats else 0
        active.append(med > 0.12)
    # Filled area is contiguous from left. Permit tiny antialiasing gaps.
    last = -1; gap = 0
    for i, on in enumerate(active):
        if on:
            last = i; gap = 0
        elif last >= 0:
            gap += 1
            if gap > 3:
                break
    return 0.0 if last < 0 else (last + 1) / max(1, len(active))


def season_result(im):
    scores = {s: filled_fraction(im, s) for s in SEASONS}
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best, second = ordered[0], ordered[1]
    margin = best[1] - second[1]
    # <=2 percentage points is treated as a visual tie, never guessed.
    main = "TIE" if margin <= .02 else best[0]
    confidence = "HIGH" if margin >= .10 else ("MEDIUM" if margin > .02 else "TIE")
    return scores, main, confidence, margin


def gender_from_mapping(row):
    # The card title itself contains e.g. "for women", "for men", "for women and men".
    # Until a robust image-text classifier is calibrated, preserve any already-known
    # site gender and mark missing values for a separate pass rather than hallucinating.
    for key in ("gender", "sex"):
        v = (row.get(key) or "").strip().lower()
        if v:
            if v in {"unisex", "women and men", "for women and men"}: return "unisex", "MAPPING"
            if v in {"female", "women", "woman", "for women"}: return "female", "MAPPING"
            if v in {"male", "men", "man", "for men"}: return "male", "MAPPING"
    return "", "NEEDS_CARD_TITLE_EXTRACTION"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    with MANIFEST.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if r.get("card_status") in {"EXISTS", "DOWNLOADED"} and r.get("local_path")]
    if args.limit: rows = rows[:args.limit]
    if args.calibrate:
        CROPS.mkdir(exist_ok=True)
        for r in rows[:24]:
            p = ROOT / r["local_path"]
            if not p.exists(): continue
            with Image.open(p) as im:
                crop_frac(im, (0.47, 0.73, 0.995, 0.94)).save(CROPS / f'{r["fragrantica_id"]}_seasons.png')
                crop_frac(im, (0.02, 0.02, 0.48, 0.15)).save(CROPS / f'{r["fragrantica_id"]}_title.png')
        print(f"calibration_crops={CROPS}")
        return
    out=[]; ties=0
    for i,r in enumerate(rows,1):
        p=ROOT/r["local_path"]
        if not p.exists(): continue
        try:
            with Image.open(p) as im:
                scores, main_season, conf, margin = season_result(im)
            gender,gsource=gender_from_mapping(r)
            if main_season=="TIE": ties+=1
            out.append({
                "prestashop_product_id":r.get("prestashop_product_id",""),
                "shobi_code":r.get("shobi_code",""),
                "fragrantica_id":r.get("fragrantica_id",""),
                "gender":gender,"gender_source":gsource,
                "winter":f'{scores["winter"]:.4f}',"spring":f'{scores["spring"]:.4f}',
                "summer":f'{scores["summer"]:.4f}',"fall":f'{scores["fall"]:.4f}',
                "main_season":main_season,"season_confidence":conf,"season_margin":f"{margin:.4f}",
                "local_path":r.get("local_path","")})
        except Exception as e:
            print(f"ERROR {p}: {e}")
        if i%250==0: print(f"processed={i}/{len(rows)}")
    fields=list(out[0]) if out else []
    with OUT.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)
    print(f"cards={len(rows)} extracted={len(out)} ties={ties} output={OUT}")

if __name__=="__main__": main()
