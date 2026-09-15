#!/usr/bin/env python3
"""Summarize every yellow validation row without changing catalog data."""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "database/catalog/catalog_site.json"
OUT_JSON = ROOT / "database/audits/validation-yellow-report.json"
OUT_MD = ROOT / "database/audits/validation-yellow-report.md"

rows = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
yellow = [r for r in rows if str(r.get("validationStatus") or "").lower() == "yellow"]

issue_counts = Counter(); check_counts = Counter(); signature_counts = Counter()
issue_codes = defaultdict(list); check_codes = defaultdict(list); signature_codes = defaultdict(list)
report_rows = []
for r in yellow:
    code = str(r.get("code") or "").strip()
    issues = list(r.get("validationIssues") or [])
    checks = r.get("validationChecks") or {}
    failed = [k for k, v in checks.items() if not v]
    sig = ",".join(failed)
    signature_counts[sig] += 1; signature_codes[sig].append(code)
    for issue in issues: issue_counts[issue] += 1; issue_codes[issue].append(code)
    for check in failed: check_counts[check] += 1; check_codes[check].append(code)
    report_rows.append({
        "code": code, "brand": r.get("brand"), "inspiredBy": r.get("inspiredBy"),
        "fragranticaUrl": r.get("fragranticaUrl"), "issues": issues, "failedChecks": failed,
        "notesCount": r.get("validationNotesCount", 0), "matchedNotesCount": r.get("validationMatchedNotesCount", 0),
        "iconsCount": r.get("validationIconsCount", 0),
    })

single = [r for r in report_rows if len(r['failedChecks']) == 1]
payload = {
    "catalogRows": len(rows), "yellowRows": len(yellow), "singleFailureRows": single,
    "byFailureSignature": [{"signature": k, "count": v, "codes": signature_codes[k]} for k,v in signature_counts.most_common()],
    "byIssue": [{"issue": k, "count": v, "codes": issue_codes[k]} for k, v in issue_counts.most_common()],
    "byFailedCheck": [{"check": k, "count": v, "codes": check_codes[k]} for k, v in check_counts.most_common()],
    "rows": report_rows,
}
OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

lines = ["# Validation yellow report","",f"- Catalog rows: **{len(rows)}**",f"- Yellow rows: **{len(yellow)}**",f"- One check from green: **{len(single)}**","","## Failed checks",""]
for key, count in check_counts.most_common(): lines.append(f"- `{key}`: **{count}**")
lines += ["", "## Failure signatures", ""]
for sig,count in signature_counts.most_common(): lines.append(f"- `{sig or '<none>'}`: **{count}** — {', '.join(signature_codes[sig][:20])}")
lines += ["", "## One check from green", "", "| Code | Brand | Inspired by | Remaining check |", "|---|---|---|---|"]
for r in single:
    safe=lambda x:str(x or '').replace('|','\\|')
    lines.append(f"| {safe(r['code'])} | {safe(r['brand'])} | {safe(r['inspiredBy'])} | {safe(r['failedChecks'][0])} |")
lines += ["", "## Issues", ""]
for key, count in issue_counts.most_common(): lines.append(f"- {key}: **{count}**")
lines += ["", "## Yellow rows", "", "| Code | Brand | Inspired by | Failed checks |", "|---|---|---|---|"]
for r in report_rows:
    safe=lambda x:str(x or '').replace('|','\\|')
    lines.append(f"| {safe(r['code'])} | {safe(r['brand'])} | {safe(r['inspiredBy'])} | {safe(', '.join(r['failedChecks']))} |")
OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(f"catalog={len(rows)} yellow={len(yellow)} single_failure={len(single)}")
print("failed_checks",dict(check_counts)); print("signatures",dict(signature_counts))
