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

# Geometry derived from the archived 1200x1200 Fragrantica p_c social cards.
# winter | spring
# summer | fall/autumn
SEASON_ROIS = {
    "winter": (0.416, 0.835, 0.650, 0.885),
    "spring": (0.680, 0.835, 0.915, 0.885),
    "summer": (0.416, 0.900, 0.650, 0.950),
    "fall":   (0.680, 0.900, 0.915, 0.950),
}

# The title/subtitle lives in the upper portion. We OCR only this small area,
# never the full image, and only interpret explicit Fragrantica gender phrases.
GENDER_ROI = (0.015, 0.015, 0.985, 0.255)


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
    if w < 4 or h < 4:
        return 0.0
    x0 = max(1, int(w * 0.02))
    x1 = max(x0 + 1, int(w * 0.98))
    ys = range(max(1, int(h * 0.18)), max(2, int(h * 0.82)))
    active = []
    for x in range(x0, x1):
        vals = [saturation(roi.getpixel((x, y))) > 0.10 for y in ys]
        active.append((sum(vals) / max(1, len(vals))) >= 0.22)
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


def normalize_ocr(text):
    text = text.lower().replace("\n", " ")
    text = re.sub(r"[^a-z ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def gender_from_card(im):
    if pytesseract is None:
        return "", "OCR_UNAVAILABLE", ""
    crop = crop_frac(im, GENDER_ROI).convert("L")
    crop = ImageOps.autocontrast(crop)
    crop = ImageEnhance.Contrast(crop).enhance(2.2)
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
    crop = crop.filter(ImageFilter.SHARPEN)
    # Two OCR layouts cover single-line and multi-line card titles.
    texts = []
    for psm in (6, 11):
        try:
            texts.append(pytesseract.image_to_string(crop, config=f"--psm {psm}", lang="eng"))
        except Exception:
            pass
    raw = " ".join(texts)
    t = normalize_ocr(raw)
    # Unisex must be tested first because it contains both words.
    unisex_patterns = (
        r"for women and men", r"for men and women", r"women and men", r"men and women",
    )
    if any(re.search(p, t) for p in unisex_patterns):
        return "unisex", "SOCIAL_CARD_OCR", t
    if re.search(r"\bfor women\b", t) or re.search(r"\bfor woman\b", t):
        return "female", "SOCIAL_CARD_OCR", t
    if re.search(r"\bfor men\b", t) or re.search(r"\bfor man\b", t):
        return "male", "SOCIAL_CARD_OCR", t
    return "", "OCR_UNRESOLVED", t


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
                crop_frac(im, GENDER_ROI).save(CROPS / f'{r["fragrantica_id"]}_title.png')
        print(f"calibration_crops={CROPS}")
        return

    out = []
    ties = 0
    genders = {"male": 0, "female": 0, "unisex": 0, "unresolved": 0}
    for i, r in enumerate(rows, 1):
        p = ROOT / r["local_path"]
        if not p.exists():
            continue
        try:
            with Image.open(p) as im:
                scores, main_season, conf, margin = season_result(im)
                gender, gsource, ocr_text = gender_from_card(im)
            if main_season == "TIE":
                ties += 1
            genders[gender if gender else "unresolved"] += 1
            out.append({
                "prestashop_product_id": r.get("prestashop_product_id", ""),
                "shobi_code": r.get("shobi_code", ""),
                "fragrantica_id": r.get("fragrantica_id", ""),
                "gender": gender,
                "gender_source": gsource,
                "gender_ocr_text": ocr_text,
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
    print(f"cards={len(rows)} extracted={len(out)} ties={ties} genders={genders} output={OUT}")


if __name__ == "__main__":
    main()
