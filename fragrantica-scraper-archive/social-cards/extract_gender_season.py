#!/usr/bin/env python3
"""Extract gender and dominant season from archived Fragrantica social cards."""
from __future__ import annotations
import argparse, csv
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOCIAL = ROOT / "fragrantica-scraper-archive" / "social-cards"
MANIFEST = SOCIAL / "manifest.csv"
OUT = SOCIAL / "gender-season.csv"
CROPS = SOCIAL / "calibration-crops"
SEASONS = ("winter", "spring", "summer", "fall")

# Geometry derived from the archived 1200x1200 Fragrantica p_c social cards.
# The seasons panel is a 2x2 grid near the bottom:
# winter | spring
# summer | fall/autumn
SEASON_ROIS = {
    "winter": (0.416, 0.835, 0.650, 0.885),
    "spring": (0.680, 0.835, 0.915, 0.885),
    "summer": (0.416, 0.900, 0.650, 0.950),
    "fall":   (0.680, 0.900, 0.915, 0.950),
}


def crop_frac(im, box):
    w, h = im.size
    return im.crop(tuple(int(v * (w if i % 2 == 0 else h)) for i, v in enumerate(box)))


def saturation(rgb):
    r, g, b = rgb
    hi, lo = max(rgb), min(rgb)
    return 0.0 if hi == 0 else (hi - lo) / hi


def filled_fraction(im, season):
    """Estimate colored fill length inside one season vote bar.

    The unfilled remainder is gray/low-saturation. The colored vote fill is contiguous
    from the left edge. We score each x-column by the fraction of interior pixels with
    visible saturation, which is robust to the icon/text drawn on top of the bar.
    """
    roi = crop_frac(im.convert("RGB"), SEASON_ROIS[season])
    w, h = roi.size
    if w < 4 or h < 4:
        return 0.0
    x0 = max(1, int(w * 0.02))
    x1 = max(x0 + 1, int(w * 0.98))
    ys = range(max(1, int(h * 0.18)), max(2, int(h * 0.82)))
    active = []
    for x in range(x0, x1):
        vals = [saturation(roi.getpixel((x, y))) > 0.10 for y in ys]
        active.append((sum(vals) / max(1, len(vals))) >= 0.22)

    # Find colored fill contiguous from the beginning; tolerate small text/AA gaps.
    first = next((i for i, on in enumerate(active[:max(8, len(active)//4)]) if on), None)
    if first is None:
        return 0.0
    last = first
    gap = 0
    for i in range(first, len(active)):
        if active[i]:
            last = i
            gap = 0
        else:
            gap += 1
            if gap > 8:
                break
    return min(1.0, (last + 1) / max(1, len(active)))


def season_result(im):
    scores = {s: filled_fraction(im, s) for s in SEASONS}
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best, second = ordered[0], ordered[1]
    margin = best[1] - second[1]
    main = "TIE" if margin <= 0.02 else best[0]
    confidence = "HIGH" if margin >= 0.10 else ("MEDIUM" if margin > 0.02 else "TIE")
    return scores, main, confidence, margin


def gender_from_mapping(row):
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
    if args.limit:
        rows = rows[:args.limit]
    if args.calibrate:
        CROPS.mkdir(exist_ok=True)
        for r in rows[:24]:
            p = ROOT / r["local_path"]
            if not p.exists():
                continue
            with Image.open(p) as im:
                crop_frac(im, (0.39, 0.80, 0.94, 0.97)).save(CROPS / f'{r["fragrantica_id"]}_seasons.png')
                crop_frac(im, (0.02, 0.02, 0.48, 0.15)).save(CROPS / f'{r["fragrantica_id"]}_title.png')
        print(f"calibration_crops={CROPS}")
        return

    out = []
    ties = 0
    for i, r in enumerate(rows, 1):
        p = ROOT / r["local_path"]
        if not p.exists():
            continue
        try:
            with Image.open(p) as im:
                scores, main_season, conf, margin = season_result(im)
            gender, gsource = gender_from_mapping(r)
            if main_season == "TIE":
                ties += 1
            out.append({
                "prestashop_product_id": r.get("prestashop_product_id", ""),
                "shobi_code": r.get("shobi_code", ""),
                "fragrantica_id": r.get("fragrantica_id", ""),
                "gender": gender,
                "gender_source": gsource,
                "winter": f'{scores["winter"]:.4f}',
                "spring": f'{scores["spring"]:.4f}',
                "summer": f'{scores["summer"]:.4f}',
                "fall": f'{scores["fall"]:.4f}',
                "main_season": main_season,
                "season_confidence": conf,
                "season_margin": f"{margin:.4f}",
                "local_path": r.get("local_path", ""),
            })
        except Exception as e:
            print(f"ERROR {p}: {e}")
        if i % 250 == 0:
            print(f"processed={i}/{len(rows)}")

    fields = list(out[0]) if out else []
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"cards={len(rows)} extracted={len(out)} ties={ties} output={OUT}")


if __name__ == "__main__":
    main()
