#!/usr/bin/env python3
"""Classify current yellow catalog rows without changing validation state."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "database/catalog/catalog_site.json"
DB = ROOT / "database/catalog/database_complete.json"
ORDERED = ROOT / "database/fragrantica/social-cards/records/social-card-ordered-image-audit.json"
V2 = ROOT / "database/audits/v2-exact-validation.json"
OUT = ROOT / "database/audits/current-yellow-breakdown.json"


def code(row):
    return str(row.get("code") or "").strip().upper()


def main():
    site = json.loads(SITE.read_text(encoding="utf-8-sig"))
    db = json.loads(DB.read_text(encoding="utf-8-sig"))
    ordered = {code(r): r for r in json.loads(ORDERED.read_text(encoding="utf-8")).get("rows", [])}
    v2_payload = json.loads(V2.read_text(encoding="utf-8")) if V2.is_file() else {}
    v2 = {code(r): r for r in v2_payload.get("rows", [])}
    db_by_code = {code(r): r for r in db}

    yellows = [r for r in site if r.get("validationStatus") == "yellow"]
    issue_counts = Counter()
    combo_counts = Counter()
    audit_result_counts = Counter()
    single_issue_counts = Counter()
    rows = []

    for s in yellows:
        c = code(s)
        issues = tuple(sorted(str(x) for x in (s.get("validationIssues") or [])))
        combo_counts[issues] += 1
        issue_counts.update(issues)
        if len(issues) == 1:
            single_issue_counts[issues[0]] += 1
        ev = ordered.get(c) or {}
        audit_result = str(ev.get("result") or "NO_AUDIT_ROW")
        audit_result_counts[audit_result] += 1
        proof = v2.get(c) or {}
        rows.append({
            "code": c,
            "fid": str((db_by_code.get(c) or {}).get("fragranticaId") or ""),
            "issues": list(issues),
            "orderedAudit": audit_result,
            "v2Status": proof.get("status"),
        })

    report = {
        "totalCatalog": len(site),
        "yellow": len(yellows),
        "issueCounts": dict(issue_counts.most_common()),
        "singleIssueCounts": dict(single_issue_counts.most_common()),
        "orderedAuditResults": dict(audit_result_counts.most_common()),
        "issueCombinations": [
            {"count": n, "issues": list(combo)}
            for combo, n in combo_counts.most_common()
        ],
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "yellow": len(yellows),
        "topIssues": issue_counts.most_common(10),
        "orderedAuditResults": audit_result_counts.most_common(),
        "singleIssueCounts": single_issue_counts.most_common(10),
        "output": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
