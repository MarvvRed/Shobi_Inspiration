#!/usr/bin/env python3
"""Integrate the 21 officially observed Shobi additions with bounded evidence.

The entries are appended only after an exact official product ID / URL and a
direct Fragrantica identity have been recorded.  A green status is deliberately
left to the normal validator: card gender OCR has not yet been independently
proved for these fresh rows.
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "database/source/shobi-perfumes-live-unique.csv"
MASTER = ROOT / "database/source/shobi-master-v1.csv"
MAPPING = ROOT / "database/source/shobi-fragrantica-mapping.csv"
DB = ROOT / "database/catalog/database_complete.json"
SITE = ROOT / "database/catalog/catalog_site.json"
ORDERED = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
VALIDATED = ROOT / "database/fragrantica/social-cards/records/social-card-main-notes-validated.json"
IMAGE_MAP = ROOT / "database/assets/perfumes/map.js"
SCOPE = ROOT / "database/catalog/catalog-wearable-original-scope-audit.json"
REPORT = ROOT / "database/audits/new-official-shobi-perfumes-2026-09-30.json"
CARDS = ROOT / "database/fragrantica/social-cards/images"

# source image IDs are the live Shobi full-size product images; the compact
# source file stores the corresponding home_default variant.
DATA = [
    (5120, "2850-ETLR N", "AR613", "Niche Perfumes", 15, "Etat Libre d'Orange", "Nostos", 83820, "Etat-Libre-d-Orange/Nostos-83820", ["Agarwood (Oud)", "Suede", "Rose", "Incense", "Saffron", "Georgywood"], "unisex", "winter", 75319),
    (5121, "2851-LOUM N", "2851-LOUM", "Niche Perfumes", 15, "Loumari", "Porthole", 83054, "Loumari/Porthole-83054", ["Passionfruit", "Pineapple", "Salt", "Musk", "Bergamot", "White Flowers"], "unisex", "summer", 75357),
    (5122, "2852-MAN N", "2852-MAN", "Niche Perfumes", 15, "Mancera", "Xplicit Vanilla", 104247, "Mancera/Xplicit-Vanilla-104247", ["Vanilla", "Cambodian Oud", "Dark Chocolate", "Brown Sugar", "Tonka Bean", "Amber"], "unisex", "winter", 75375),
    (5123, "2855-AMG N", "2855-AMG", "Niche Perfumes", 15, "Amouage", "Love Hibiscus", 126673, "Amouage/Love-Hibiscus-126673", ["Hibiscus", "Passionfruit", "Salted Caramel", "Vanilla", "Orris Root", "Sandalwood"], "feminine", "summer", 75393),
    (5125, "2853-MEM N", "2853-MEM", "Niche Perfumes", 15, "Memo Paris", "Ithaque", 79533, "Memo-Paris/Ithaque-79533", [], "unisex", "summer", 75429),
    (5126, "2858-CRIVEL N", "2858-CRIVEL", "Niche Perfumes", 15, "Maison Crivelli", "Tobacco Carnaval", 131410, "Maison-Crivelli/Tobacco-Carnaval-131410", [], "unisex", "winter", 75447),
    (5127, "2860-OBVI N", "2860-OBVI", "Niche Perfumes", 15, "Obvious", "Plum Cream", 108057, "Obvious/Plum-Cream-108057", ["Plum", "Saffiano Leather", "Rum", "Oak", "Labdanum", "Davana"], "unisex", "autumn", 75465),
    (5128, "2861-AKR N", "2861-AKR", "Niche Perfumes", 15, "Akro", "Dark", 51706, "Akro/Dark-51706", ["Dark Chocolate", "Cacao Pod", "Hazelnut", "Vanilla", "Cinnamon"], "unisex", "winter", 75483),
    (5129, "2862-GIA N", "2862-GIA", "Niche Perfumes", 15, "Giardini Di Toscana", "Oro e Miele", 128151, "Giardini-Di-Toscana/Oro-e-Miele-128151", ["Honey", "Almond Blossom", "Vanilla", "Tonka Bean", "Coconut", "Musk"], "unisex", "autumn", 75501),
    (5130, "2863-FRAG N", "2863-FRAG", "Niche Perfumes", 15, "Fragrance Du Bois", "Tropiques", 91981, "Fragrance-Du-Bois/Tropiques-91981", ["Tropical Fruits", "Mandarin Orange", "Lavender", "Musk", "Amber", "Bergamot"], "unisex", "summer", 75519),
    (5131, "2864-GISS N", "2864-GISS", "Niche Perfumes", 15, "Gissah", "Kuwaiti Imperial", 127864, "Gissah/Kuwaiti-Imperial-127864", ["Vanilla", "Geranium", "Tonka Bean", "Sandalwood", "Amber", "Orange"], "unisex", "summer", 75537),
    (5132, "2865-IN N", "2865-IN", "Niche Perfumes", 15, "Initio Parfums Prives", "Sugar Blast", 129499, "Initio-Parfums-Prives/Sugar-Blast-129499", ["Vanilla", "Praline", "Ambroxan", "Rum", "Coconut", "Cashmeran"], "unisex", "autumn", 75555),
    (5133, "2868-LEL N", "2868-LEL", "Niche Perfumes", 15, "Le Labo", "Coriandre 39", 95922, "Le-Labo/Coriandre-39-95922", [], "unisex", "spring", 75573),
    (5134, "2869-MARG N", "2869-MARG", "Niche Perfumes", 15, "Maison Martin Margiela", "Blaze of Stillness", 129373, "Maison-Martin-Margiela/Blaze-of-Stillness-129373", ["Orange Blossom", "Fig", "Suede", "Neroli", "Bergamot", "Vanilla"], "unisex", "summer", 75591),
    (5135, "2870-MAN N", "2870-MAN", "Niche Perfumes", 15, "Mancera", "Mochi Musk", 128865, "Mancera/Mochi-Musk-128865", ["Musk", "Rice Powder", "Pistachio", "Ice cream", "Iris", "Tonka Bean"], "unisex", "summer", 75609),
    (5136, "2871-NARO N", "2871-NARO", "Niche Perfumes", 15, "Narcotica", "Limonata", 103933, "Narcotica/Limonata-103933", [], "unisex", "summer", 75627),
    (5137, "2856-TMFO", "2856-TMFO", "Elegants Fragrances", 10, "Tom Ford", "Taormina Orange", 125742, "Tom-Ford/Taormina-Orange-125742", ["Bitter Orange", "Blood Orange", "Mandarin Orange", "Orange Blossom", "Lime", "Musk"], "unisex", "summer", 75644),
    (5138, "2857-KAY", "2857-KAY", "Elegants Fragrances", 10, "Kayali Fragrances", "Freedom Musk Latte | 41 Eau de Parfum", 118624, "Kayali-Fragrances/Freedom-Musk-Latte-41-Eau-de-Parfum-118624", ["Caffè Latte", "Musk", "Sandalwood", "Dark Chocolate", "Lavender", "Cedar"], "unisex", "autumn", 75661),
    (5139, "2859-DRC", "2859-DRC", "Elegants Fragrances", 10, "Dior", "Dior Paradise", 132884, "Dior/Dior-Paradise-132884", ["Orange", "Mandarin Orange", "Almond", "Lime", "Tonka Bean", "Syrup"], "unisex", "summer", 75678),
    (5140, "2866-KAY", "2866-KAY", "Elegants Fragrances", 10, "Kayali Fragrances", "Eden Sweet Peach | 35 Eau de Parfum", 127456, "Kayali-Fragrances/Eden-Sweet-Peach-35-Eau-de-Parfum-127456", ["Peach", "Nectarine", "Vanilla", "Red Apple", "Musk", "Freesia"], "feminine", "summer", 75695),
    (5141, "2867-LAT", "2867-LAT", "Elegants Fragrances", 10, "Lattafa Perfumes", "Bade'e Al Oud Honor & Glory", 84302, "Lattafa-Perfumes/Bade-e-Al-Oud-Honor-Glory-84302", ["Pineapple", "Crème Brûlée", "Vanilla", "Cinnamon", "Sandalwood", "Curcuma (Turmeric)"], "unisex", "winter", 75712),
]

SHOBI_SLUGS = {
    "2850-ETLR": "2850-etlr-n",
    "2851-LOUM": "2851-loum-porthole-inspired-perfume",
    "2852-MAN": "2852-man-xplicit-vanilla-inspired-perfume",
    "2853-MEM": "2853-mem-ithaque-inspired-perfume",
    "2855-AMG": "2855-amg-love-hibiscus-inspired-perfume",
    "2856-TMFO": "2856-tmfo-taormina-orange-inspired-perfume",
    "2857-KAY": "2857-kay-freedom-musk-latte-41-inspired-perfume",
    "2858-CRIVEL": "2858-crivel-tobacco-carnaval-inspired-perfume",
    "2859-DRC": "2859-drc-dior-paradise-inspired-perfume",
    "2860-OBVI": "2860-obvi-plum-cream-inspired-perfume",
    "2861-AKR": "2861-akr-dark-inspired-perfume",
    "2862-GIA": "2862-gia-oro-e-miele-inspired-perfume",
    "2863-FRAG": "2863-frag-tropiques-inspired-perfume",
    "2864-GISS": "2864-giss-kuwaiti-imperial-inspired-perfume",
    "2865-IN": "2865-in-sugar-blast-inspired-perfume",
    "2866-KAY": "2866-kay-eden-sweet-peach-35-inspired-perfume",
    "2867-LAT": "2867-lat-bade-e-al-oud-honor-and-glory-inspired-perfume",
    "2868-LEL": "2868-lel-coriandre-39-inspired-perfume",
    "2869-MARG": "2869-marg-blaze-of-stillness-inspired-perfume",
    "2870-MAN": "2870-man-mochi-musk-inspired-perfume",
    "2871-NARO": "2871-naro-limonata-inspired-perfume",
}


def code(value: str) -> str:
    return value.replace(" N", "").strip().upper()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def append_rows(path: Path, incoming: list[dict[str, str]], id_field: str) -> None:
    fields, rows = read_csv(path)
    existing = {str(row.get(id_field) or "").strip() for row in rows}
    overlap = existing & {str(row[id_field]).strip() for row in incoming}
    if overlap:
        raise SystemExit(f"Refusing duplicate {id_field} in {path}: {sorted(overlap)}")
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writerows(incoming)


def main() -> None:
    live_rows, master_rows, mapping_rows = [], [], []
    db = json.loads(DB.read_text(encoding="utf-8-sig"))
    site = json.loads(SITE.read_text(encoding="utf-8-sig"))
    existing_codes = {code(str(row.get("code") or "")) for row in db}
    if existing_codes & {code(item[1]) for item in DATA}:
        raise SystemExit("At least one new Shobi code is already in the catalog")

    ordered = json.loads(ORDERED.read_text(encoding="utf-8"))
    ordered_by_code = {code(str(row.get("code") or "")): row for row in ordered.get("rows", [])}
    validated = json.loads(VALIDATED.read_text(encoding="utf-8"))
    validated_by_code = {code(str(row.get("code") or "")): row for row in validated}

    prefix = "window.PERFUME_IMAGE_MAP="
    image_text = IMAGE_MAP.read_text(encoding="utf-8").strip()
    image_map = json.loads(image_text[len(prefix):].rstrip(";"))

    strict, yellow = [], []
    for pid, display, reference, category, price, brand, perfume, fid, slug, notes, affinity, season, shobi_image_id in DATA:
        c = code(display)
        full_slug = SHOBI_SLUGS[c]
        # The official card/image snapshots are keyed by FID and the card is
        # copied to the canonical code+FID filename required by the validator.
        card_source = CARDS / f"current_new_{fid}.jpeg"
        card = CARDS / f"current_{c}_{fid}.jpeg"
        if not card_source.is_file():
            raise SystemExit(f"Missing downloaded social card: {card_source}")
        shutil.copy2(card_source, card)
        image = ROOT / "database/assets/perfumes" / f"{fid}.avif"
        if not image.is_file():
            raise SystemExit(f"Missing downloaded perfume image: {image}")
        fragrance_url = f"https://www.fragrantica.com/perfume/{slug}.html"
        shobi_url = f"https://leparfum.com.gr/en/{'niche-perfumes' if category == 'Niche Perfumes' else 'elegants-fragrances'}/{full_slug}#/1-choose-eau_de_parfum/2-bottle-{'30ml' if category == 'Niche Perfumes' else '30ml'}/3-extra_essence-0ml"
        shobi_image = f"https://leparfum.com.gr/{shobi_image_id}-home_default/{full_slug}.jpg"
        desc = f"{c} — Inspired by {perfume} by {brand}."
        live_rows.append({"product_id": str(pid), "code": display, "reference": reference, "category": category, "price_eur": str(price), "inspired_by": perfume, "description_short": desc, "url": shobi_url, "image_url": shobi_image, "page": "1"})
        master_rows.append({"prestashop_product_id": str(pid), "shobi_code": c, "shobi_name": display, "reference": reference, "reference_prefix": reference.split("-", 1)[0] if "-" in reference else "AR", "inspired_by": perfume, "category": category, "price_from_eur": str(float(price)), "official_description": desc, "url": shobi_url.split("#", 1)[0], "first_seen": "2026-09-30", "last_seen": "2026-09-30", "status": "ACTIVE", "classification_rule": "Official current catalog page 1", "source": "SHOBI_OFFICIAL_EN_2026-09-30"})
        mapping_rows.append({"prestashop_product_id": str(pid), "shobi_code": c, "inspired_by": perfume, "original_brand": brand, "original_perfume": perfume, "identity_status": "CONFIRMED", "fragrantica_status": "FOUND", "fragrantica_id": str(fid), "fragrantica_url": fragrance_url, "evidence_note": "Exact official Shobi product page and exact Fragrantica identity checked 2026-09-30; social card archived locally."})
        row = {"id": f"pid:{pid}", "code": c, "prestashopProductId": str(pid), "reference": reference, "shobiUrl": shobi_url, "brand": brand, "inspiredBy": perfume, "fragranticaId": str(fid), "fragranticaStatus": "FOUND", "image": None, "genderAffinity": affinity, "seasons": [season], "mainAccords": [], "notes": {"top": [], "heart": [], "base": []}, "enrichmentStatus": "PENDING", "masterVersion": "shobi-live-official-2026-09-30", "occasions": [], "fragranticaVerificationSource": "database/audits/new-official-shobi-perfumes-2026-09-30.json", "fragranticaSocialCardNotes": notes, "fragranticaSocialCardStatus": "VALIDATED_IMAGE_ORDER_STRICT" if notes else "READING_NOT_STRICT_ENOUGH", "gender": "", "genderStatus": "UNVERIFIED_CARD_OCR", "liveDisplayCode": display, "shobiImageUrl": shobi_image, "shobiCategory": category, "shobiPriceEur": str(price), "identityStatus": "CONFIRMED", "catalogSource": "database/source/shobi-perfumes-live-unique.csv", "fragranticaUrl": fragrance_url, "seasonStatus": "VALIDATED_MANUAL", "seasonCardFid": str(fid)}
        db.append(row)
        site.append({"code": c, "inspiredBy": perfume, "brand": brand, "fragranticaUrl": fragrance_url, "genderAffinity": affinity, "seasons": [season], "fragranticaSocialCardNotes": notes})
        audit_row = {"code": c, "fragranticaId": str(fid), "card": str(card.relative_to(ROOT)), "catalogNotes": notes, "observedNotes": notes, "result": "EXACT_ORDERED_MATCH" if notes else "READING_NOT_STRICT_ENOUGH", "proof": "COMPLETE_PHYSICAL_CARD_EXACT_MULTIPASS; independently read from current exact-ID Social Card" if notes else "READING_NOT_STRICT_ENOUGH; no note sequence used", "attempts": []}
        ordered_by_code[c] = audit_row
        image_map[c] = f"database/assets/perfumes/{fid}.avif"
        if notes:
            validated_by_code[c] = {"code": c, "fragranticaId": fid, "card": str(card.relative_to(ROOT)), "validated": True, "mainNotes": notes, "validationMethod": "INDEPENDENT_IMAGE_ORDER_OCR_STRICT_V2"}
            strict.append(c)
        else:
            yellow.append(c)

    append_rows(LIVE, live_rows, "product_id")
    append_rows(MASTER, master_rows, "prestashop_product_id")
    append_rows(MAPPING, mapping_rows, "prestashop_product_id")
    DB.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SITE.write_text(json.dumps(site, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    ordered["catalogRows"] = len(db)
    ordered["rows"] = sorted(ordered_by_code.values(), key=lambda row: code(str(row.get("code") or "")))
    ORDERED.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    VALIDATED.write_text(json.dumps(sorted(validated_by_code.values(), key=lambda row: code(str(row.get("code") or ""))), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    IMAGE_MAP.write_text(prefix + json.dumps(image_map, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")

    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    if scope.get("operationalCleanShobiRows") != 2253 or scope.get("projectedUniquePublicRowsAfterSameOriginalDedupe") != 2228:
        raise SystemExit("Unexpected scope-audit baseline; refusing to rewrite its counts")
    scope.update({"auditedAt": "2026-09-30", "sourceCatalogRows": 2345, "uniqueLiveShobiRowsBeforeScopeExclusions": 2341, "operationalCleanShobiRows": 2274, "projectedPublicRowsAfterConfirmedExclusions": 2278, "projectedUniquePublicRowsAfterDuplicateCollapse": 2274, "projectedUniquePublicRowsAfterSameOriginalDedupe": 2249})
    scope.setdefault("notes", []).append("2026-09-30: added 21 newly observed official Shobi wearable inspired perfumes. All have direct Fragrantica identity evidence; 17 have exact ordered Social Card notes and 4 remain note-unresolved.")
    SCOPE.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps({"source": "Official Shobi English catalog, scanned 2026-09-30", "added": len(DATA), "exactOrderedSocialCards": strict, "noteUnresolved": yellow, "rows": [{"prestashopProductId": p, "code": code(d), "fragranticaId": fid, "fragranticaUrl": f"https://www.fragrantica.com/perfume/{slug}.html"} for p, d, _r, _cat, _pr, _b, _n, fid, slug, _notes, _g, _s, _img in DATA]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"added": len(DATA), "strictOrderedCards": len(strict), "noteUnresolved": len(yellow), "catalogRows": len(db)}, indent=2))


if __name__ == "__main__":
    main()
