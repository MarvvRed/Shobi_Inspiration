#!/usr/bin/env python3
"""Reuse an existing strict Social Card proof only for the identical Fragrantica source image.

Safety invariants:
- Recognition is never performed from catalog notes.
- Source proof must already be EXACT_ORDERED_MATCH.
- Source and target must have the same Fragrantica ID.
- Source and target Social Card bytes must have the same SHA-256.
- The independently observed source sequence is transferred first and only then
  compared to the target catalog sequence.
- No catalog note data is rewritten.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database/catalog/database_complete.json"
AUDIT = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
IMGDIR = ROOT / "database/fragrantica/social-cards/images"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def norm_code(value):
    return str(value or "").strip().upper()


def fid_of(row):
    for key in ("fragranticaId", "fragranticaID", "fragrantica_id", "fid", "fragranticaFid"):
        v = row.get(key)
        if v is not None and str(v).strip():
            m = re.search(r"\d+", str(v))
            if m:
                return m.group(0)
    for key in ("fragranticaUrl", "fragranticaURL", "urlFragrantica"):
        v = str(row.get(key) or "")
        m = re.search(r"-(\d+)\.html(?:$|[?#])", v)
        if m:
            return m.group(1)
    return None


def expected_notes(row):
    for key in ("fragranticaSocialCardNotes", "mainNotes", "notes"):
        v = row.get(key)
        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            return [x.strip() for x in v if x.strip()]
    return []


def find_card(code, fid):
    if not code or not fid:
        return None
    # Exact current naming convention first.
    for ext in ("jpeg", "jpg", "png", "webp"):
        p = IMGDIR / f"current_{code}_{fid}.{ext}"
        if p.exists():
            return p
    # Conservative fallback: exact code/FID tokens only.
    matches = []
    for p in IMGDIR.glob("*"):
        if not p.is_file():
            continue
        stem = p.stem.upper()
        if code in stem and re.search(rf"(?:^|[_-]){re.escape(fid)}(?:$|[_-])", stem):
            matches.append(p)
    return matches[0] if len(matches) == 1 else None


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    db = load_json(DB)
    audit = load_json(AUDIT)
    rows = audit.get("rows", []) if isinstance(audit, dict) else audit
    catalog = {norm_code(r.get("code")): r for r in db if isinstance(r, dict)}

    card_cache = {}
    def card_info(code):
        row = catalog.get(code)
        if not row:
            return None
        fid = fid_of(row)
        card = find_card(code, fid)
        if not fid or not card:
            return None
        key = str(card)
        digest = card_cache.setdefault(key, sha256(card))
        return fid, card, digest

    strict_by_identity = defaultdict(list)
    for item in rows:
        if item.get("result") != "EXACT_ORDERED_MATCH":
            continue
        code = norm_code(item.get("code"))
        observed = item.get("observedNotes")
        if not isinstance(observed, list) or not observed:
            continue
        info = card_info(code)
        if not info:
            continue
        fid, card, digest = info
        # Source itself must remain self-consistent with its catalog row.
        if observed != expected_notes(catalog.get(code, {})):
            continue
        strict_by_identity[(fid, digest)].append({
            "code": code,
            "observedNotes": observed,
            "card": str(card.relative_to(ROOT)),
        })

    recovered = []
    rejected = Counter()
    examined = 0
    for item in rows:
        if item.get("result") == "EXACT_ORDERED_MATCH":
            continue
        code = norm_code(item.get("code"))
        row = catalog.get(code)
        if not row:
            rejected["missing_catalog_row"] += 1
            continue
        info = card_info(code)
        if not info:
            rejected["no_exact_local_card"] += 1
            continue
        fid, card, digest = info
        sources = [s for s in strict_by_identity.get((fid, digest), []) if s["code"] != code]
        if not sources:
            rejected["no_identical_strict_source"] += 1
            continue
        examined += 1
        sequences = {tuple(s["observedNotes"]) for s in sources}
        if len(sequences) != 1:
            rejected["strict_sources_disagree"] += 1
            continue
        observed = list(next(iter(sequences)))
        expected = expected_notes(row)
        if not expected:
            rejected["target_has_no_expected_sequence"] += 1
            continue
        if observed != expected:
            rejected["target_sequence_not_exact"] += 1
            continue

        item.update({
            "result": "EXACT_ORDERED_MATCH",
            "observedNotes": observed,
            "proof": "IDENTICAL_SOCIAL_CARD_SHA256_AND_FID_REUSE_FROM_EXISTING_STRICT_EXACT_ORDERED_PROOF; CATALOG_NOT_USED_FOR_RECOGNITION",
            "identicalCardProofReuse": {
                "fragranticaId": fid,
                "sha256": digest,
                "targetCard": str(card.relative_to(ROOT)),
                "sourceCodes": [s["code"] for s in sources],
                "sourceCards": sorted({s["card"] for s in sources}),
                "observedNotes": observed,
            },
        })
        recovered.append(code)

    if isinstance(audit, dict):
        audit["results"] = dict(sorted(Counter(x.get("result") for x in rows).items()))
        audit["identicalSocialCardProofReuse"] = {
            "examined": examined,
            "recovered": len(recovered),
            "codes": recovered,
            "rejected": dict(sorted(rejected.items())),
        }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "strictIdentities": len(strict_by_identity),
        "examined": examined,
        "recovered": len(recovered),
        "codes": recovered,
        "results": audit.get("results", {}) if isinstance(audit, dict) else {},
        "rejected": dict(sorted(rejected.items())),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
