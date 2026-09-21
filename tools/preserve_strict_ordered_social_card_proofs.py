#!/usr/bin/env python3
"""Preserve still-valid strict Social Card proofs across a full audit rebuild.

The image audit intentionally starts from pixels on every publication.  Some
older strict recovery methods are expensive and are not part of that immediate
rebuild, so replacing the report wholesale would silently demote already
certified rows.  This bridge does *not* create evidence: it carries forward an
existing ``EXACT_ORDERED_MATCH`` only when its complete identity and sequence
chain is unchanged and the cited Social Card file still exists.

It is generic (no code or perfume allowlist), rejects deprecated fast proof
markers, and records the preserved source in the rebuilt audit.  A changed FID,
catalog sequence, card path, missing evidence, or non-exact prior result is
never preserved.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
BASELINE = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.pre-rebuild.json"
FAST_MARKER = "CURRENT_FID_FAST_EXACT_PROOF"


def code(value):
    return str(value or "").strip().upper()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def exact_card_exists(path_value, fid):
    path = ROOT / str(path_value or "")
    if not path.is_file():
        return False
    # Both current and archived naming schemes bind the final filename token to
    # the Fragrantica ID; do not accept merely a code-name substring.
    return bool(re.search(rf"(?:^|[_-]){re.escape(fid)}(?:\.[^.]+)?$", path.name))


def durable_strict_proof(item):
    proof = str(item.get("proof") or "").strip()
    if not proof or FAST_MARKER in proof.upper():
        return False
    # The existing audit is accepted only for its explicit strict Social Card
    # proof classes.  This is a generic proof taxonomy, never a list of codes.
    required = ("EXACT", "SOCIAL_CARD")
    return all(token in proof.upper() for token in required) or (
        "EXACT_HIGH_CONFIDENCE_LABELS" in proof.upper()
        or "ALL_LABELS_EXACT_HIGH_CONFIDENCE" in proof.upper()
        or "STRICT_EXACT_MAJORITY" in proof.upper()
        or "TWO_INDEPENDENT_EXACT_LABEL_READS" in proof.upper()
    )


def main():
    if not BASELINE.is_file():
        raise SystemExit(f"Missing pre-rebuild strict audit snapshot: {BASELINE}")
    db = load(DB)
    audit = load(AUDIT)
    baseline = load(BASELINE)
    db_by_code = {code(row.get("code")): row for row in db}
    current_by_code = {code(row.get("code")): row for row in audit.get("rows", [])}
    preserved, rejected = [], Counter()

    for previous in baseline.get("rows", []):
        if previous.get("result") != "EXACT_ORDERED_MATCH":
            continue
        shobi_code = code(previous.get("code"))
        current = current_by_code.get(shobi_code)
        row = db_by_code.get(shobi_code)
        if not current or not row:
            rejected["missing_current_row"] += 1
            continue
        if current.get("result") == "EXACT_ORDERED_MATCH":
            continue
        fid = str(row.get("fragranticaId") or "").strip()
        notes = list(row.get("fragranticaSocialCardNotes") or [])
        if not fid or not notes:
            rejected["missing_current_fid_or_notes"] += 1
            continue
        if not durable_strict_proof(previous):
            rejected["prior_proof_not_durable_strict"] += 1
            continue
        if (str(previous.get("fragranticaId") or "") != fid or
                list(previous.get("catalogNotes") or []) != notes or
                list(previous.get("observedNotes") or []) != notes):
            rejected["prior_identity_or_sequence_changed"] += 1
            continue
        if (str(current.get("fragranticaId") or "") != fid or
                list(current.get("catalogNotes") or []) != notes):
            rejected["rebuilt_identity_or_sequence_changed"] += 1
            continue
        if not exact_card_exists(previous.get("card"), fid):
            rejected["prior_exact_card_missing"] += 1
            continue
        current.update({
            "result": "EXACT_ORDERED_MATCH",
            "observedNotes": notes,
            "card": previous["card"],
            "proof": previous["proof"],
            "components": previous.get("components", []),
            "preservedStrictProof": {
                "source": "pre-rebuild social-card-ordered-image-audit.json",
                "fragranticaId": fid,
                "card": previous["card"],
                "sequence": notes,
                "proof": previous["proof"],
                "continuityChecks": ["same_code", "same_fid", "same_catalog_sequence", "same_observed_sequence", "exact_card_file_exists"],
            },
        })
        preserved.append(shobi_code)

    audit["results"] = dict(sorted(Counter(row.get("result") for row in audit.get("rows", [])).items()))
    audit["strictProofContinuity"] = {
        "preserved": len(preserved),
        "codes": sorted(preserved),
        "rejected": dict(sorted(rejected.items())),
        "policy": "Existing strict exact proof is retained only under unchanged code/FID/catalog/observed/card evidence. No new recognition or catalog rewrite occurs.",
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"preserved": len(preserved), "results": audit["results"], "rejected": dict(sorted(rejected.items()))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
