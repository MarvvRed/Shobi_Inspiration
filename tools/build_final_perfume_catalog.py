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
# These pairs are independently audited as two Shobi listings of the exact same
# original perfume.  The code sets make this a closed safety gate: a new shared
# Fragrantica ID is never collapsed automatically.
CONFIRMED_DUPLICATE_ORIGINALS = {
    "221": {"525-DRC", "1074-DRC"},
    "248": {"475-CAL", "1048-CAL"},
    "257": {"470-CAL", "1045-CAL"},
    "423": {"653-ARM", "1131-ARM"},
    "485": {"557-DOL", "1095-DOL"},
    "498": {"1504-DON", "574-DON"},
    "502": {"494-CHA", "1064-CHA"},
    "698": {"566-DOL", "1099-DOL"},
    "704": {"920-TMU", "1262-TMU"},
    "720": {"717-ISS", "718-ISS"},
    "813": {"426-BRB", "1027-BRB"},
    "897": {"1250-RAL", "2533-RAL"},
    "1261": {"769-LART", "1195-LART"},
    "3403": {"753-KEN", "1190-KEN"},
    "4323": {"127-KIL", "153-PARF"},
    "5979": {"711-HUG", "1163-HUG"},
    "10573": {"734-JIM", "735-JIM"},
    "12424": {"500-CHA", "501-CHA"},
    "14606": {"468-CAL", "1043-CAL"},
    "26777": {"909-SFER", "1258-SFER"},
    "31045": {"880-PRA", "1239-PRA"},
    "35780": {"483-CAR", "1057-CAR"},
    "44034": {"1096-DOL", "1872-DOL"},
    "46186": {"1542-JOM", "2626-JOM"},
    "95641": {"2456-PAC", "2513-PAC"},
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


def duplicate_identity_key(db: dict, site: dict) -> tuple[str, str, str, str]:
    """The public catalog may collapse two live Shobi category listings."""
    return (
        str(db.get("fragranticaId") or "").strip(),
        str(site.get("brand") or "").strip().casefold(),
        str(site.get("inspiredBy") or "").strip().casefold(),
        str(site.get("fragranticaUrl") or "").strip().casefold(),
    )


def stable_listing_key(db: dict) -> tuple[int, str]:
    """Keep the oldest live Shobi listing when it is cross-listed by category."""
    product_id = str(db.get("prestashopProductId") or "").strip()
    return (int(product_id) if product_id.isdigit() else 10**12, str(db.get("shobiUrl") or ""))


def collapse_confirmed_duplicate_originals(candidates):
    """Keep one live Shobi listing for each explicitly audited same-original pair."""
    by_fid = {}
    for candidate in candidates:
        fid = str(candidate[0].get("fragranticaId") or "").strip()
        if fid in CONFIRMED_DUPLICATE_ORIGINALS:
            by_fid.setdefault(fid, []).append(candidate)

    dropped, collapsed = set(), []
    for fid, expected_codes in CONFIRMED_DUPLICATE_ORIGINALS.items():
        matches = by_fid.get(fid, [])
        observed_codes = {code(item[0].get("code")) for item in matches}
        if observed_codes != expected_codes:
            raise SystemExit(
                f"Duplicate-original safety gate failed for FID {fid}: "
                f"expected {sorted(expected_codes)}, found {sorted(observed_codes)}"
            )
        keep = min(matches, key=lambda item: stable_listing_key(item[0]))
        keep_code = code(keep[0].get("code"))
        removed = []
        for item in matches:
            if item is keep:
                continue
            dropped.add(id(item))
            removed.append(code(item[0].get("code")))
        collapsed.append({
            "fragranticaId": fid,
            "keptCode": keep_code,
            "keptPrestashopProductId": keep[0].get("prestashopProductId"),
            "removedCodes": sorted(removed),
            "removedPrestashopProductIds": sorted(
                str(item[0].get("prestashopProductId")) for item in matches if item is not keep
            ),
        })
    return [item for item in candidates if id(item) not in dropped], collapsed


def main() -> None:
    db_rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    site_rows = json.loads(SITE.read_text(encoding="utf-8-sig"))
    excluded = {code(item) for item in json.loads(EXCLUSIONS.read_text(encoding="utf-8")).get("codes", [])}
    scope = json.loads(SCOPE_AUDIT.read_text(encoding="utf-8"))
    if len(db_rows) != len(site_rows):
        raise SystemExit("Database/public-catalog row count mismatch")
    if scope.get("confirmedOutOfScopeCount") != len(excluded):
        raise SystemExit("Scope audit and exclusion manifest disagree")

    eligible, exceptions, failures = [], [], []
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
        eligible.append((db, site, exception))

    expected_before_same_original_dedupe = scope.get("projectedUniquePublicRowsAfterDuplicateCollapse")
    if failures or len(eligible) != expected_before_same_original_dedupe:
        raise SystemExit(json.dumps({"failures": failures, "eligibleRows": len(eligible), "expected": expected_before_same_original_dedupe}, ensure_ascii=False))

    eligible, same_original_collapsed = collapse_confirmed_duplicate_originals(eligible)
    expected = expected_before_same_original_dedupe - sum(
        len(item["removedCodes"]) for item in same_original_collapsed
    )

    by_code: dict[str, list[tuple[dict, dict, dict | None]]] = {}
    for candidate in eligible:
        by_code.setdefault(code(candidate[0].get("code")), []).append(candidate)

    final_rows, final_db_rows, direct, collapsed = [], [], 0, []
    for product_code, candidates in by_code.items():
        fingerprints = {duplicate_identity_key(db, site) for db, site, _ in candidates}
        if len(fingerprints) != 1:
            failures.append({
                "code": product_code,
                "reason": "same Shobi code maps to different originals; manual review required",
                "prestashopProductIds": [db.get("prestashopProductId") for db, _, _ in candidates],
            })
            continue
        db, site, exception = min(candidates, key=lambda item: stable_listing_key(item[0]))
        if len(candidates) > 1:
            collapsed.append({
                "code": product_code,
                "keptPrestashopProductId": db.get("prestashopProductId"),
                "removedPrestashopProductIds": sorted(
                    str(item[0].get("prestashopProductId"))
                    for item in candidates if item[0] is not db
                ),
            })
        if exception:
            exceptions.append({"code": product_code, **exception})
        else:
            direct += 1

        # catalog_site.json is deliberately compact.  Its validation fields
        # must come from the audit generated immediately before this builder,
        # never from a stale prior site export.
        audit = db.get("validationAudit") or {}
        status = audit.get("status")
        checks = audit.get("checks")
        issues = audit.get("issues")
        if status not in {"green", "yellow", "red"} or not isinstance(checks, dict) or not isinstance(issues, list):
            failures.append({"code": product_code, "reason": "missing_or_invalid_validation_audit"})
            continue
        site = {
            **site,
            # Notes shown to visitors must be the exact sequence used by the
            # validation audit, never a stale compact-site export.
            "fragranticaSocialCardNotes": db.get("fragranticaSocialCardNotes") or [],
            "validationStatus": status,
            "validationIssues": issues,
            "validationChecks": checks,
            "validationNotesCount": audit.get("notesCount"),
            "validationMatchedNotesCount": audit.get("matchedNotesCount"),
            "validationIconsCount": audit.get("iconsCount"),
        }
        final_rows.append(site)
        # Keep the complete companion export in lockstep with the public
        # final catalog so the independent invariant verifier sees the same
        # audit state that the browser displays.
        final_db_rows.append({
            **db,
            "validationStatus": status,
            "validationIssues": issues,
            "validationChecks": checks,
            "validationNotesCount": audit.get("notesCount"),
            "validationMatchedNotesCount": audit.get("matchedNotesCount"),
            "validationIconsCount": audit.get("iconsCount"),
        })

    if failures or len(final_rows) != expected:
        raise SystemExit(json.dumps({"failures": failures, "finalRows": len(final_rows), "expected": expected}, ensure_ascii=False))

    certificate = {
        "rule": "Publish only one-to-one Shobi records whose original is an audited genuine wearable perfume. Candles, home/room/car fragrance, body or hair mists, laundry scents, accessories, and Shobi-invented/non-demonstrable originals are excluded.",
        "sourceCatalogRows": len(db_rows),
        "confirmedExcludedRows": len(excluded),
        "eligibleVerifiedShobiListings": len(eligible),
        "sourceCrossListedShobiListingsCollapsed": scope.get("crossListedShobiListingsCollapsed", []),
        "confirmedSameOriginalListingsCollapsed": same_original_collapsed,
        "unexpectedOperationalDuplicatesCollapsed": collapsed,
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
        f"- Final unique perfumes: **{len(final_rows)}**",
        f"- Excluded as non-wearable/non-demonstrable originals: **{len(excluded)}**",
        f"- Cross-listed Shobi pages collapsed: **{len(collapsed)}**",
        f"- Confirmed same-original Shobi listings collapsed: **{sum(len(item["removedCodes"]) for item in same_original_collapsed)}**",
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
