#!/usr/bin/env python3
"""Apply only independently re-verified V6 Social Card sequences.

The neural report is a work list, never a proof by itself.  This writer
rechecks both reports, the live FID and the uniquely resolvable exact card
before changing an audit row.  It does not alter catalog notes.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
V6 = ROOT / "database/audits/current-yellow-neural-ocr-v6.json"
PROOF = ROOT / "database/audits/current-yellow-neural-ocr-v6-independent-verification.json"
CARDS = ROOT / "database/fragrantica/social-cards/images"


def code(value): return str(value or "").strip().upper()


def load(path): return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_exact_fid_card(shobi_code, fid):
    current = sorted({path for ext in ("jpeg", "jpg", "png", "webp") for path in CARDS.glob(f"current_{shobi_code}_{fid}.{ext}")})
    if len(current) == 1:
        return current[0], "CURRENT_EXACT_FID_CARD"
    archived = sorted({path for ext in ("jpeg", "jpg", "png", "webp") for path in CARDS.glob(f"*_{shobi_code}_{fid}.{ext}")})
    if not current and len(archived) == 1:
        return archived[0], "ARCHIVED_EXACT_CODE_AND_FID_CARD"
    return None, None


def neural_source_is_strict(source, fid, catalog, card, card_source):
    if (source.get("result") != "EXACT_NEURAL_SLOT_SEQUENCE" or
            str(source.get("fid") or "") != fid or
            list(source.get("catalog") or []) != catalog or
            list(source.get("observed") or []) != catalog or
            source.get("card") != card or source.get("cardSource") != card_source):
        return False
    slots = list(source.get("slots") or [])
    if len(slots) != len(catalog) or not catalog:
        return False
    for expected, slot in zip(catalog, slots):
        if (slot.get("winner") != expected or int(slot.get("exactReads") or 0) < 2 or
                list(slot.get("competitors") or [])):
            return False
    return True


def independent_layout_is_strict(proof, fid, catalog, card, card_source):
    evidence = proof.get("layoutEvidence") or {}
    return bool(
        proof.get("result") == "INDEPENDENT_EXACT_NEURAL_SEQUENCE"
        and proof.get("sourceV6Result") == "EXACT_NEURAL_SLOT_SEQUENCE"
        and str(proof.get("fid") or "") == fid
        and list(proof.get("catalog") or []) == catalog
        and list(proof.get("observed") or []) == catalog
        and proof.get("card") == card and proof.get("cardSource") == card_source
        and list(evidence.get("observed") or []) == catalog
        and int(evidence.get("exactReads") or 0) >= 1
        and not list(evidence.get("competitors") or [])
    )


def main():
    db = {code(row.get("code")): row for row in load(DB)}
    payload = load(AUDIT)
    audits = {code(row.get("code")): row for row in payload.get("rows", [])}
    sources = {code(row.get("code")): row for row in load(V6).get("rows", [])}
    proofs = {code(row.get("code")): row for row in load(PROOF).get("rows", [])}
    applied, skipped = [], []
    for shobi_code, proof in sorted(proofs.items()):
        if proof.get("result") != "INDEPENDENT_EXACT_NEURAL_SEQUENCE":
            continue
        row, audit, source = db.get(shobi_code), audits.get(shobi_code), sources.get(shobi_code)
        if not row or not audit or not source:
            skipped.append({"code": shobi_code, "reason": "missing_live_record"}); continue
        fid = str(row.get("fragranticaId") or "").strip()
        catalog = list(row.get("fragranticaSocialCardNotes") or [])
        card_path, card_source = resolve_exact_fid_card(shobi_code, fid)
        card = str(card_path.relative_to(ROOT)) if card_path else ""
        if audit.get("result") != "READING_NOT_STRICT_ENOUGH":
            skipped.append({"code": shobi_code, "reason": "unexpected_audit_state"}); continue
        if (str(audit.get("fragranticaId") or "") != fid or audit.get("catalogNotes") != catalog or
                not card or not neural_source_is_strict(source, fid, catalog, card, card_source) or
                not independent_layout_is_strict(proof, fid, catalog, card, card_source)):
            skipped.append({"code": shobi_code, "reason": "strict_proof_mismatch"}); continue
        audit.update({
            "result": "EXACT_ORDERED_MATCH",
            "observedNotes": catalog,
            "card": card,
            "v6IndependentLayoutProof": {
                "report": "database/audits/current-yellow-neural-ocr-v6-independent-verification.json",
                "sourceReport": "database/audits/current-yellow-neural-ocr-v6.json",
                "fid": fid, "card": card, "cardSource": card_source,
            },
        })
        applied.append(shobi_code)
    payload["rows"] = [audits[code(row.get("code"))] for row in payload.get("rows", [])]
    AUDIT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"applied": applied, "skipped": skipped}, ensure_ascii=False))


if __name__ == "__main__": main()
