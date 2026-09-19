#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'tools/build_validation_audit.py'
VERIFIER=ROOT/'tools/verify_catalog_invariants.py'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'missing anchor: {label}')
    if text.count(old) != 1:
        raise SystemExit(f'non-unique anchor: {label}')
    return text.replace(old,new,1)


def patch_builder():
    p=BUILDER; t=p.read_text(encoding='utf-8')
    t=replace_once(t,
        'V2_EXACT_VALIDATION = ROOT / "database/audits/v2-exact-validation.json"\n',
        'V2_EXACT_VALIDATION = ROOT / "database/audits/v2-exact-validation.json"\nCURRENT_YELLOW_V2_PILOT = ROOT / "database/audits/current-yellow-label-ocr-v2.json"\nCURRENT_YELLOW_V2_VALIDATION = ROOT / "database/audits/current-yellow-v2-exact-validation.json"\nNEAR_PASS_REFINEMENT = ROOT / "database/audits/current-yellow-near-pass-ocr-refinement.json"\n',
        'builder constants')
    t=replace_once(t,
        'v2_validation = {row_code(item): item for item in v2_validation_payload.get("rows", [])}\n',
        'v2_validation = {row_code(item): item for item in v2_validation_payload.get("rows", [])}\ncurrent_yellow_v2_pilot_payload = json.loads(CURRENT_YELLOW_V2_PILOT.read_text(encoding="utf-8")) if CURRENT_YELLOW_V2_PILOT.is_file() else {}\ncurrent_yellow_v2_validation_payload = json.loads(CURRENT_YELLOW_V2_VALIDATION.read_text(encoding="utf-8")) if CURRENT_YELLOW_V2_VALIDATION.is_file() else {}\nnear_pass_refinement_payload = json.loads(NEAR_PASS_REFINEMENT.read_text(encoding="utf-8")) if NEAR_PASS_REFINEMENT.is_file() else {}\ncurrent_yellow_v2_pilot = {row_code(item): item for item in current_yellow_v2_pilot_payload.get("rows", [])}\ncurrent_yellow_v2_validation = {row_code(item): item for item in current_yellow_v2_validation_payload.get("rows", [])}\nnear_pass_refinement = {row_code(item): item for item in near_pass_refinement_payload.get("rows", [])}\n',
        'builder payload maps')
    anchor='\ndef exact_ordered_card_evidence(row, fid, notes):\n'
    func=r'''
def near_pass_supplemental_evidence(row, fid, notes):
    """Recompute targeted supplemental proof for one previously weak V2 label.

    The stored SUPPLEMENTAL_STRONG_EXACT result is only a hint. All original
    strong labels are rechecked from the current-yellow V2 pilot, while the one
    failed label must have >=2 new exact crop reads and zero competing eligible
    reads in the refinement report. Current FID, ordered sequence and archived
    Social Card must still match the live row.
    """
    c = row_code(row)
    pilot = current_yellow_v2_pilot.get(c)
    validation = current_yellow_v2_validation.get(c)
    refinement = near_pass_refinement.get(c)
    current_audit = ordered_card_audit.get(c)
    if not pilot or not validation or not refinement or not current_audit:
        return False
    if refinement.get("result") != "SUPPLEMENTAL_STRONG_EXACT":
        return False
    if pilot.get("result") != "EXACT_LABEL_SEQUENCE" or validation.get("status") != "REVIEW":
        return False
    if any(str(x.get("fid") or "") != fid for x in (pilot, validation, refinement)):
        return False
    if str(current_audit.get("fragranticaId") or "") != fid:
        return False
    card = str(current_audit.get("card") or "")
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

'''
    t=replace_once(t,anchor,'\n'+func+'def exact_ordered_card_evidence(row, fid, notes):\n','builder supplemental function')
    t=replace_once(t,
        '    return strict_whole_card or v2_strong_ordered_evidence(row, fid, notes)\n',
        '    return strict_whole_card or v2_strong_ordered_evidence(row, fid, notes) or near_pass_supplemental_evidence(row, fid, notes)\n',
        'builder evidence return')
    p.write_text(t,encoding='utf-8')


