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
V2_LABEL_PILOT = ROOT / "database/audits/label-ocr-pilot.json"
V2_EXACT_VALIDATION = ROOT / "database/audits/v2-exact-validation.json"
CURRENT_YELLOW_V2_PILOT = ROOT / "database/audits/current-yellow-label-ocr-v2.json"
CURRENT_YELLOW_V2_VALIDATION = ROOT / "database/audits/current-yellow-v2-exact-validation.json"
NEAR_PASS_REFINEMENT = ROOT / "database/audits/current-yellow-near-pass-ocr-refinement.json"
V4_INDEPENDENT_SLOT_VERIFICATION = ROOT / "database/audits/current-yellow-slot-ocr-v4-independent-verification.json"
REPORT = ROOT / "database/audits/CURRENT-CATALOG-AUDIT.md"
ALLOWLIST = ROOT / "database/audits/identity-change-allowlist.json"
CRITICAL_FIXES = ROOT / "database/audits/critical-identity-fixes.json"
CRITICAL_REGISTRY = ROOT / "database/audits/critical-identity-regression-registry.json"
SHARED_FID_REGISTRY = ROOT / "database/audits/shared-fid-alias-registry.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def row_code(row):
    return str(row.get("code") or "").strip().upper()


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


def v2_strong_ordered_evidence(row, fid, notes, current_audit, v2_pilot, v2_validation):
    """Independently recompute the conservative V2 proof instead of trusting its status field."""
    c = row_code(row)
    proof = v2_validation.get(c)
    pilot = v2_pilot.get(c)
    ev = current_audit.get(c)
    if not proof or not pilot or not ev:
        return False
    if proof.get("status") != "STRONG_EXACT" or pilot.get("result") != "EXACT_LABEL_SEQUENCE":
        return False
    if str(proof.get("fid") or "") != fid or str(pilot.get("fid") or "") != fid:
        return False
    if str(ev.get("fragranticaId") or "").strip() != fid:
        return False
    card = str(ev.get("card") or "").strip()
    if not card or not (ROOT / card).is_file():
        return False
    if list(pilot.get("catalog") or []) != list(notes) or list(pilot.get("observed") or []) != list(notes):
        return False
    details = list(pilot.get("details") or [])
    if not notes or len(details) != len(notes):
        return False
    for expected, detail in zip(notes, details):
        winner = detail.get("note")
        if not detail.get("confident") or winner != expected:
            return False
        reads = list(detail.get("reads") or [])
        winner_exact = [
            read for read in reads
            if read.get("eligible") and read.get("exact") and read.get("candidate") == winner
        ]
        exact_crop = [read for read in winner_exact if read.get("variant") != "locator"]
        competing = [
            read for read in reads
            if read.get("eligible") and read.get("candidate") and read.get("candidate") != winner
        ]
        if len(winner_exact) < 2 or not exact_crop or competing:
            return False
    return True



def near_pass_supplemental_evidence(row, fid, notes, current_audit, pilot_map, validation_map, refinement_map):
    """Independently recompute the targeted one-label supplemental proof."""
    c = row_code(row)
    pilot = pilot_map.get(c)
    validation = validation_map.get(c)
    refinement = refinement_map.get(c)
    ev = current_audit.get(c)
    if not pilot or not validation or not refinement or not ev:
        return False
    if refinement.get("result") != "SUPPLEMENTAL_STRONG_EXACT":
        return False
    if pilot.get("result") != "EXACT_LABEL_SEQUENCE" or validation.get("status") != "REVIEW":
        return False
    if any(str(x.get("fid") or "") != fid for x in (pilot, validation, refinement)):
        return False
    if str(ev.get("fragranticaId") or "").strip() != fid:
        return False
    card = str(ev.get("card") or "").strip()
    if not card or not (ROOT / card).is_file():
        return False
    if list(pilot.get("catalog") or []) != list(notes) or list(pilot.get("observed") or []) != list(notes):
        return False
    details = list(pilot.get("details") or [])
    labels = list(validation.get("labels") or [])
    if not notes or len(details) != len(notes) or len(labels) != len(notes):
        return False
    failed = [lab for lab in labels if not lab.get("ok")]
    if len(failed) != 1:
        return False
    failed_note = failed[0].get("note")
    if refinement.get("failedNote") != failed_note:
        return False
    refined = refinement.get("refined") or {}
    if refined.get("expected") != failed_note:
        return False
    rreads = list(refined.get("reads") or [])
    rexact = [r for r in rreads if r.get("eligible") and r.get("exact") and r.get("candidate") == failed_note]
    rcompeting = [r for r in rreads if r.get("eligible") and r.get("candidate") and r.get("candidate") != failed_note]
    if len(rexact) < 2 or rcompeting:
        return False
    for expected, detail, label in zip(notes, details, labels):
        if detail.get("note") != expected or label.get("note") != expected or not detail.get("confident"):
            return False
        if expected == failed_note:
            continue
        if not label.get("ok"):
            return False
        reads = list(detail.get("reads") or [])
        winner_exact = [r for r in reads if r.get("eligible") and r.get("exact") and r.get("candidate") == expected]
        exact_crop = [r for r in winner_exact if r.get("variant") != "locator"]
        competing = [r for r in reads if r.get("eligible") and r.get("candidate") and r.get("candidate") != expected]
        if len(winner_exact) < 2 or not exact_crop or competing:
            return False
    return True


