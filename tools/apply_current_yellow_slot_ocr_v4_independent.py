#!/usr/bin/env python3
"""Apply only independently re-verified V4 slot proofs to the ordered audit."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
ORDERED_AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
PROOF = ROOT / "database/audits/current-yellow-slot-ocr-v4-independent-verification.json"


def code(value):
    return str(value or "").strip().upper()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def proof_is_complete(proof, row):
    fid = str(row.get("fragranticaId") or "").strip()
    notes = list(row.get("fragranticaSocialCardNotes") or [])
    card = str(proof.get("card") or "")
    if (proof.get("result") != "INDEPENDENT_EXACT_SLOT_SEQUENCE" or
            str(proof.get("fid") or "") != fid or proof.get("catalog") != notes or
            proof.get("observed") != notes or not notes or not card or not (ROOT / card).is_file()):
        return False
    exact_cards = proof.get("currentExactCardCandidates") or []
    if exact_cards != [card]:
        return False
    winners = []
    for slot in proof.get("slots") or []:
        if slot.get("strong"):
            winner = slot.get("winner")
            exact_reads = [read for read in slot.get("reads") or [] if read.get("eligible") and read.get("exact") and read.get("candidate") == winner]
            exact_modes = {(read.get("family"), read.get("psm")) for read in exact_reads if read.get("family") and read.get("psm") is not None}
            competitors = [read for read in slot.get("reads") or [] if read.get("eligible") and read.get("candidate") and read.get("candidate") != winner]
            if not winner or len(exact_reads) < 2 or len(exact_modes) < 2 or competitors:
                return False
            winners.append(winner)
        elif any(read.get("eligible") for read in slot.get("reads") or []):
            return False
    return winners == notes


def main():
    rows = load(DB)
    audit = load(ORDERED_AUDIT)
    report = load(PROOF)
    rows_by_code = {code(row.get("code")): row for row in rows}
    audit_by_code = {code(row.get("code")): row for row in audit.get("rows", [])}
    applied = []
    for proof in report.get("rows", []):
        shobi_code = code(proof.get("code"))
        row = rows_by_code.get(shobi_code)
        item = audit_by_code.get(shobi_code)
        if not row or not item:
            raise SystemExit(f"Missing V4 independent target: {shobi_code}")
        if item.get("result") != "READING_NOT_STRICT_ENOUGH":
            raise SystemExit(f"V4 independent target is no longer unresolved: {shobi_code}")
        if not proof_is_complete(proof, row):
            raise SystemExit(f"V4 independent proof chain is incomplete: {shobi_code}")
        if (str(item.get("fragranticaId") or "") != str(proof.get("fid") or "") or
                list(item.get("catalogNotes") or []) != list(proof.get("catalog") or [])):
            raise SystemExit(f"V4 independent audit/card/FID mismatch: {shobi_code}")
        item.update({
            "result": "EXACT_ORDERED_MATCH",
            "observedNotes": list(proof["observed"]),
            "card": proof["card"],
            "proof": proof["proof"],
            "v4IndependentSlotProof": {
                "report": "database/audits/current-yellow-slot-ocr-v4-independent-verification.json",
                "card": proof["card"],
                "fid": proof["fid"],
                "slotCount": len(proof["slots"]),
            },
        })
        applied.append(shobi_code)
    audit["results"] = dict(sorted(Counter(item.get("result") for item in audit.get("rows", [])).items()))
    audit["v4IndependentSlotRecovery"] = {"applied": len(applied), "codes": sorted(applied)}
    ORDERED_AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"applied": len(applied), "codes": sorted(applied), "results": audit["results"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
