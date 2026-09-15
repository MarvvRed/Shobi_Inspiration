#!/usr/bin/env python3
"""Build the publishable, perfume-only Shobi catalog from audited sources."""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
SITE = ROOT / "database/catalog/catalog_site.json"
EXCLUSIONS = ROOT / "database/catalog/catalog-scope-exclusions.json"
SCOPE_AUDIT = ROOT / "database/catalog/catalog-wearable-original-scope-audit.json"
FINAL = ROOT / "database/catalog/catalog_final_perfume_only.json"
FINAL_DB = ROOT / "database/catalog/database_final_perfume_only.json"
CERTIFICATE = ROOT / "database/catalog/final-perfume-catalog-certification.json"
SUMMARY = ROOT / "database/audits/FINAL-PERFUME-CATALOG.md"

# These are the only visible rows without the usual complete Fragrantica
# identity chain.  They are admitted only because the cited primary/archived
# evidence establishes one concrete, wearable original perfume.
EXCEPTIONS = {
    "2816-MOOD": {
        "reason": "Official Mood London product page: Blonde Maracujá 100ml perfume spray.",
        "source": "https://www.mood.london/collections/perfume-spray/products/blonde-maracuja-100ml",
    },
    "2085-CLIV": {
        "reason": "Official Clive Christian release: X Neroli Limited Edition perfume, 20% concentration.",
        "source": "https://us.clivechristian.com/blogs/new-collection-launch/a-blossoming-story",
    },
    "1251-ROM": {
        "reason": "Exact archived Fragrantica Social Card for Royal Blue by Romane, FID 21103, visibly labels the bottle as cologne for men.",
        "source": "database/fragrantica/social-cards/images/current_1251-ROM_21103.jpeg",
    },
}


def code(value: object) -> str:
    return str(value or "").strip().upper()


def url_matches_fid(url: object, fid: object) -> bool:
    fid_text, url_text = str(fid or "").strip(), str(url or "").strip()
    if not fid_text or not url_text:
        return False
    escaped = re.escape(fid_text)
    return bool(re.search(rf"-{escaped}\.html(?:$|[?#])", url_text, re.I) or
                re.search(rf"/p/{escaped}(?:/?$|[?#])", url_text, re.I))


def main() -> None:
    db_rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    site_rows = json.loads(SITE.read_text(encoding="utf-8-sig"))
    excluded = {code(item) for item in json.loads(EXCLUSIONS.read_text(encoding="utf-8")).get("codes", [])}
    scope = json.loads(SCOPE_AUDIT.read_text(encoding="utf-8"))
    if len(db_rows) != len(site_rows):
        raise SystemExit("Database/public-catalog row count mismatch")
    if scope.get("confirmedOutOfScopeCount") != len(excluded):
        raise SystemExit("Scope audit and exclusion manifest disagree")

    final_rows, final_db_rows, direct, exceptions, failures = [], [], 0, [], []
    for db, site in zip(db_rows, site_rows):
        product_code = code(db.get("code"))
        if product_code in excluded:
            continue
        identity_check = bool((db.get("validationAudit") or {}).get("checks", {}).get("identity"))
        standard_proof = (
            identity_check
            and str(db.get("identityStatus") or "").upper() == "CONFIRMED"
            and bool(db.get("fragranticaVerificationSource"))
            and url_matches_fid(db.get("fragranticaUrl"), db.get("fragranticaId"))
        )
        exception = EXCEPTIONS.get(product_code)
        source_ok = db.get("catalogSource") == "database/source/shobi-perfumes-live-unique.csv"
        shobi_ok = bool(db.get("prestashopProductId")) and bool(db.get("shobiUrl"))
        if not source_ok or not shobi_ok or not (standard_proof or exception):
            failures.append({
                "code": product_code,
                "sourceOk": source_ok,
                "shobiOk": shobi_ok,
                "standardIdentityProof": standard_proof,
                "exception": exception,
            })
            continue
        if exception:
            exceptions.append({"code": product_code, **exception})
        else:
            direct += 1
        final_rows.append(site)
        final_db_rows.append(db)

    expected = scope.get("projectedPublicRowsAfterConfirmedExclusions")
    if failures or len(final_rows) != expected:
        raise SystemExit(json.dumps({"failures": failures, "rows": len(final_rows), "expected": expected}, ensure_ascii=False))

    certificate = {
        "rule": "Publish only one-to-one Shobi records whose original is an audited genuine wearable perfume. Candles, home/room/car fragrance, body or hair mists, laundry scents, accessories, and Shobi-invented/non-demonstrable originals are excluded.",
        "sourceCatalogRows": len(db_rows),
        "confirmedExcludedRows": len(excluded),
        "finalRows": len(final_rows),
        "allFinalRowsFromLiveShobiSource": True,
        "allFinalRowsHaveShobiProductIdAndUrl": True,
        "directFragranticaIdentityProofRows": direct,
        "exceptionRowsWithSpecificEvidence": exceptions,
        "excludedCodes": sorted(excluded),
        "scopeAudit": "database/catalog/catalog-wearable-original-scope-audit.json",
    }
    FINAL.write_text(json.dumps(final_rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    FINAL_DB.write_text(json.dumps(final_db_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CERTIFICATE.write_text(json.dumps(certificate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Final perfume-only Shobi catalog",
        "",
        f"- Final rows: **{len(final_rows)}**",
        f"- Excluded as non-wearable/non-demonstrable originals: **{len(excluded)}**",
        f"- Direct Fragrantica identity proofs: **{direct}**",
        f"- Specific-evidence exceptions: **{len(exceptions)}**",
        "- Every published row has a live Shobi product ID and URL.",
        "",
        "## Specific-evidence exceptions",
        "",
    ]
    for item in exceptions:
        lines.append(f"- `{item['code']}` — {item['reason']} Source: `{item['source']}`.")
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"finalRows": len(final_rows), "excluded": len(excluded), "direct": direct, "exceptions": len(exceptions)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
