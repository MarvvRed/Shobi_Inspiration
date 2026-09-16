#!/usr/bin/env python3
"""Merge only exact multipass card proofs into the strict image audit."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
RECOVERY = ROOT / "database/audits/exact-card-proof-multipass.json"


def code(value):
    return str(value or "").strip().upper()


rows = json.loads(DB.read_text(encoding="utf-8-sig"))
audit = json.loads(AUDIT.read_text(encoding="utf-8"))
recovery = json.loads(RECOVERY.read_text(encoding="utf-8"))
by_code = {code(row.get("code")): row for row in rows}
audit_by_code = {code(item.get("code")): item for item in audit.get("rows", [])}
applied = []

for proof in recovery.get("rows", []):
    if proof.get("result") not in {"EXACT_ORDERED_MATCH_MULTIPASS", "EXACT_ORDERED_MATCH_RELAXED_MULTIPASS", "EXACT_ORDERED_MATCH_CONSENSUS_MULTIPASS"}:
        continue
    item = audit_by_code.get(code(proof.get("code")))
    row = by_code.get(code(proof.get("code")))
    if not item or not row:
        raise SystemExit(f"Missing exact-proof target: {proof.get('code')}")
    notes = list(row.get("fragranticaSocialCardNotes") or [])
    if item.get("result") != "READING_NOT_STRICT_ENOUGH":
        raise SystemExit(f"Unexpected existing audit result: {proof.get('code')}")
    if (str(proof.get("fragranticaId") or "") != str(row.get("fragranticaId") or "") or
            proof.get("catalogNotes") != notes or proof.get("observedNotes") != notes or
            not proof.get("card") or not (ROOT / proof["card"]).is_file()):
        raise SystemExit(f"Invalid exact-proof chain: {proof.get('code')}")
    selected = proof.get("selected") or {}
    item.update({
        "result": "EXACT_ORDERED_MATCH",
        "observedNotes": notes,
        "components": selected.get("components") or [],
        "proof": proof.get("proof"),
        "multipassEvidence": {"variant": selected.get("variant"), "psm": selected.get("psm")},
    })
    applied.append(code(proof.get("code")))

audit["results"] = dict(sorted(Counter(item.get("result") for item in audit.get("rows", [])).items()))
audit["multipassRecovery"] = {"applied": len(applied), "codes": applied}
AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"applied": len(applied), "results": audit["results"]}, ensure_ascii=False))
