#!/usr/bin/env python3
"""Integrate four exact, manually cross-checked Shobi/Fragrantica records."""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "database/source/shobi-perfumes-live-unique.csv"
MASTER = ROOT / "database/source/shobi-master-v1.csv"
MAPPING = ROOT / "database/source/shobi-fragrantica-mapping.csv"
DB_PATH = ROOT / "database/catalog/database_complete.json"
SITE_PATH = ROOT / "database/catalog/catalog_site.json"
SCOPE_PATH = ROOT / "database/catalog/catalog-wearable-original-scope-audit.json"
ORDERED_PATH = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
VALIDATED_PATH = ROOT / "database/fragrantica/social-cards/records/social-card-main-notes-validated.json"
MANIFEST_PATH = ROOT / "database/fragrantica/social-cards/manifest.csv"
CANDIDATE_MANIFEST = ROOT / "database/audits/pending-shobi-social-card-manifest-2026-10-19.csv"
AUDIT_PATH = ROOT / "database/audits/pending-shobi-additions-2026-10-19.json"
ID_AUDIT_PATH = ROOT / "database/audits/recovered-shobi-product-ids-2026-10-19.json"
PROOF_PATH = ROOT / "database/audits/verified-shobi-additions-2026-10-19.json"
RECENT_PATH = ROOT / "database/catalog/recent-additions.json"
YELLOW_PATH = ROOT / "database/audits/current-yellow-breakdown.json"
OFFICIAL_DB_PATH = ROOT / "OFFICIAL_DATABASE.md"
HANDOFF_PATH = ROOT / "AI_HANDOFF.md"
PERFUME_MAP_PATH = ROOT / "database/assets/perfumes/map.js"
ICON_MAP_PATH = ROOT / "database/assets/note-icons/map.js"
CARD_DIR = ROOT / "database/fragrantica/social-cards/images"
PRODUCT_IMG_DIR = ROOT / "database/assets/perfumes"

ALL_CHECKS = {k: True for k in (
    "shobiProduct", "shobiIdentity", "identity", "fid", "url", "socialCard",
    "image", "notes", "icons", "gender", "season"
)}

