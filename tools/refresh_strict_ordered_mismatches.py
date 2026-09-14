#!/usr/bin/env python3
"""Recheck only rows corrected after the completed full card audit."""
from __future__ import annotations

import json
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from audit_social_card_order_from_images import DB, LEXICON, OUT, find_card, inspect


def main():
    report = json.loads(OUT.read_text(encoding="utf-8"))
    rows = json.loads(DB.read_text(encoding="utf-8-sig"))
    lexicon = [line.strip() for line in LEXICON.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_code = {str(row.get("code") or "").strip().upper(): row for row in rows}
    targets = [item for item in report["rows"] if item.get("result") == "ORDERED_MISMATCH"]
    tasks = []
    for item in targets:
        row = by_code.get(str(item.get("code") or "").strip().upper())
        if not row:
            raise SystemExit(f"Missing corrected row: {item.get('code')}")
        card = find_card(row)
        tasks.append((row, str(card) if card else "", lexicon))
    with ProcessPoolExecutor(max_workers=max(1, min(6, os.cpu_count() or 2))) as pool:
        refreshed = list(pool.map(inspect, tasks))
    refreshed_by_code = {item["code"]: item for item in refreshed}
    report["rows"] = [refreshed_by_code.get(item.get("code"), item) for item in report["rows"]]
    report["results"] = dict(sorted(Counter(item["result"] for item in report["rows"]).items()))
    report["refresh"] = {"recheckedCorrectedRows": len(refreshed), "rule": "Only the 110 rows changed after the completed full audit were reread from their exact archived Social Card image."}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rechecked": len(refreshed), "results": report["results"]}, indent=2))


if __name__ == "__main__":
    main()