def v4_independent_slot_evidence(row, fid, notes, current_audit, proof_map):
    """Independently revalidate every stored V4 slot proof field used by green."""
    c = row_code(row)
    proof = proof_map.get(c)
    audit = current_audit.get(c)
    if not proof or not audit:
        return False
    if proof.get("result") != "INDEPENDENT_EXACT_SLOT_SEQUENCE" or proof.get("sourceV4Result") != "EXACT_SLOT_SEQUENCE":
        return False
    if str(proof.get("fid") or "") != fid or proof.get("catalog") != notes or proof.get("observed") != notes or not notes:
        return False
    card = str(proof.get("card") or "")
    linked = audit.get("v4IndependentSlotProof") or {}
    if (not card or not (ROOT / card).is_file() or audit.get("result") != "EXACT_ORDERED_MATCH" or
            str(audit.get("fragranticaId") or "") != fid or audit.get("catalogNotes") != notes or
            audit.get("observedNotes") != notes or str(audit.get("card") or "") != card or
            linked.get("report") != "database/audits/current-yellow-slot-ocr-v4-independent-verification.json" or
            str(linked.get("fid") or "") != fid or str(linked.get("card") or "") != card or
            proof.get("currentExactCardCandidates") != [card]):
        return False
    observed = []
    for slot in proof.get("slots") or []:
        reads = list(slot.get("reads") or [])
        if slot.get("strong"):
            winner = slot.get("winner")
            exact = [read for read in reads if read.get("eligible") and read.get("exact") and read.get("candidate") == winner]
            configurations = {(read.get("family"), read.get("psm")) for read in exact if read.get("family") and read.get("psm") is not None}
            competitors = [read for read in reads if read.get("eligible") and read.get("candidate") and read.get("candidate") != winner]
            if not winner or len(exact) < 2 or len(configurations) < 2 or competitors:
                return False
            observed.append(winner)
        elif any(read.get("eligible") for read in reads):
            return False
    return observed == notes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-ref", help="Git ref whose database_complete.json is the identity baseline")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    db = load(DB)
    site = load(SITE)
    final = load(FINAL)
    audit_rows = load(ORDERED_AUDIT).get("rows", [])
    v2_pilot_rows = load(V2_LABEL_PILOT).get("rows", []) if V2_LABEL_PILOT.is_file() else []
    v2_validation_rows = load(V2_EXACT_VALIDATION).get("rows", []) if V2_EXACT_VALIDATION.is_file() else []
    cy_pilot_rows = load(CURRENT_YELLOW_V2_PILOT).get("rows", []) if CURRENT_YELLOW_V2_PILOT.is_file() else []
    cy_validation_rows = load(CURRENT_YELLOW_V2_VALIDATION).get("rows", []) if CURRENT_YELLOW_V2_VALIDATION.is_file() else []
    refinement_rows = load(NEAR_PASS_REFINEMENT).get("rows", []) if NEAR_PASS_REFINEMENT.is_file() else []
    v4_independent_rows = load(V4_INDEPENDENT_SLOT_VERIFICATION).get("rows", []) if V4_INDEPENDENT_SLOT_VERIFICATION.is_file() else []
    by_code = {row_code(r): r for r in db}
    site_by_code = {row_code(r): r for r in site}
    final_by_code = {row_code(r): r for r in final}
    audit_by_code = {row_code(r): r for r in audit_rows}
    v2_pilot = {row_code(r): r for r in v2_pilot_rows}
    v2_validation = {row_code(r): r for r in v2_validation_rows}
    cy_pilot = {row_code(r): r for r in cy_pilot_rows}
    cy_validation = {row_code(r): r for r in cy_validation_rows}
    refinement = {row_code(r): r for r in refinement_rows}
    v4_independent = {row_code(r): r for r in v4_independent_rows}

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
    green_v2 = []
    green_supplemental = []
    green_v4_independent = []
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
        strict = bool(
            ev
            and not ev.get("v4IndependentSlotProof")
            and ev.get("result") == "EXACT_ORDERED_MATCH"
            and str(ev.get("fragranticaId") or "").strip() == fid
            and ev.get("catalogNotes") == notes
            and ev.get("observedNotes") == notes
            and str(ev.get("card") or "").strip()
            and (ROOT / str(ev.get("card") or "").strip()).is_file()
        )
        v2 = v2_strong_ordered_evidence(row, fid, notes, audit_by_code, v2_pilot, v2_validation)
        supplemental = near_pass_supplemental_evidence(row, fid, notes, audit_by_code, cy_pilot, cy_validation, refinement)
        v4 = v4_independent_slot_evidence(row, fid, notes, audit_by_code, v4_independent)
        if not strict and not v2 and not supplemental and not v4:
            failures.append(f"{code}: green without strict whole-card, revalidated STRONG_EXACT V2, supplemental one-label proof, or independent V4 slot proof")
            continue
        if v2 and not strict:
            green_v2.append(code)
        if supplemental and not strict and not v2:
            green_supplemental.append(code)
        if v4 and not strict and not v2 and not supplemental:
            green_v4_independent.append(code)

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
            old = {row_code(r): r for r in baseline}
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
            f"- Green rows with mandatory ordered Social Card proof: **{len(green)} / {counts['green']}**",
            f"- Green rows using independently revalidated STRONG_EXACT V2 proof: **{len(green_v2)}**",
            f"- Green rows using independently revalidated supplemental one-label OCR proof: **{len(green_supplemental)}**",
            f"- Green rows using independently revalidated V4 current-card slot proof: **{len(green_v4_independent)}**",
            f"- Approved shared-FID alias groups present: **{len(approved_shared_present)}**",
            f"- Unapproved shared FIDs: **{len(unapproved_shared)}**",
            f"- Unauthorized identity/FID changes vs baseline: **{len(identity_changes)}**", "",
            "A green row is accepted only when the current FID and ordered note sequence are proven by strict whole-card `EXACT_ORDERED_MATCH`, independently revalidated `STRONG_EXACT` V2, the independently revalidated one-label supplemental OCR path, or a separate V4 current-card slot proof. The V4 route requires the original V4 result only as a work-list selector, then independently re-resolves the current exact-FID card and requires the full pixel-derived sequence, two exact OCR configurations per occupied slot, and zero competing eligible reads.", "",
            "Shared Fragrantica IDs are allowed only when the exact set of Shobi codes is registered in `shared-fid-alias-registry.json`; any new member or new shared FID fails CI.", ""
        ]), encoding="utf-8")

    print(json.dumps({
        "rows": len(site), "counts": counts, "greenOrderedProof": len(green), "greenV2Strong": len(green_v2), "greenSupplementalStrong": len(green_supplemental), "greenV4IndependentSlot": len(green_v4_independent),
        "approvedSharedFidGroups": len(approved_shared_present), "unapprovedSharedFids": len(unapproved_shared),
        "protectedIdentities": len(protected), "unauthorizedIdentityChanges": len(identity_changes), "failures": len(failures)
    }, indent=2))
    if failures:
        for item in failures[:100]: print("FAIL:", item)
        raise SystemExit(f"Catalog invariant gate failed with {len(failures)} issue(s)")


if __name__ == "__main__":
    main()
