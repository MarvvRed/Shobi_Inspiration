#!/usr/bin/env python3
"""Build the versioned universal canonical Shobi database from audited outputs."""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL_DB = ROOT / "database/catalog/database_final_perfume_only.json"
CERTIFICATE = ROOT / "database/catalog/final-perfume-catalog-certification.json"
AUDIT = ROOT / "database/audits/CURRENT-CATALOG-AUDIT.md"
OUT_DIR = ROOT / "database/canonical"
OUT = OUT_DIR / "shobi-universal-v1.json"
README = OUT_DIR / "README.md"


def code(row: dict) -> str:
    return str(row.get("code") or "").strip().upper()


def main() -> None:
    rows = json.loads(FINAL_DB.read_text(encoding="utf-8-sig"))
    certificate = json.loads(CERTIFICATE.read_text(encoding="utf-8"))

    expected = int(certificate["finalRows"])
    if len(rows) != expected:
        raise SystemExit(f"Canonical source has {len(rows)} rows; certificate requires {expected}")

    codes = [code(row) for row in rows]
    product_ids = [str(row.get("prestashopProductId") or "").strip() for row in rows]
    shobi_urls = [str(row.get("shobiUrl") or "").strip() for row in rows]
    if not all(codes) or len(set(codes)) != expected:
        raise SystemExit("Canonical source has missing or duplicate Shobi codes")
    if not all(product_ids) or len(set(product_ids)) != expected:
        raise SystemExit("Canonical source has missing or duplicate Shobi product IDs")
    if not all(shobi_urls) or len(set(shobi_urls)) != expected:
        raise SystemExit("Canonical source has missing or duplicate Shobi URLs")

    statuses = Counter(str(row.get("validationStatus") or "").strip().lower() for row in rows)
    invalid_statuses = set(statuses) - {"green", "yellow", "red"}
    if invalid_statuses:
        raise SystemExit(f"Invalid canonical validation statuses: {sorted(invalid_statuses)}")

    green_failures = []
    for row in rows:
        if str(row.get("validationStatus") or "").lower() != "green":
            continue
        checks = row.get("validationChecks") or (row.get("validationAudit") or {}).get("checks") or {}
        if not checks or not all(bool(value) for value in checks.values()):
            green_failures.append(code(row))
    if green_failures:
        raise SystemExit(f"Green rows without complete audit checks: {green_failures[:20]}")

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    database = {
        "schema": "shobi-universal-canonical/v1",
        "title": "Shobi Universal Canonical Database",
        "generatedAt": generated_at,
        "sourceCommit": os.environ.get("GITHUB_SHA") or None,
        "canonicalRule": (
            "A green record is admitted only with the audited Shobi identity, "
            "matching Fragrantica FID/URL, exact Social Card and ordered notes, "
            "plus validated icons, gender and season. Yellow records are retained "
            "with their evidence state and are never promoted by inference."
        ),
        "source": {
            "records": "database/catalog/database_final_perfume_only.json",
            "certificate": "database/catalog/final-perfume-catalog-certification.json",
            "independentAudit": "database/audits/CURRENT-CATALOG-AUDIT.md",
        },
        "summary": {
            "total": expected,
            "green": statuses["green"],
            "yellow": statuses["yellow"],
            "red": statuses["red"],
            "directFragranticaIdentityProofRows": int(certificate["directFragranticaIdentityProofRows"]),
            "exceptionRowsWithSpecificEvidence": certificate.get("exceptionRowsWithSpecificEvidence", []),
        },
        "records": rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(database, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    README.write_text(
        "# Shobi Universal Canonical Database\n\n"
        "shobi-universal-v1.json is the versioned canonical snapshot. It is built "
        "only from the certified complete export, never from the lightweight browser "
        "catalog. It preserves every record field and audit state, including the "
        "unpromoted yellow records.\n",
        encoding="utf-8",
    )
    print(json.dumps(database["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
