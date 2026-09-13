#!/usr/bin/env python3
"""Rebuild the website catalog from the current Shobi-only live CSV."""

import csv
import json
import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LIVE_CSV = ROOT / "shobi-perfumes-live-unique.csv"
MASTER = ROOT / "data/shobi-master-v1.csv"
MAPPING = ROOT / "data/shobi-fragrantica-mapping.csv"
IDENTITY_REVIEW = ROOT / "data/shobi-identity-review-2026-09-04.csv"
OLD_SITE = ROOT / "database_complete.json"
NOTES = ROOT / "social-card-main-notes-validated.json"
GENDER = ROOT / "social-card-gender.json"
GENDER_SEASON = ROOT / "fragrantica-scraper-archive/social-cards/gender-season.csv"
OUTPUT = ROOT / "database_complete.json"
SITE_OUTPUT = ROOT / "catalog_site.json"

# Corrections individually verified against the Shobi product identity and the
# corresponding perfume page. These override stale candidate matches in the
# historical mapping file until that large source file is regenerated.
CONFIRMED_IDENTITY_OVERRIDES = {
    "646-ARM": ("Giorgio Armani", "Armani Code for Women", "413", "https://www.fragrantica.com/perfume/Giorgio-Armani/Armani-Code-for-Women-413.html"),
    "716-ISS": ("Issey Miyake", "A Scent by Issey Miyake", "6432", "https://www.fragrantica.com/perfume/Issey-Miyake/A-Scent-by-Issey-Miyake-6432.html"),
    "847-NRO": ("Narciso Rodriguez", "Narciso Poudree", "36679", "https://www.fragrantica.com/perfume/Narciso-Rodriguez/Narciso-Poudree-36679.html"),
    "866-PAC": ("Rabanne", "Ultraviolet", "519", "https://www.fragrantica.com/perfume/Paco-Rabanne/Ultraviolet-519.html"),
    "1165-HUG": ("Hugo Boss", "Hugo Energise", "569", "https://www.fragrantica.com/perfume/Hugo-Boss/Hugo-Energise-569.html"),
    "1189-KEN": ("Kenzo", "Kenzo Homme Sport Extreme", "18174", "https://www.fragrantica.com/perfume/Kenzo/Kenzo-Homme-Sport-Extreme-18174.html"),
    "1281-YZLO": ("Yves Saint Laurent", "L'Homme Parfum Intense", "18841", "https://www.fragrantica.com/perfume/Yves-Saint-Laurent/L-Homme-Parfum-Intense-18841.html"),
    "1890-LEL": ("Le Labo", "Lys 41", "18382", "https://www.fragrantica.com/perfume/Le-Labo/Lys-41-18382.html"),
    "2265-KAY": ("Kayali Fragrances", "Oudgasm Rose Oud 16 Eau de Parfum Intense", "85186", "https://www.fragrantica.com/perfume/Kayali-Fragrances/Oudgasm-Rose-Oud-16-Eau-de-Parfum-Intense-85186.html"),
    "521-DRC": ("Dior", "Dior Addict", "215", "https://www.fragrantica.com/perfume/Dior/Dior-Addict-215.html"),
    "676-GUC": ("Gucci", "Flora by Gucci Eau de Toilette", "5226", "https://www.fragrantica.com/perfume/Gucci/Flora-by-Gucci-Eau-de-Toilette-5226.html"),
    "843-NRO": ("Narciso Rodriguez", "For Her", "209", "https://www.fragrantica.com/perfume/Narciso-Rodriguez/For-Her-209.html"),
}