CANDIDATES = [
    {
        "code": "2854-RIH", "display": "2854-RIH W", "product_id": "5224", "reference": "2854-RIH",
        "category": "Fragrances For Women", "price": 9.0, "inspired_by_source": "REBL FLEUR",
        "brand": "Rihanna", "perfume": "Reb'l Fleur", "fid": "10554",
        "fragrantica_url": "https://www.fragrantica.com/perfume/Rihanna/Reb-l-Fleur-10554.html",
        "shobi_url": "https://leparfum.com.gr/en/fragrances-for-women/2854-rih-inspired-reb-l-fleur",
        "shobi_image": "https://leparfum.com.gr/78224-home_default/2854-rih-inspired-reb-l-fleur.jpg",
        "description": "2854-RIH — Inspired by Reb'l Fleur. Juicy fruit meets coconut and flowers, resting on a warm vanilla, patchouli and musk base.",
        "notes": ["Coconut", "Vanilla", "Peach", "Patchouli", "Plum", "Red Berries"],
        "accords": ["fruity", "sweet", "vanilla", "coconut", "powdery"],
        "gender": "Female", "affinity": "feminine", "season": "fall", "season_label": "Autumn",
        "gender_label": "for women", "season_observation": "Autumn bar is visibly the longest of the four seasonal bars.",
        "image_id": 78224
    },
    {
        "code": "2877-VIC", "display": "2877-VIC MP", "product_id": "5225", "reference": "2877-VIC",
        "category": "Fragrances For Men", "price": 9.0, "inspired_by_source": "SPICEBOMB INFRARED",
        "brand": "Viktor&Rolf", "perfume": "Spicebomb Infrared", "fid": "66514",
        "fragrantica_url": "https://www.fragrantica.com/perfume/Viktor-Rolf/Spicebomb-Infrared-66514.html",
        "shobi_url": "https://leparfum.com.gr/en/fragrances-for-men/2877-vic-inspired-spicebomb-infrared",
        "shobi_image": "https://leparfum.com.gr/78225-home_default/2877-vic-inspired-spicebomb-infrared.jpg",
        "description": "2877-VIC — Inspired by Spicebomb Infrared. Red fruits and pepper meet cinnamon, with tobacco and benzoin adding a warm finish.",
        "notes": ["Cinnamon", "Red Fruits", "Pink Pepper", "Tobacco", "Pimento", "Benzoin"],
        "accords": ["warm spicy", "cinnamon", "tobacco", "sweet", "fruity"],
        "gender": "Male", "affinity": "masculine", "season": "winter", "season_label": "Winter",
        "gender_label": "for men",
        "season_observation": "Winter bar is visibly the longest of the four seasonal bars. FID 66514 is Spicebomb Infrared EDT (2021); do not substitute later EDP FID 81409.",
        "image_id": 78225
    },
    {
        "code": "2878-MAN", "display": "2878-MAN", "product_id": "5226", "reference": "2878-MAN",
        "category": "Elegants Fragrances", "price": 10.0, "inspired_by_source": "FIG ME UP",
        "brand": "Mancera", "perfume": "Fig Me Up", "fid": "98362",
        "fragrantica_url": "https://www.fragrantica.com/perfume/Mancera/Fig-Me-Up-98362.html",
        "shobi_url": "https://leparfum.com.gr/en/elegants-fragrances/2878-man-inspired-fig-me-up",
        "shobi_image": "https://leparfum.com.gr/78226-home_default/2878-man-inspired-fig-me-up.jpg",
        "description": "2878-MAN — Inspired by Fig Me Up. Green fig leaves and violet meet creamy fig, plum and woods, with a soft tobacco and toffee finish.",
        "notes": ["Fig", "Plum", "Rhubarb", "Tobacco", "Fig Leaf", "Agarwood (Oud)"],
        "accords": ["fruity", "sweet", "green", "woody", "aromatic"],
        "gender": "Unisex", "affinity": "unisex", "season": "spring", "season_label": "Spring",
        "gender_label": "for women and men",
        "season_observation": "Spring bar is visibly the longest of the four seasonal bars.",
        "image_id": 78226
    },
    {
        "code": "2879-KAY", "display": "2879-KAY", "product_id": "5227", "reference": "2879-KAY",
        "category": "Elegants Fragrances", "price": 10.0, "inspired_by_source": "FREEDOM MUSK MATCHA 45",
        "brand": "Kayali Fragrances", "perfume": "Freedom Musk Matcha | 45 Eau de Parfum", "fid": "118623",
        "fragrantica_url": "https://www.fragrantica.com/perfume/Kayali-Fragrances/Freedom-Musk-Matcha-45-118623.html",
        "shobi_url": "https://leparfum.com.gr/en/elegants-fragrances/2879-kay-inspired-freedom-musk-matcha-45",
        "shobi_image": "https://leparfum.com.gr/78227-home_default/2879-kay-inspired-freedom-musk-matcha-45.jpg",
        "description": "2879-KAY — Inspired by Freedom Musk Matcha | 45. Matcha and green apple meet creamy oat milk, vanilla and praline, over soft musk and sandalwood.",
        "notes": ["Matcha Tea", "Oat", "Milk", "Musk", "Mate", "Vanilla"],
        "accords": ["powdery", "lactonic", "green", "musky", "savory"],
        "gender": "Unisex", "affinity": "unisex", "season": "fall", "season_label": "Autumn",
        "gender_label": "for women and men",
        "season_observation": "Autumn bar is visibly slightly longer than the Spring bar.",
        "image_id": 78227
    }
]

