#!/usr/bin/env python3
"""Independent catalog safety gate.

This verifier is deliberately separate from the catalog builder: published green state,
Fragrantica identities and shared-FID exceptions must prove themselves independently.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
SITE = ROOT / "database/catalog/catalog_site.json"
FINAL = ROOT / "database/catalog/catalog_final_perfume_only.json"
ORDERED_AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
REPORT = ROOT / "database/audits/CURRENT-CATALOG-AUDIT.md"
ALLOWLIST = ROOT / "database/audits/identity-change-allowlist.json"
CRITICAL_FIXES = ROOT / "database/audits/critical-identity-fixes.json"
CRITICAL_REGISTRY = ROOT / "database/audits/critical-identity-regression-registry.json"
SHARED_FID_REGISTRY = ROOT / "database/audits/shared-fid-alias-registry.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def identity(row):
    return (norm(row.get("brand")), norm(row.get("inspiredBy")), str(row.get("fragranticaId") or "").strip())


def identity_from_spec(spec):
    return (norm(spec.get("brand")), norm(spec.get("name")), str(spec.get("fid") or spec.get("fragranticaId") or "").strip())


def git_json(ref: str, path: str):
    proc = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout.lstrip("\ufeff"))


def load_authorized_identity_changes():
    """Return exact before->after transitions; a code-only permanent bypass is forbidden."""
    out = {}
    if ALLOWLIST.is_file():
        data = load(ALLOWLIST)
        for item in data.get("authorizedChanges", []) if isinstance(data, dict) else []:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").strip().upper()
            before, after = item.get("from") or {}, item.get("to") or {}
            if code and before and after:
                out[(code, identity_from_spec(before), identity_from_spec(after))] = str(item.get("reason") or "")
    # The six audited corrections are historical, exact, reviewable transitions and are
    # therefore valid authorizations for the one rebuild that materializes them.
    if CRITICAL_FIXES.is_file():
        for item in load(CRITICAL_FIXES):
            code = str(item.get("code") or "").strip().upper()
            before, after = item.get("before") or {}, item.get("after") or {}
            if code and before and after:
                out[(code, identity_from_spec(before), identity_from_spec(after))] = str(after.get("reason") or "critical identity correction")
    return out


def load_protected_identities():
    rows = load(CRITICAL_REGISTRY).get("rows", []) if CRITICAL_REGISTRY.is_file() else []
    return {str(item.get("code") or "").strip().upper(): item for item in rows}


def load_shared_fid_registry():
    rows = load(SHARED_FID_REGISTRY).get("rows", []) if SHARED_FID_REGISTRY.is_file() else []
    return {
        str(item.get("fragranticaId") or "").strip(): frozenset(str(c).strip().upper() for c in item.get("codes", []))
        for item in rows
        if item.get("fragranticaId") and item.get("codes")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-ref", help="Git ref whose database_complete.json is the identity baseline")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    db = load(DB)
    site = load(SITE)
    final = load(FINAL)
    audit_rows = load(ORDERED_AUDIT).get("rows", [])
    by_code = {str(r.get("code") or "").strip().upper(): r for r in db}
    site_by_code = {str(r.get("code") or "").strip().upper(): r for r in site}
    final_by_code = {str(r.get("code") or "").strip().upper(): r for r in final}
    audit_by_code = {str(r.get("code") or "").strip().upper(): r for r in audit_rows}

    failures = []
    if len(by_code) != len(db): failures.append("duplicate Shobi codes in database_complete.json")
    if len(site_by_code) != len(site): failures.append("duplicate Shobi codes in catalog_site.json")
    if set(by_code) != set(site_by_code): failures.append("database_complete/catalog_site code sets differ")
    if len(final_by_code) != len(final): failures.append("duplicate Shobi codes in catalog_final_perfume_only.json")
    if set(final_by_code) != set(site_by_code): failures.append("catalog_final_perfume_only/catalog_site code sets differ")
    for code, final_row in final_by_code.items():
        site_row = site_by_code.get(code)
        if site_row and final_row.get("validationStatus") != site_row.get("validationStatus"):
            failures.append(f"{code}: final catalog validation status differs from audit catalog")

    green = []
    for code, srow in site_by_code.items():
        if srow.get("validationStatus") != "green":
            continue
        green.append(code)
        row, ev = by_code.get(code), audit_by_code.get(code)
        if not row:
            failures.append(f"{code}: green row missing from database_complete")
            continue
        notes = row.get("fragranticaSocialCardNotes") or []
        fid = str(row.get("fragranticaId") or "").strip()
        if not ev or ev.get("result") != "EXACT_ORDERED_MATCH":
            failures.append(f"{code}: green without EXACT_ORDERED_MATCH")
            continue
        if str(ev.get("fragranticaId") or "").strip() != fid:
            failures.append(f"{code}: green audit FID differs from catalog FID")
        if ev.get("catalogNotes") != notes or ev.get("observedNotes") != notes:
            failures.append(f"{code}: green notes are not exact/count/order identical to Social Card")
        card = str(ev.get("card") or "").strip()
        if not card or not (ROOT / card).is_file():
            failures.append(f"{code}: green exact proof has no local Social Card file")

    # Shared FIDs are permitted only for exact, audited alias groups. A third code joining
    # an approved pair, or any entirely new shared FID, is a hard regression.
    fid_codes = defaultdict(list)
    for code, row in by_code.items():
        fid = str(row.get("fragranticaId") or "").strip()
        if fid:
            fid_codes[fid].append(code)
    approved_shared = load_shared_fid_registry()
    unapproved_shared = []
    approved_shared_present = []
    for fid, codes in sorted(fid_codes.items()):
        if len(codes) < 2:
            continue
        actual = frozenset(codes)
        if approved_shared.get(fid) == actual:
            approved_shared_present.append((fid, sorted(codes)))
        else:
            unapproved_shared.append((fid, sorted(codes)))
            failures.append(f"FID {fid} is shared by unapproved code set: {','.join(sorted(codes))}")

    # Exact regression locks for identities that were previously mapped to the wrong perfume.
    protected = load_protected_identities()
    for code, expected in protected.items():
        row = by_code.get(code)
        if not row:
            failures.append(f"{code}: protected identity missing")
            continue
        expected_identity = identity_from_spec({"brand": expected.get("brand"), "name": expected.get("name"), "fid": expected.get("fragranticaId")})
        if identity(row) != expected_identity:
            failures.append(f"{code}: protected identity/FID regression {identity(row)} != {expected_identity}")
        expected_url = str(expected.get("fragranticaUrl") or "").strip()
        if expected_url and str(row.get("fragranticaUrl") or "").strip() != expected_url:
            failures.append(f"{code}: protected Fragrantica URL regression")

    identity_changes = []
    if args.baseline_ref:
        baseline = git_json(args.baseline_ref, "database/catalog/database_complete.json")
        if baseline is not None:
            old = {str(r.get("code") or "").strip().upper(): r for r in baseline}
            allowed = load_authorized_identity_changes()
            for code in sorted(set(old) & set(by_code)):
                before, after = identity(old[code]), identity(by_code[code])
                if before != after and (code, before, after) not in allowed:
                    identity_changes.append((code, before, after))
            for code, before, after in identity_changes:
                failures.append(f"{code}: unauthorized identity/FID change {before} -> {after}")

    counts = {s: sum(r.get("validationStatus") == s for r in site) for s in ("green", "yellow", "red")}
    if args.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join([
            "# Current Catalog Audit", "",
            "> Auto-generated by `tools/verify_catalog_invariants.py`. Do not maintain counts manually.", "",
            f"- Total catalog rows: **{len(site)}**",
            f"- Green: **{counts['green']}**",
            f"- Yellow: **{counts['yellow']}**",
            f"- Red: **{counts['red']}**",
            f"- Green rows with mandatory exact ordered Social Card proof: **{len(green)} / {counts['green']}**",
            f"- Approved shared-FID alias groups present: **{len(approved_shared_present)}**",
            f"- Unapproved shared FIDs: **{len(unapproved_shared)}**",
            f"- Unauthorized identity/FID changes vs baseline: **{len(identity_changes)}**", "",
            "A green row is accepted only when its current Fragrantica ID has an `EXACT_ORDERED_MATCH` and the catalog note list is identical to the observed Social Card list in count, value, and order.", "",
            "Shared Fragrantica IDs are allowed only when the exact set of Shobi codes is registered in `shared-fid-alias-registry.json`; any new member or new shared FID fails CI.", ""
        ]), encoding="utf-8")

    print(json.dumps({
        "rows": len(site), "counts": counts, "greenExactOrdered": len(green),
        "approvedSharedFidGroups": len(approved_shared_present), "unapprovedSharedFids": len(unapproved_shared),
        "protectedIdentities": len(protected), "unauthorizedIdentityChanges": len(identity_changes), "failures": len(failures)
    }, indent=2))
    if failures:
        for item in failures[:100]: print("FAIL:", item)
        raise SystemExit(f"Catalog invariant gate failed with {len(failures)} issue(s)")


if __name__ == "__main__":
    main()