BRAND_ALIASES = {
    "Abercrombie Fitch": "Abercrombie & Fitch",
    "Victoria s Secret": "Victoria's Secret",
    "Penhaligons": "Penhaligon's",
    "Penhaligon s": "Penhaligon's",
    "Estee Lauder": "Estée Lauder",
    "Kayali": "Kayali Fragrances",
    "mugler": "Mugler",
    "Frederic Malle": "Frédéric Malle",
    "Dolce&Gabbana": "Dolce & Gabbana",
    "Dolce Gabbana": "Dolce & Gabbana",
    "DSQUARED2": "Dsquared2",
    "DSQUARED²": "Dsquared2",
    "Dsquared²": "Dsquared2",
    "Marc Antoine Barrois": "Marc-Antoine Barrois",
    "Zadig  Voltaire": "Zadig & Voltaire",
    "Zadig Voltaire": "Zadig & Voltaire",
    "kylie-cosmetics": "Kylie Cosmetics",
    "Kylie Jenner": "Kylie Cosmetics",
    "maison-mataha": "Maison Mataha",
    "Lacoste": "Lacoste Fragrances",
    "guy laroche": "Guy Laroche",
    "Jo Malone": "Jo Malone London",
    "Kilian": "By Kilian",
    "Maison Margiela": "Maison Martin Margiela",
    "Roja Parfums": "Roja Dove",
    "Initio": "Initio Parfums Prives",
    "Stephane Humbert Lucas": "Stéphane Humbert Lucas 777",
    "Stéphane Humbert Lucas": "Stéphane Humbert Lucas 777",
    "liquides-imaginaires": "Les Liquides Imaginaires",
    "DKNY": "Donna Karan",
    "Goldfield & Banks": "Goldfield & Banks Australia",
    "Goldfield Banks Australia": "Goldfield & Banks Australia",
    "Sospiro": "Sospiro Perfumes",
    "Chabaud": "Chabaud Maison de Parfum",
    "Martine Micallef": "M. Micallef",
    "Tauer": "Tauer Perfumes",
    "Lancome": "Lancôme",
    "Hermes": "Hermès",
    "Viktor Rolf": "Viktor&Rolf",
    "Born to Stand Out": "BORNTOSTANDOUT",
    "Borntostandout": "BORNTOSTANDOUT",
    "borntostandout": "BORNTOSTANDOUT",
    "mind-games": "Mind Games",
    "bdk Parfums": "BDK Parfums",
    "matiere-premiere": "Matiere Premiere",
    "Ramon Monegal": "Ramón Monegal",
    "Courreges": "Courrèges",
    "Juliette Has A Gun": "Juliette Has a Gun",
    "memo-paris": "Memo Paris",
    "atelier-materi": "Atelier Materi",
    "boy-smells": "Boy Smells",
    "sabrina-carpenter": "Sabrina Carpenter",
    "lorenzo-pazzaglia": "Lorenzo Pazzaglia",
    "somens": "Somens",
    "paris-corner": "Paris Corner",
    "the-spirit-of-dubai": "The Spirit of Dubai",
    "zielinski-rozen": "Zielinski & Rozen",
    "dries-van-noten": "Dries Van Noten",
    "billie-eilish": "Billie Eilish",
    "casamorati": "Casamorati",
    "scent-salim": "Scent Salim",
    "parfums-delrae": "Parfums DelRae",
    "Zarko Perfume": "ZARKOPERFUME",
    "Comme des Garons": "Comme des Garçons",
    "Banderas": "Antonio Banderas",
    "Paco Rabanne": "Rabanne",
    "Baccarat": "Maison Francis Kurkdjian",
}


def canonical_brand(value):
    brand = " ".join(str(value or "").split())
    return BRAND_ALIASES.get(brand, brand)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean_code(value):
    value = str(value or "").strip()
    match = re.match(r"^(\d+)\s*-\s*([A-Za-z]+)", value)
    return f"{match.group(1)}-{match.group(2).upper()}" if match else value


def identity_from_fragrantica_url(url):
    match = re.search(r"/perfume/([^/]+)/(.+?)-(\d+)\.html", url or "")
    if not match:
        return "", ""
    brand = unquote(match.group(1)).replace("-", " ").strip()
    name = unquote(match.group(2)).replace("-", " ").strip()
    return brand, name


