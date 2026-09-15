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

# High-value regression sentinels: these identities were previously observed mapped
# to the wrong Fragrantica perfume and must never silently drift again.
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


def git_json(ref: str, path: str):
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout.lstrip("\ufeff"))


def load_allowlist():
    if not ALLOWLIST.is_file():
        return set()
    data = load(ALLOWLIST)
    entries = data.get("authorizedChanges", data if isinstance(data, list) else [])
    return {str(item.get("code") or "").strip().upper() for item in entries if isinstance(item, dict)}


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
    if len(by_code) != len(db):
        failures.append("duplicate Shobi codes in database_complete.json")
    if len(site_by_code) != len(site):
        failures.append("duplicate Shobi codes in catalog_site.json")
    if set(by_code) != set(site_by_code):
        failures.append("database_complete/catalog_site code sets differ")

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

    # A single Fragrantica ID may legitimately be reused by multiple Shobi products,
    # but it cannot represent different perfume identities.
    fid_identities = defaultdict(lambda: defaultdict(list))
    for code, row in by_code.items():
        fid = str(row.get("fragranticaId") or "").strip()
        if fid:
            key = (norm(row.get("brand")), norm(row.get("inspiredBy")))
            fid_identities[fid][key].append(code)
    for fid, groups in fid_identities.items():
        if len(groups) > 1:
            detail = "; ".join(f"{brand}/{name}: {','.join(codes)}" for (brand, name), codes in groups.items())
            failures.append(f"FID {fid} maps to multiple identities: {detail}")

    # Permanent sentinels for identities already proven wrong in the past.
    for code, expected in PROTECTED_IDENTITIES.items():
        row = by_code.get(code)
        if not row:
            failures.append(f"{code}: protected identity missing")
            continue
        if str(row.get("fragranticaId") or "").strip() != expected["fid"]:
            failures.append(f"{code}: protected FID changed from {expected['fid']}")
        if norm(expected["name"]) not in norm(row.get("inspiredBy")) and norm(row.get("inspiredBy")) not in norm(expected["name"]):
            failures.append(f"{code}: protected perfume identity changed from {expected['name']}")

    # Block silent code->(brand,name,FID) changes. Legitimate corrections require an
    # explicit entry in identity-change-allowlist.json, making the exception reviewable.
    identity_changes = []
    if args.baseline_ref:
        baseline = git_json(args.baseline_ref, "database/catalog/database_complete.json")
        if baseline is not None:
            old = {str(r.get("code") or "").strip().upper(): r for r in baseline}
            allowed = load_allowlist()
            for code in sorted(set(old) & set(by_code)):
                if identity(old[code]) != identity(by_code[code]) and code not in allowed:
                    identity_changes.append((code, identity(old[code]), identity(by_code[code])))
            for code, before, after in identity_changes:
                failures.append(f"{code}: unauthorized identity/FID change {before} -> {after}")

    counts = {s: sum(r.get("validationStatus") == s for r in site) for s in ("green", "yellow", "red")}

    if args.write_report:
        lines = [
            "# Current Catalog Audit",
            "",
            "> Auto-generated by `tools/verify_catalog_invariants.py`. Do not maintain counts manually.",
            "",
            f"- Total catalog rows: **{len(site)}**",
            f"- Green: **{counts['green']}**",
            f"- Yellow: **{counts['yellow']}**",
            f"- Red: **{counts['red']}**",
            f"- Green rows with mandatory exact ordered Social Card proof: **{len(green)} / {counts['green']}**",
            f"- Conflicting shared Fragrantica IDs: **{sum(len(g) > 1 for g in fid_identities.values())}**",
            f"- Unauthorized identity/FID changes vs baseline: **{len(identity_changes)}**",
            "",
            "A green row is accepted only when its current Fragrantica ID has an `EXACT_ORDERED_MATCH` and the catalog note list is identical to the observed Social Card list in count, value, and order.",
            "",
        ]
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"rows": len(site), "counts": counts, "greenExactOrdered": len(green), "failures": len(failures)}, indent=2))
    if failures:
        for item in failures[:100]:
            print("FAIL:", item)
        raise SystemExit(f"Catalog invariant gate failed with {len(failures)} issue(s)")


if __name__ == "__main__":
    main()
