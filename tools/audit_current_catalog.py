#!/usr/bin/env python3
"""Audit the current public catalog without trusting its existing colour badges.

Every green row is independently tied to an exact archived Social Card proof:
either the strict ordered-image audit or the current-FID exact-card proof.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
SITE = ROOT / "database/catalog/catalog_site.json"
ORDERED = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
VALIDATED = ROOT / "database/fragrantica/social-cards/records/social-card-main-notes-validated.json"
JSON_OUT = ROOT / "database/audits/current-catalog-audit.json"
MD_OUT = ROOT / "database/audits/CURRENT-CATALOG-AUDIT.md"


def code(value: object) -> str:
    return str(value or "").strip().upper()


def values(value: object) -> list[str]:
    return list(value or [])


def url_matches_fid(url: object, fid: object) -> bool:
    fid_text = str(fid or "").strip()
    url_text = str(url or "").strip()
    if not fid_text or not url_text:
        return False
    escaped = re.escape(fid_text)
    return bool(re.search(rf"-{escaped}\.html(?:$|[?#])", url_text, re.I) or
                re.search(rf"/p/{escaped}(?:/?$|[?#])", url_text, re.I))


def same_site_projection(db: dict, site: dict) -> bool:
    return (
        db.get("code") == site.get("code")
        and db.get("brand") == site.get("brand")
        and db.get("inspiredBy") == site.get("inspiredBy")
        and values(db.get("fragranticaSocialCardNotes")) == values(site.get("fragranticaSocialCardNotes"))
        and (db.get("validationAudit") or {}).get("status") == site.get("validationStatus")
    )


def main() -> None:
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    site_rows = json.loads(SITE.read_text(encoding="utf-8-sig"))
    ordered_rows = json.loads(ORDERED.read_text(encoding="utf-8")).get("rows", [])
    validated_rows = json.loads(VALIDATED.read_text(encoding="utf-8"))

    ordered = {code(item.get("code")): item for item in ordered_rows}
    validated = {code(item.get("code")): item for item in validated_rows}
    if len(rows) != len(site_rows) or len(rows) != len(ordered_rows):
        raise SystemExit("Current catalog, public projection, and ordered audit counts differ")

    green_proofs = []
    failures = []
    yellow = []
    projection_mismatches = []
    duplicate_codes: dict[str, list[dict]] = defaultdict(list)
    duplicate_pids: dict[str, list[dict]] = defaultdict(list)
    duplicate_urls: dict[str, list[dict]] = defaultdict(list)

    for index, (row, site) in enumerate(zip(rows, site_rows)):
        product_code = code(row.get("code"))
        fid = str(row.get("fragranticaId") or "").strip()
        notes = values(row.get("fragranticaSocialCardNotes"))
        status = (row.get("validationAudit") or {}).get("status")
        checks = (row.get("validationAudit") or {}).get("checks") or {}
        duplicate_codes[product_code].append(row)
        duplicate_pids[str(row.get("prestashopProductId") or "").strip()].append(row)
        duplicate_urls[str(row.get("shobiUrl") or "").strip().lower().rstrip("/")].append(row)

        if not same_site_projection(row, site):
            projection_mismatches.append({"index": index, "code": product_code})

        if status == "green":
            strict = ordered.get(product_code) or {}
            source = validated.get(product_code) or {}
            strict_proof = (
                strict.get("result") == "EXACT_ORDERED_MATCH"
                and str(strict.get("fragranticaId") or "") == fid
                and values(strict.get("observedNotes")) == notes
                and values(strict.get("catalogNotes")) == notes
                and bool(strict.get("card"))
                and (ROOT / str(strict.get("card"))).is_file()
            )
            fast_proof = (
                source.get("validationMethod") == "CURRENT_FID_FAST_EXACT_PROOF"
                and str(source.get("fragranticaId") or "") == fid
                and values(source.get("mainNotes")) == notes
                and bool(source.get("card"))
                and (ROOT / str(source.get("card"))).is_file()
            )
            proof = "strict-ordered-image" if strict_proof else "current-fid-exact-card" if fast_proof else None
            passed_checks = all(value is True for value in checks.values()) and bool(checks)
            row_failures = []
            if not product_code:
                row_failures.append("missing code")
            if not fid or not url_matches_fid(row.get("fragranticaUrl"), fid):
                row_failures.append("Fragrantica URL/FID mismatch")
            if not notes:
                row_failures.append("missing Main Notes")
            if not passed_checks:
                row_failures.append("green row has a failed validation check")
            if proof is None:
                row_failures.append("missing exact ordered Social Card proof")
            if row_failures:
                failures.append({
                    "code": product_code,
                    "brand": row.get("brand"),
                    "inspiredBy": row.get("inspiredBy"),
                    "failures": row_failures,
                })
            else:
                card = strict.get("card") if strict_proof else source.get("card")
                green_proofs.append({
                    "code": product_code,
                    "prestashopProductId": row.get("prestashopProductId"),
                    "fragranticaId": fid,
                    "fragranticaUrl": row.get("fragranticaUrl"),
                    "notes": notes,
                    "proof": proof,
                    "card": card,
                })
        elif status == "yellow":
            yellow.append({
                "code": product_code,
                "brand": row.get("brand"),
                "inspiredBy": row.get("inspiredBy"),
                "failedChecks": [name for name, value in checks.items() if value is not True],
            })
        else:
            failures.append({
                "code": product_code,
                "brand": row.get("brand"),
                "inspiredBy": row.get("inspiredBy"),
                "failures": [f"unexpected validation status: {status!r}"],
            })

    # These four code collisions are retained deliberately: each has a distinct
    # live Shobi product ID and product URL (men/women category listings), so no
    # row can be deleted without choosing between still-live source products.
    parallel_listings = [
        {
            "code": product_code,
            "prestashopProductIds": [item.get("prestashopProductId") for item in group],
            "shobiUrls": [item.get("shobiUrl") for item in group],
        }
        for product_code, group in sorted(duplicate_codes.items())
        if product_code and len(group) > 1
    ]
    pid_collisions = [key for key, group in duplicate_pids.items() if key and len(group) > 1]
    url_collisions = [key for key, group in duplicate_urls.items() if key and len(group) > 1]

    myth = next((item for item in green_proofs if item["code"] == "1912-AMG"), None)
    report = {
        "rule": "A green row passes only with a coherent FID/URL, exact current notes, all validation checks true, and an exact archived Social Card proof. Existing badges are not accepted as evidence.",
        "catalogRows": len(rows),
        "siteRows": len(site_rows),
        "orderedAuditRows": len(ordered_rows),
        "validationCounts": dict(Counter((row.get("validationAudit") or {}).get("status") for row in rows)),
        "greenProofCounts": dict(Counter(item["proof"] for item in green_proofs)),
        "greenRowsAudited": len(green_proofs),
        "greenProofs": green_proofs,
        "greenFailures": failures,
        "siteProjectionMismatches": projection_mismatches,
        "parallelShobiListings": parallel_listings,
        "duplicatePrestashopProductIds": pid_collisions,
        "duplicateShobiUrls": url_collisions,
        "mythsMan": myth,
        "unverifiedYellowRows": yellow,
    }
    JSON_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Current catalog audit",
        "",
        "- Catalog rows: **%d**" % len(rows),
        "- Public-site rows: **%d**" % len(site_rows),
        "- Green rows audited: **%d**" % len(green_proofs),
        "- Green-row errors: **%d**" % len(failures),
        "- Yellow (intentionally unverified) rows: **%d**" % len(yellow),
        "- Red rows: **%d**" % report["validationCounts"].get("red", 0),
        "- DB/site projection mismatches: **%d**" % len(projection_mismatches),
        "- Fragrantica URL/FID mismatches among green rows: **0**" if not any("Fragrantica URL/FID mismatch" in x["failures"] for x in failures) else "- Fragrantica URL/FID mismatches among green rows: **present**",
        "- Duplicate Prestashop product IDs: **%d**" % len(pid_collisions),
        "- Duplicate Shobi URLs: **%d**" % len(url_collisions),
        "",
        "## Green proof methods",
        "",
    ]
    for proof, count in sorted(report["greenProofCounts"].items()):
        lines.append(f"- `{proof}`: **{count}**")
    lines += ["", "## Confirmed green-row errors", ""]
    if failures:
        for item in failures:
            lines.append(f"- `{item['code']}` — {item['brand']} — {item['inspiredBy']}: {'; '.join(item['failures'])}")
    else:
        lines.append("- None.")
    lines += ["", "## Myths Man — Amouage", ""]
    if myth:
        lines.append("- `1912-AMG`, FID `38259`: exact 6-note match — " + ", ".join(myth["notes"]) + ".")
    lines += ["", "## Parallel live Shobi listings retained", ""]
    for item in parallel_listings:
        lines.append(f"- `{item['code']}`: distinct product IDs {', '.join(map(str, item['prestashopProductIds']))}.")
    lines += ["", "## Intentionally unverified yellow rows", ""]
    for item in yellow:
        lines.append(f"- `{item['code']}` — {item['brand']} — {item['inspiredBy']}: {', '.join(item['failedChecks'])}.")
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "catalogRows": len(rows),
        "greenRowsAudited": len(green_proofs),
        "greenFailures": len(failures),
        "yellow": len(yellow),
        "siteProjectionMismatches": len(projection_mismatches),
        "json": str(JSON_OUT),
        "markdown": str(MD_OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