def identity_from_description(description):
    text = str(description or "").strip()
    text = re.sub(r"^\d+\s*-\s*[A-Za-z]+(?:\s+(?:W|WP|M|MP|N|AR|EL|Ν))?\s*", "", text)
    text = re.split(r"\.(?:\s|$)|\b(?:Dupe|Similar|Type|Perfume|Fragrance)\b", text, maxsplit=1, flags=re.I)[0]
    parts = [part.strip(" .") for part in text.rsplit(" - ", 1)]
    if len(parts) == 2 and all(parts):
        return parts[1], parts[0]
    return "Unknown Brand", text.strip(" .") or "Unidentified Shobi fragrance"


live_rows = read_csv(LIVE_CSV)
master_by_pid = {row["prestashop_product_id"].strip(): row for row in read_csv(MASTER)}
mapping_by_pid = {row["prestashop_product_id"].strip(): row for row in read_csv(MAPPING)}
review_by_pid = {
    row["prestashop_product_id"].strip(): row
    for row in read_csv(IDENTITY_REVIEW)
    if row.get("esito_revisione", "").strip().lower() == "match corretto"
    and row.get("marchio_abbinato", "").strip()
}
old_by_pid = {
    str(row.get("prestashopProductId") or "").strip(): row
    for row in json.loads(OLD_SITE.read_text(encoding="utf-8-sig"))
}

notes_by_code = {
    clean_code(row.get("code")): row
    for row in json.loads(NOTES.read_text(encoding="utf-8-sig"))
}
gender_by_code = {
    clean_code(row.get("code")): row
    for row in json.loads(GENDER.read_text(encoding="utf-8-sig"))
}
season_by_code = {clean_code(row.get("shobi_code")): row for row in read_csv(GENDER_SEASON)}

out = []
for live in live_rows:
    pid = live["product_id"].strip()
    canonical_code = clean_code(live["code"])
    master = master_by_pid[pid]
    mapping = mapping_by_pid[pid]
    old = old_by_pid.get(pid, {})
    review = review_by_pid.get(pid, {})

    url_brand, url_name = identity_from_fragrantica_url(mapping.get("fragrantica_url", ""))
    fallback_brand, fallback_name = identity_from_description(live.get("description_short", ""))
    override = CONFIRMED_IDENTITY_OVERRIDES.get(canonical_code)
    if override:
        brand, inspired_by, fragrantica_id, fragrantica_url = override
    else:
        brand = (
            review.get("marchio_abbinato")
            or mapping.get("original_brand")
            or old.get("brand")
            or url_brand
            or fallback_brand
        ).strip()
        inspired_by = (
            mapping.get("original_perfume")
            or old.get("inspiredBy")
            or url_name
            or master.get("inspired_by")
            or live.get("inspired_by")
            or fallback_name
        ).strip()
        fragrantica_id = mapping.get("fragrantica_id") or old.get("fragranticaId") or None
        fragrantica_url = mapping.get("fragrantica_url") or old.get("fragranticaUrl") or ""

    brand = canonical_brand(brand)
    row = dict(old)
    row.update({
        "id": f"pid:{pid}",
        "code": canonical_code,
        "liveDisplayCode": live["code"].strip(),
        "prestashopProductId": pid,
        "reference": live["reference"].strip(),
        "shobiUrl": live["url"].strip(),
        "shobiImageUrl": live["image_url"].strip(),
        "shobiCategory": live["category"].strip(),
        "shobiPriceEur": live["price_eur"].strip(),
        "brand": brand,
        "inspiredBy": inspired_by,
        "fragranticaId": fragrantica_id,
        "fragranticaUrl": fragrantica_url,
        "fragranticaStatus": mapping.get("fragrantica_status") or old.get("fragranticaStatus") or "NOT_FOUND",
        "identityStatus": mapping.get("identity_status") or "AMBIGUOUS",
        "masterVersion": "shobi-live-unique-2026-09-13-2332",
        "catalogSource": "shobi-perfumes-live-unique.csv",
    })

    note_entry = notes_by_code.get(canonical_code, {})
    gender_entry = gender_by_code.get(canonical_code, {})
    season_entry = season_by_code.get(canonical_code, {})
    social_gender = str(gender_entry.get("gender") or season_entry.get("gender") or "").lower()
    if not social_gender:
        description = live.get("description_short", "").lower()
        category = live.get("category", "").lower()
        if "women" in category or "women's perfume" in description:
            social_gender = "female"
        elif "men" in category or "men's perfume" in description:
            social_gender = "male"
        elif "unisex" in description:
            social_gender = "unisex"
    gender_affinity = {
        "male": "masculine",
        "female": "feminine",
        "unisex": "unisex",
    }.get(social_gender, str(row.get("genderAffinity") or "").lower())

    row["genderAffinity"] = gender_affinity
    row["gender"] = gender_entry.get("gender") or row.get("gender") or ""
    main_season = str(season_entry.get("main_season") or "").lower()
    row["seasons"] = row.get("seasons") or ([main_season] if main_season else [])
    row["occasions"] = row.get("occasions") or []
    row["mainAccords"] = row.get("mainAccords") or []
    row["notes"] = row.get("notes") or {"top": [], "heart": [], "base": []}
    row["fragranticaSocialCardNotes"] = row.get("fragranticaSocialCardNotes") or note_entry.get("mainNotes") or []
    out.append(row)