def norm_code(v):
    return str(v or "").strip().upper()

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def write_json(path, obj, pretty=True):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2 if pretty else None,
                                     separators=None if pretty else (",", ":")) + "\n", encoding="utf-8")

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def append_csv(path, incoming, id_field, unique_fields=()):
    fields, rows = read_csv(path)
    ids = {str(r.get(id_field) or "").strip() for r in rows}
    overlap = ids & {str(r.get(id_field) or "").strip() for r in incoming}
    if overlap:
        raise SystemExit(f"Refusing duplicate {id_field} in {path}: {sorted(overlap)}")
    for key in unique_fields:
        existing = {norm_code(r.get(key)) for r in rows}
        incoming_values = {norm_code(r.get(key)) for r in incoming}
        dup = existing & incoming_values
        if dup:
            raise SystemExit(f"Refusing duplicate {key} in {path}: {sorted(dup)}")
    with Path(path).open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writerows(incoming)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-manifest", required=True, type=Path)
    args = parser.parse_args()
    today = "2026-10-19"

    db = read_json(DB_PATH)
    site = read_json(SITE_PATH)
    existing_codes = {norm_code(r.get("code")) for r in db}
    existing_ids = {str(r.get("prestashopProductId") or "").strip() for r in db}
    existing_fids = {str(r.get("fragranticaId") or "").strip() for r in db if r.get("fragranticaId")}
    for c in CANDIDATES:
        if c["code"] in existing_codes:
            raise SystemExit(f"{c['code']} already exists in database_complete; refusing duplicate")
        if c["product_id"] in existing_ids:
            raise SystemExit(f"PrestaShop ID {c['product_id']} already exists; refusing duplicate")
        if c["fid"] in existing_fids:
            raise SystemExit(f"FID {c['fid']} already exists; require manual duplicate-original review")
    if len(db) != len(site):
        raise SystemExit(f"database_complete/catalog_site mismatch: {len(db)} != {len(site)}")
    if not args.base_manifest.is_file():
        raise SystemExit("Original full social-card manifest backup missing")

    _, candidate_rows = read_csv(CANDIDATE_MANIFEST)
    candidate_by_code = {norm_code(r.get("shobi_code")): r for r in candidate_rows}
    if set(candidate_by_code) != {c["code"] for c in CANDIDATES}:
        raise SystemExit(f"Candidate manifest code mismatch: {sorted(candidate_by_code)}")

    icon_text = ICON_MAP_PATH.read_text(encoding="utf-8")
    icon_prefix = "window.FRAGRANTICA_NOTE_ICON_MAP="
    if not icon_text.startswith(icon_prefix):
        raise SystemExit("Unexpected note icon map format")
    icon_map = json.loads(icon_text[len(icon_prefix):].strip().rstrip(";"))
    for c in CANDIDATES:
        for note in c["notes"]:
            icon = icon_map.get(note.casefold())
            if not icon or not (ROOT / icon).is_file():
                raise SystemExit(f"{c['code']}: local note icon missing/unmapped for {note}")

    perfume_map_text = PERFUME_MAP_PATH.read_text(encoding="utf-8").strip()
    map_prefix = "window.PERFUME_IMAGE_MAP="
    if not perfume_map_text.startswith(map_prefix):
        raise SystemExit("Unexpected perfume image map format")
    perfume_map = json.loads(perfume_map_text[len(map_prefix):].rstrip(";"))

    CARD_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCT_IMG_DIR.mkdir(parents=True, exist_ok=True)
    source_rows, master_rows, mapping_rows, db_rows, site_rows, proof_rows, manifest_additions = [], [], [], [], [], [], []
    card_paths = {}

    for c in CANDIDATES:
        m = candidate_by_code[c["code"]]
        if (str(m.get("prestashop_product_id") or "").strip() != c["product_id"]
            or str(m.get("fragrantica_id") or "").strip() != c["fid"]
            or m.get("identity_status") != "CONFIRMED" or m.get("fragrantica_status") != "FOUND"
            or m.get("card_status") != "DOWNLOADED" or str(m.get("error") or "").strip()):
            raise SystemExit(f"{c['code']}: downloader manifest incomplete/contradictory: {m}")
        downloaded = ROOT / str(m.get("local_path") or "")
        if not downloaded.is_file():
            raise SystemExit(f"{c['code']}: downloaded exact-FID Social Card missing: {downloaded}")
        try:
            check = Image.open(downloaded)
            check.verify()
            im = Image.open(downloaded).convert("RGB")
        except Exception as exc:
            raise SystemExit(f"{c['code']}: invalid downloaded image: {exc}")
        if im.size != (1200, 1200):
            raise SystemExit(f"{c['code']}: Social Card must be 1200x1200, got {im.size}")

        card_rel = f"database/fragrantica/social-cards/images/current_{c['code']}_{c['fid']}.jpeg"
        card_path = ROOT / card_rel
        shutil.copy2(downloaded, card_path)
        card_hash = digest(card_path)
        if card_hash != str(m.get("sha256") or "").strip():
            raise SystemExit(f"{c['code']}: card hash mismatch")
        card_paths[c["code"]] = card_rel

        # This bottle-only image is cropped from the exact same Fragrantica ID card.
        product_img = PRODUCT_IMG_DIR / f"{c['fid']}.jpg"
        crop_bottom = 680 if c["fid"] == "118623" else 650
        Image.open(card_path).convert("RGB").crop((40, 125, 460, crop_bottom)).save(product_img, "JPEG", quality=94, optimize=True)
        if product_img.stat().st_size < 5000:
            raise SystemExit(f"{c['code']}: bottle crop unexpectedly small")
        perfume_map[c["code"]] = f"database/assets/perfumes/{c['fid']}.jpg"

        selected_url = c["shobi_url"] + "#/1-choose-eau_de_parfum/2-bottle-30ml/3-extra_essence-0ml"
        price_text = f"{c['price']:.1f}".rstrip("0").rstrip(".")
        source_rows.append({
            "product_id": c["product_id"], "code": c["display"], "reference": c["reference"],
            "category": c["category"], "price_eur": price_text, "inspired_by": c["inspired_by_source"],
            "description_short": c["description"], "url": selected_url, "image_url": c["shobi_image"], "page": "1"
        })
        master_rows.append({
            "prestashop_product_id": c["product_id"], "shobi_code": c["code"], "shobi_name": c["display"],
            "reference": c["reference"], "reference_prefix": c["reference"].split("-", 1)[0],
            "inspired_by": c["inspired_by_source"], "category": c["category"], "price_from_eur": f"{c['price']:.1f}",
            "official_description": c["description"], "url": c["shobi_url"], "first_seen": today,
            "last_seen": today, "status": "ACTIVE", "classification_rule": "Official live Shobi Eau de Parfum product page",
            "source": "SHOBI_OFFICIAL_EN_2026-10-19"
        })
        mapping_rows.append({
            "prestashop_product_id": c["product_id"], "shobi_code": c["code"],
            "inspired_by": c["inspired_by_source"], "original_brand": c["brand"], "original_perfume": c["perfume"],
            "identity_status": "CONFIRMED", "fragrantica_status": "FOUND", "fragrantica_id": c["fid"],
            "fragrantica_url": c["fragrantica_url"],
            "evidence_note": "Official product ID recovered from PrestaShop article[data-id-product]; exact FID card/title/brand, ordered notes, note icons, gender and season checked 2026-10-19."
        })

        notes = list(c["notes"])
        audit = {"status": "green", "checks": dict(ALL_CHECKS), "issues": [],
                 "notesCount": 6, "matchedNotesCount": 6, "iconsCount": 6}
        db_rows.append({
            "id": f"pid:{c['product_id']}", "code": c["code"], "prestashopProductId": c["product_id"],
            "reference": c["reference"], "shobiUrl": selected_url, "brand": c["brand"], "inspiredBy": c["perfume"],
            "fragranticaId": c["fid"], "fragranticaStatus": "FOUND", "image": None,
            "genderAffinity": c["affinity"], "seasons": [c["season"]], "mainAccords": list(c["accords"]),
            "notes": {"top": [], "heart": [], "base": []}, "enrichmentStatus": "PENDING",
            "masterVersion": "shobi-live-official-2026-10-19", "occasions": [],
            "fragranticaVerificationSource": "database/audits/verified-shobi-additions-2026-10-19.json",
            "fragranticaSocialCardNotes": notes, "fragranticaSocialCardStatus": "VALIDATED_IMAGE_ORDER_STRICT",
            "gender": c["gender"], "genderSource": c["fragrantica_url"], "genderStatus": "VALIDATED_SOCIAL_CARD",
            "liveDisplayCode": c["display"], "shobiImageUrl": c["shobi_image"], "shobiCategory": c["category"],
            "shobiPriceEur": price_text, "identityStatus": "CONFIRMED",
            "catalogSource": "database/source/shobi-perfumes-live-unique.csv",
            "fragranticaUrl": c["fragrantica_url"], "seasonStatus": "VALIDATED_MANUAL",
            "seasonCardFid": c["fid"], "validationAudit": audit
        })
        site_rows.append({
            "code": c["code"], "inspiredBy": c["perfume"], "brand": c["brand"],
            "fragranticaUrl": c["fragrantica_url"], "genderAffinity": c["affinity"],
            "seasons": [c["season"]], "mainAccords": list(c["accords"]), "occasions": [],
            "fragranticaSocialCardNotes": notes, "validationStatus": "green", "validationIssues": [],
            "validationChecks": dict(ALL_CHECKS), "validationNotesCount": 6, "validationMatchedNotesCount": 6,
            "validationIconsCount": 6
        })
        icon_records = {note: icon_map[note.casefold()] for note in notes}
        proof_rows.append({
            "code": c["code"], "liveDisplayCode": c["display"], "prestashopProductId": int(c["product_id"]),
            "shobiReference": c["reference"], "officialShobiProductUrl": c["shobi_url"],
            "officialShobiImageUrl": c["shobi_image"], "officialDescription": c["description"],
            "originalBrand": c["brand"], "originalPerfume": c["perfume"], "fragranticaId": int(c["fid"]),
            "fragranticaUrl": c["fragrantica_url"], "cardPath": card_rel, "cardSHA256": card_hash,
            "cardDimensions": [1200, 1200], "mainNotesExactVisualOrder": notes, "localNoteIcons": icon_records,
            "genderLabelOnCard": c["gender_label"], "gender": c["gender"], "seasonBarWinner": c["season_label"],
            "seasonBarObservation": c["season_observation"],
            "visualMethod": "Full exact-FID 1200x1200 Social Card and enlarged complete note-panel crop read twice in row-major order; no pyramid used.",
            "bottleImagePath": f"database/assets/perfumes/{c['fid']}.jpg", "bottleImageSHA256": digest(product_img),
            "validation": "CERTIFIED_GREEN_FULL_CHAIN_VERIFIED"
        })
        manifest_additions.append({
            "prestashop_product_id": c["product_id"], "shobi_code": c["code"],
            "inspired_by": c["inspired_by_source"], "original_brand": c["brand"], "original_perfume": c["perfume"],
            "identity_status": "CONFIRMED", "fragrantica_status": "FOUND", "fragrantica_id": c["fid"],
            "fragrantica_url": c["fragrantica_url"], "social_card_url": m.get("social_card_url") or "",
            "local_path": card_rel, "card_status": "EXISTS", "bytes": str(card_path.stat().st_size),
            "sha256": card_hash, "error": ""
        })

    # Append the official source tables only after all four image/icon/identity checks passed.
    append_csv(LIVE, source_rows, "product_id", ("code",))
    append_csv(MASTER, master_rows, "prestashop_product_id", ("shobi_code",))
    append_csv(MAPPING, mapping_rows, "prestashop_product_id", ("shobi_code",))

    base_fields, base_rows = read_csv(args.base_manifest)
    merged = {(str(r.get("prestashop_product_id") or "").strip(), norm_code(r.get("shobi_code"))): r for r in base_rows}
    for row in manifest_additions:
        key = (row["prestashop_product_id"], norm_code(row["shobi_code"]))
        if key in merged or any(norm_code(old.get("shobi_code")) == key[1] for old in base_rows):
            raise SystemExit(f"Refusing existing card manifest entry {key}")
        merged[key] = row
    with MANIFEST_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=base_fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(merged.values())

    PERFUME_MAP_PATH.write_text(map_prefix + json.dumps(perfume_map, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    db.extend(db_rows)
    site.extend(site_rows)
    write_json(DB_PATH, db)
    write_json(SITE_PATH, site, pretty=False)

    ordered_data = read_json(ORDERED_PATH)
    if not isinstance(ordered_data, dict) or not isinstance(ordered_data.get("rows"), list):
        raise SystemExit("Unexpected ordered-image audit schema")
    ordered_by_code = {norm_code(r.get("code")): r for r in ordered_data["rows"]}
    for p in proof_rows:
        ordered_by_code[p["code"]] = {
            "code": p["code"], "fragranticaId": p["fragranticaId"], "card": p["cardPath"],
            "catalogNotes": p["mainNotesExactVisualOrder"], "observedNotes": p["mainNotesExactVisualOrder"],
            "result": "EXACT_ORDERED_MATCH",
            "proof": "Independent visual read of full exact-FID Social Card and complete note-panel crop; no competing sequence.",
            "attempts": []
        }
    ordered_data["catalogRows"] = len(db)
    ordered_data["rows"] = sorted(ordered_by_code.values(), key=lambda r: norm_code(r.get("code")))
    write_json(ORDERED_PATH, ordered_data)

    validated_data = read_json(VALIDATED_PATH)
    if not isinstance(validated_data, list):
        raise SystemExit("Unexpected validated-main-notes schema")
    validated_by_code = {norm_code(r.get("code")): r for r in validated_data}
    for p in proof_rows:
        validated_by_code[p["code"]] = {
            "code": p["code"], "fragranticaId": p["fragranticaId"], "card": p["cardPath"],
            "validated": True, "mainNotes": p["mainNotesExactVisualOrder"],
            "validationMethod": "INDEPENDENT_MANUAL_FULL_CARD_AND_CROP_2026-10-19"
        }
    write_json(VALIDATED_PATH, sorted(validated_by_code.values(), key=lambda r: norm_code(r.get("code"))))

    scope = read_json(SCOPE_PATH)
    expected = {
        "sourceCatalogRows": 2349, "uniqueLiveShobiRowsBeforeScopeExclusions": 2345,
        "operationalCleanShobiRows": 2278, "projectedPublicRowsAfterConfirmedExclusions": 2282,
        "projectedUniquePublicRowsAfterDuplicateCollapse": 2278,
        "projectedUniquePublicRowsAfterSameOriginalDedupe": 2253
    }
    for key, value in expected.items():
        if scope.get(key) not in (value - 4, value):
            raise SystemExit(f"Unexpected scope baseline {key}={scope.get(key)}")
        scope[key] = value
    scope["auditedAt"] = today
    scope.setdefault("notes", []).append(
        "2026-10-19: added four live official Shobi EDPs after exact product-ID recovery, exact-FID Social Card visual/order verification, local note-icon checks, and gender/season review."
    )
    write_json(SCOPE_PATH, scope)

    write_json(PROOF_PATH, {
        "auditDate": today, "status": "CERTIFIED_GREEN_FULL_CHAIN_VERIFIED",
        "method": "Official product IDs from PrestaShop article[data-id-product]; exact FID Social Cards; full card plus complete note crop read twice; local icons verified; gender from card; longest season bar selected.",
        "catalogChanged": True, "newPublicRows": 4, "rows": proof_rows
    })

    candidate_audit = read_json(AUDIT_PATH)
    ca_by_code = {norm_code(r.get("code")).replace(" W", "").replace(" MP", ""): r for r in candidate_audit.get("candidates", [])}
    for c in CANDIDATES:
        ar = ca_by_code.get(c["code"])
        if not ar:
            raise SystemExit(f"Missing pending candidate audit row {c['code']}")
        p = next(x for x in proof_rows if x["code"] == c["code"])
        ar.update({
            "prestashop_product_id": c["product_id"], "product_image_url": c["shobi_image"],
            "fragrantica_url": c["fragrantica_url"], "certification": "CERTIFIED_GREEN_FULL_CHAIN_VERIFIED",
            "local_social_card": p["cardPath"], "local_product_image": p["bottleImagePath"],
            "verified_main_notes_order": c["notes"], "verified_gender": c["gender"],
            "verified_gender_label": c["gender_label"], "verified_season": c["season_label"],
            "local_note_icons": p["localNoteIcons"], "card_sha256": p["cardSHA256"],
            "product_image_sha256": p["bottleImageSHA256"]
        })
    candidate_audit["status"] = "CERTIFIED_GREEN_FULL_CHAIN_VERIFIED"
    candidate_audit["publication_policy"] = "All four records are integrated after exact official product IDs, FIDs, ordered Social Cards, local icons, gender and season proof."
    candidate_audit["catalog_changed"] = True
    write_json(AUDIT_PATH, candidate_audit)

    id_audit = read_json(ID_AUDIT_PATH)
    ia_by_code = {norm_code(r.get("code")).replace(" W", "").replace(" MP", ""): r for r in id_audit.get("candidates", [])}
    for c in CANDIDATES:
        item = ia_by_code.get(c["code"])
        if not item:
            raise SystemExit(f"Missing recovered-ID row {c['code']}")
        item["prestashop_product_id"] = c["product_id"]
        item["status"] = "CARD_VISUALLY_VERIFIED_AND_CATALOGED"
        item["fragrantica_id"] = c["fid"]
        item["fragrantica_url"] = c["fragrantica_url"]
        item["local_social_card"] = card_paths[c["code"]]
    id_audit["status"] = "ALL_FOUR_IDS_AND_SOCIAL_CARDS_VERIFIED"
    id_audit["catalog_changed"] = True
    write_json(ID_AUDIT_PATH, id_audit)

    recent = read_json(RECENT_PATH)
    entries = {norm_code(x.get("code")): x for x in recent.get("entries", [])}
    for c in CANDIDATES:
        entries[c["code"]] = {"code": c["code"], "addedDate": today}
    recent["entries"] = sorted(entries.values(), key=lambda x: (str(x.get("addedDate") or ""), norm_code(x.get("code"))))
    recent["count"] = len(set(norm_code(x) for x in recent.get("codes", [])) | set(entries))
    write_json(RECENT_PATH, recent)

    yellow = read_json(YELLOW_PATH)
    if yellow.get("totalCatalog") not in (2274, 2278):
        raise SystemExit(f"Unexpected yellow report baseline: {yellow.get('totalCatalog')}")
    yellow["totalCatalog"] = 2278
    write_json(YELLOW_PATH, yellow)

    official_text = OFFICIAL_DB_PATH.read_text(encoding="utf-8")
    for old, new in (("2,249", "2,253"), ("2,274", "2,278"), ("2,246", "2,250")):
        official_text = official_text.replace(old, new)
    OFFICIAL_DB_PATH.write_text(official_text, encoding="utf-8")

    handoff = HANDOFF_PATH.read_text(encoding="utf-8")
    handoff = handoff.replace("**Last verified:** 2026-10-02", "**Last verified:** 2026-10-19")
    handoff = handoff.replace("| Operational source catalog | 2,274 | 2,268 | 6 | 0 |", "| Operational source catalog | 2,278 | 2,272 | 6 | 0 |")
    handoff = handoff.replace("| Public perfume-only catalog | 2,249 | 2,243 | 6 | 0 |", "| Public perfume-only catalog | 2,253 | 2,247 | 6 | 0 |")
    marker = "## Recent additions UI"
    batch = """## Newly verified Shobi additions — 2026-10-19

The following four official wearable Eau de Parfum listings were integrated as green after exact product-ID recovery and full Social Card proof:

- 2854-RIH — product ID 5224, Rihanna — Reb'l Fleur, FID 10554.
- 2877-VIC — product ID 5225, Viktor&Rolf — Spicebomb Infrared (2021 EDT), FID 66514 (not the later EDP/FID 81409).
- 2878-MAN — product ID 5226, Mancera — Fig Me Up, FID 98362.
- 2879-KAY — product ID 5227, Kayali Fragrances — Freedom Musk Matcha | 45 Eau de Parfum, FID 118623.

Ordered notes, icon paths, card/gender/season evidence: database/audits/verified-shobi-additions-2026-10-19.json.

"""
    if "## Newly verified Shobi additions — 2026-10-19" not in handoff:
        handoff = handoff.replace(marker, batch + marker)
    handoff = handoff.replace("- Current batch date: 2026-09-30.\n- It is visible through 2026-10-20.\n- From 2026-10-21, those products automatically leave the filter and the filter is hidden.", "- Historical batch date: 2026-09-30 (21 products; visible through 2026-10-20).\n- Current batch date: 2026-10-19 (4 products; visible through 2026-11-08).\n- Each batch expires independently based on its own addedDate; do not extend the September batch when adding October entries.")
    HANDOFF_PATH.write_text(handoff, encoding="utf-8")

    print(json.dumps({
        "integrated": [c["code"] for c in CANDIDATES],
        "productIds": {c["code"]: c["product_id"] for c in CANDIDATES},
        "fids": {c["code"]: c["fid"] for c in CANDIDATES},
        "notesAndIconsVerified": 24, "operationalRows": len(db), "siteRows": len(site),
        "greenAdded": 4, "orderedAuditRows": len(ordered_by_code)
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
