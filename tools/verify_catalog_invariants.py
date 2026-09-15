#!/usr/bin/env python3
"""Independent catalog safety gate.

This script is intentionally separate from build_validation_audit.py: it verifies the
published state instead of trusting the builder that produced it.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
SITE = ROOT / "database/catalog/catalog_site.json"
ORDERED_AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
REPORT = ROOT / "database/audits/CURRENT-CATALOG-AUDIT.md"
ALLOWLIST = ROOT / "database/audits/identity-change-allowlist.json"

PROTECTED_IDENTITIES = {
    "1037-BLG": {"fid": "9403", "name": "Bvlgari Man"},
    "1751-GUL": {"fid": "3681", "name": "Ma Dame"},
    "928-TRU": {"fid": "16241", "name": "Trussardi Delicate Rose"},
    "548-CLI": {"fid": "372", "name": "Happy"},
    "1086-CLI": {"fid": "373", "name": "Happy For Men"},
    "2194-ORT": {"fid": "69923", "name": "Cuoium"},
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def identity(row):
    return (norm(row.get("brand")), norm(row.get("inspiredBy")), str(row.get("fragranticaId") or "").strip())


def identity_from_spec(spec):
    return (norm(spec.get("brand")), norm(spec.get("name")), str(spec.get("fid") or "").strip())


def git_json(ref: str, path: str):
    proc = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout.lstrip("\ufeff"))


def load_allowlist():
    if not ALLOWLIST.is_file():
        return {}
    data = load(ALLOWLIST)
    entries = data.get("authorizedChanges", []) if isinstance(data, dict) else []
    out = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip().upper()
        before = item.get("from") or {}
        after = item.get("to") or {}
        if code and before and after:
            out[(code, identity_from_spec(before), identity_from_spec(after))] = str(item.get("reason") or "")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-ref", help="Git ref whose database_complete.json is the identity baseline")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    db = load(DB)
    site = load(SITE)
    audit_rows = load(ORDERED_AUDIT).get("rows", [])
    by_code = {str(r.get("code") or "").strip().upper(): r for r in db}
    site_by_code = {str(r.get("code") or "").strip().upper(): r for r in site}
    audit_by_code = {str(r.get("code") or "").strip().upper(): r for r in audit_rows}

    failures = []
    if len(by_code) != len(db): failures.append("duplicate Shobi codes in database_complete.json")
    if len(site_by_code) != len(site): failures.append("duplicate Shobi codes in catalog_site.json")
    if set(by_code) != set(site_by_code): failures.append("database_complete/catalog_site code sets differ")

    green = []
    for code, srow in site_by_code.items():
        if srow.get("validationStatus") != "green":
            continue
        green.append(code)
        row = by_code.get(code)
        ev = audit_by_code.get(code)
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

    fid_identities = defaultdict(lambda: defaultdict(list))
    for code, row in by_code.items():
        fid = str(row.get("fragranticaId") or "").strip()
        if fid:
            fid_identities[fid][(norm(row.get("brand")), norm(row.get("inspiredBy")))].append(code)
    conflicting_fids = 0
    for fid, groups in fid_identities.items():
        if len(groups) > 1:
            conflicting_fids += 1
            detail = "; ".join(f"{brand}/{name}: {','.join(codes)}" for (brand, name), codes in groups.items())
            failures.append(f"FID {fid} maps to multiple identities: {detail}")

    for code, expected in PROTECTED_IDENTITIES.items():
        row = by_code.get(code)
        if not row:
            failures.append(f"{code}: protected identity missing")
            continue
        if str(row.get("fragranticaId") or "").strip() != expected["fid"]:
            failures.append(f"{code}: protected FID changed from {expected['fid']}")
        actual_name = norm(row.get("inspiredBy"))
        expected_name = norm(expected["name"])
        if expected_name not in actual_name and actual_name not in expected_name:
            failures.append(f"{code}: protected perfume identity changed from {expected['name']}")

    identity_changes = []
    if args.baseline_ref:
        baseline = git_json(args.baseline_ref, "database/catalog/database_complete.json")
        if baseline is not None:
            old = {str(r.get("code") or "").strip().upper(): r for r in baseline}
            allowed = load_allowlist()
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
            f"- Conflicting shared Fragrantica IDs: **{conflicting_fids}**",
            f"- Unauthorized identity/FID changes vs baseline: **{len(identity_changes)}**", "",
            "A green row is accepted only when its current Fragrantica ID has an `EXACT_ORDERED_MATCH` and the catalog note list is identical to the observed Social Card list in count, value, and order.", ""
        ]), encoding="utf-8")

    print(json.dumps({"rows": len(site), "counts": counts, "greenExactOrdered": len(green), "conflictingFids": conflicting_fids, "failures": len(failures)}, indent=2))
    if failures:
        for item in failures[:100]: print("FAIL:", item)
        raise SystemExit(f"Catalog invariant gate failed with {len(failures)} issue(s)")


if __name__ == "__main__":
    main()