if len(out) != 2332:
    raise SystemExit(f"Expected 2332 live Shobi perfumes, found {len(out)}")
if len({row["prestashopProductId"] for row in out}) != len(out):
    raise SystemExit("Duplicate PrestaShop product ID")
if len({row["shobiUrl"] for row in out}) != len(out):
    raise SystemExit("Duplicate Shobi URL")
if any(not row["brand"] or not row["inspiredBy"] for row in out):
    raise SystemExit("Blank brand or perfume identity remains")
if any(row["brand"] != canonical_brand(row["brand"]) for row in out):
    raise SystemExit("Non-canonical brand label remains")
out_by_code = {row["code"]: row for row in out}
for code, (brand, name, fragrantica_id, fragrantica_url) in CONFIRMED_IDENTITY_OVERRIDES.items():
    row = out_by_code.get(code)
    actual = (row.get("brand"), row.get("inspiredBy"), str(row.get("fragranticaId")), row.get("fragranticaUrl"))
    expected = (brand, name, fragrantica_id, fragrantica_url)
    if actual != expected:
        raise SystemExit(f"Confirmed identity regression for {code}: {actual!r} != {expected!r}")

OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

site_required_fields = ("code", "inspiredBy", "brand")
site_optional_fields = (
    "genderAffinity",
    "seasons",
    "occasions",
    "mainAccords",
    "fragranticaSocialCardNotes",
    "userRatings",
)
site_rows = []
for row in out:
    site_row = {field: row[field] for field in site_required_fields}
    site_row.update({
        field: row[field]
        for field in site_optional_fields
        if row.get(field) not in (None, "", [], {})
    })
    site_rows.append(site_row)
if len(site_rows) != len(out):
    raise SystemExit("Site catalog row count differs from complete database")
SITE_OUTPUT.write_text(
    json.dumps(site_rows, ensure_ascii=False, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
print("rows", len(out))
print("old enrichments retained", sum(row["prestashopProductId"] in old_by_pid for row in out))
print("with main notes", sum(bool(row["fragranticaSocialCardNotes"]) for row in out))
print("with gender", sum(bool(row["genderAffinity"]) for row in out))
print("with season", sum(bool(row["seasons"]) for row in out))
print("confirmed Shobi review brands", sum(row["prestashopProductId"] in review_by_pid for row in out))
print("canonical brands", len({row["brand"] for row in out}))
print("site catalog bytes", SITE_OUTPUT.stat().st_size)
