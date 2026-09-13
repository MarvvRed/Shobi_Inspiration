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
OLD_SITE = ROOT / "database_complete.json"
NOTES = ROOT / "social-card-main-notes-validated.json"
GENDER = ROOT / "social-card-gender.json"
GENDER_SEASON = ROOT / "fragrantica-scraper-archive/social-cards/gender-season.csv"
OUTPUT = ROOT / "database_complete.json"


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

    url_brand, url_name = identity_from_fragrantica_url(mapping.get("fragrantica_url", ""))
    fallback_brand, fallback_name = identity_from_description(live.get("description_short", ""))
    brand = (mapping.get("original_brand") or old.get("brand") or url_brand or fallback_brand).strip()
    inspired_by = (
        mapping.get("original_perfume")
        or old.get("inspiredBy")
        or url_name
        or master.get("inspired_by")
        or live.get("inspired_by")
        or fallback_name
    ).strip()

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
        "fragranticaId": (mapping.get("fragrantica_id") or old.get("fragranticaId") or None),
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

OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("rows", len(out))
print("old enrichments retained", sum(row["prestashopProductId"] in old_by_pid for row in out))
print("with main notes", sum(bool(row["fragranticaSocialCardNotes"]) for row in out))
print("with gender", sum(bool(row["genderAffinity"]) for row in out))
print("with season", sum(bool(row["seasons"]) for row in out))
