#!/usr/bin/env python3
import csv
import os
import tempfile
from pathlib import Path

PATH = Path("data/shobi-fragrantica-mapping.csv")
PREFIXES = (
    "No Fragrantica candidate found via public web search",
    "Public search candidate not unique/strong enough",
    "Candidate found but verification insufficient",
)

with PATH.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames or []
    rows = list(reader)

keep = []
removed = []
for row in rows:
    note = (row.get("evidence_note") or "").strip()
    if row.get("identity_status") == "AMBIGUOUS" and note.startswith(PREFIXES):
        removed.append(row)
    else:
        keep.append(row)

fd, tmp = tempfile.mkstemp(prefix=PATH.name + ".", suffix=".tmp", dir=PATH.parent)
with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(keep)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, PATH)

print(f"Removed {len(removed)} failed auto-ambiguity rows; retained {len(keep)} mappings")