def patch_verifier():
    p=VERIFIER; t=p.read_text(encoding='utf-8')
    t=replace_once(t,
        'V2_EXACT_VALIDATION = ROOT / "database/audits/v2-exact-validation.json"\n',
        'V2_EXACT_VALIDATION = ROOT / "database/audits/v2-exact-validation.json"\nCURRENT_YELLOW_V2_PILOT = ROOT / "database/audits/current-yellow-label-ocr-v2.json"\nCURRENT_YELLOW_V2_VALIDATION = ROOT / "database/audits/current-yellow-v2-exact-validation.json"\nNEAR_PASS_REFINEMENT = ROOT / "database/audits/current-yellow-near-pass-ocr-refinement.json"\n',
        'verifier constants')
    anchor='\ndef main():\n'
    func=r'''
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

'''
    t=replace_once(t,anchor,'\n'+func+'def main():\n','verifier supplemental function')
    t=replace_once(t,
        '    v2_validation_rows = load(V2_EXACT_VALIDATION).get("rows", []) if V2_EXACT_VALIDATION.is_file() else []\n',
        '    v2_validation_rows = load(V2_EXACT_VALIDATION).get("rows", []) if V2_EXACT_VALIDATION.is_file() else []\n    cy_pilot_rows = load(CURRENT_YELLOW_V2_PILOT).get("rows", []) if CURRENT_YELLOW_V2_PILOT.is_file() else []\n    cy_validation_rows = load(CURRENT_YELLOW_V2_VALIDATION).get("rows", []) if CURRENT_YELLOW_V2_VALIDATION.is_file() else []\n    refinement_rows = load(NEAR_PASS_REFINEMENT).get("rows", []) if NEAR_PASS_REFINEMENT.is_file() else []\n',
        'verifier load rows')
    t=replace_once(t,
        '    v2_validation = {row_code(r): r for r in v2_validation_rows}\n',
        '    v2_validation = {row_code(r): r for r in v2_validation_rows}\n    cy_pilot = {row_code(r): r for r in cy_pilot_rows}\n    cy_validation = {row_code(r): r for r in cy_validation_rows}\n    refinement = {row_code(r): r for r in refinement_rows}\n',
        'verifier maps')
    t=replace_once(t,
        '    green_v2 = []\n',
        '    green_v2 = []\n    green_supplemental = []\n',
        'verifier supplemental list')
    t=replace_once(t,
        '        v2 = v2_strong_ordered_evidence(row, fid, notes, audit_by_code, v2_pilot, v2_validation)\n        if not strict and not v2:\n            failures.append(f"{code}: green without strict whole-card or revalidated STRONG_EXACT V2 proof")\n            continue\n        if v2 and not strict:\n            green_v2.append(code)\n',
        '        v2 = v2_strong_ordered_evidence(row, fid, notes, audit_by_code, v2_pilot, v2_validation)\n        supplemental = near_pass_supplemental_evidence(row, fid, notes, audit_by_code, cy_pilot, cy_validation, refinement)\n        if not strict and not v2 and not supplemental:\n            failures.append(f"{code}: green without strict whole-card, revalidated STRONG_EXACT V2, or revalidated supplemental one-label proof")\n            continue\n        if v2 and not strict:\n            green_v2.append(code)\n        if supplemental and not strict and not v2:\n            green_supplemental.append(code)\n',
        'verifier green gate')
    t=replace_once(t,
        '            f"- Green rows using independently revalidated STRONG_EXACT V2 proof: **{len(green_v2)}**",\n',
        '            f"- Green rows using independently revalidated STRONG_EXACT V2 proof: **{len(green_v2)}**",\n            f"- Green rows using independently revalidated supplemental one-label OCR proof: **{len(green_supplemental)}**",\n',
        'verifier report line')
    t=replace_once(t,
        '            "A green row is accepted only when the current FID and ordered note sequence are proven either by the strict whole-card `EXACT_ORDERED_MATCH` path or by independently revalidated `STRONG_EXACT` V2 per-label OCR evidence with multiple exact reads, a real crop read, and zero competing eligible candidates for every note.", "",\n',
        '            "A green row is accepted only when the current FID and ordered note sequence are proven by strict whole-card `EXACT_ORDERED_MATCH`, independently revalidated `STRONG_EXACT` V2, or the independently revalidated one-label supplemental OCR path. Supplemental proof preserves the same exact-read and zero-competitor requirements and may replace only one previously weak label while every other label must still satisfy the original strong V2 gate.", "",\n',
        'verifier report prose')
    t=replace_once(t,
        '        "rows": len(site), "counts": counts, "greenOrderedProof": len(green), "greenV2Strong": len(green_v2),\n',
        '        "rows": len(site), "counts": counts, "greenOrderedProof": len(green), "greenV2Strong": len(green_v2), "greenSupplementalStrong": len(green_supplemental),\n',
        'verifier json output')
    p.write_text(t,encoding='utf-8')


if __name__=='__main__':
    patch_builder()
    patch_verifier()
    print('patched builder and independent verifier for supplemental near-pass proof')
