#!/usr/bin/env python3
"""Checkpointed bulk resolver scaffold for Shobi perfume identity.

This tool deliberately does NOT invent perfume identities. It prepares unresolved
Shobi Master rows as durable work items, preserves already-reviewed mappings,
and supports importing externally verified results back into the official mapping.

Identity verification itself must come from evidence; this script is the queue,
checkpoint and validation layer for scaling that work safely.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

MASTER = Path("data/shobi-master-v1.csv")
MAPPING = Path("data/shobi-fragrantica-mapping.csv")
STATE = Path("data/identity-resolver-state.json")
QUEUE = Path("data/identity-review-queue.csv")

FIELDS = [
    "prestashop_product_id", "shobi_code", "inspired_by", "original_brand",
    "original_perfume", "identity_status", "fragrantica_status",
    "fragrantica_id", "fragrantica_url", "evidence_note",
]
QUEUE_FIELDS = [
    "prestashop_product_id", "shobi_code", "inspired_by", "reference_prefix",
    "category", "official_description", "shobi_url",
]


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def key(row):
    return (row.get("prestashop_product_id") or "").strip()


def build_queue(limit: int | None):
    master = read_csv(MASTER)
    mapping = read_csv(MAPPING)
    mapped = {key(r) for r in mapping if key(r)}
    unresolved = [r for r in master if key(r) and key(r) not in mapped]
    if limit is not None:
        unresolved = unresolved[:limit]
    queue = [{
        "prestashop_product_id": r.get("prestashop_product_id", ""),
        "shobi_code": r.get("shobi_code", ""),
        "inspired_by": r.get("inspired_by", ""),
        "reference_prefix": r.get("reference_prefix", ""),
        "category": r.get("category", ""),
        "official_description": r.get("official_description", ""),
        "shobi_url": r.get("url", ""),
    } for r in unresolved]
    write_csv(QUEUE, QUEUE_FIELDS, queue)
    state = {
        "master_total": len(master),
        "mapping_total": len(mapping),
        "remaining_total": len([r for r in master if key(r) and key(r) not in mapped]),
        "queue_total": len(queue),
        "next_product_id": key(queue[0]) if queue else None,
    }
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2))


def validate_result(r):
    identity = (r.get("identity_status") or "").strip().upper()
    frag = (r.get("fragrantica_status") or "").strip().upper()
    if identity not in {"CONFIRMED", "AMBIGUOUS"}:
        raise ValueError(f"invalid identity_status for {key(r)}: {identity}")
    if frag not in {"FOUND", "NOT_FOUND"}:
        raise ValueError(f"invalid fragrantica_status for {key(r)}: {frag}")
    if identity == "AMBIGUOUS" and (r.get("fragrantica_id") or "").strip():
        raise ValueError(f"AMBIGUOUS row {key(r)} cannot have official Fragrantica ID")
    if frag == "FOUND" and not (r.get("fragrantica_id") or "").strip():
        raise ValueError(f"FOUND row {key(r)} requires fragrantica_id")
    if frag == "FOUND" and not (r.get("fragrantica_url") or "").strip():
        raise ValueError(f"FOUND row {key(r)} requires fragrantica_url")
    if identity == "CONFIRMED" and not (r.get("original_perfume") or "").strip():
        raise ValueError(f"CONFIRMED row {key(r)} requires original_perfume")


def import_results(path: Path):
    existing = read_csv(MAPPING)
    by_id = {key(r): r for r in existing if key(r)}
    incoming = read_csv(path)
    for r in incoming:
        if not key(r):
            raise ValueError("result row missing prestashop_product_id")
        validate_result(r)
        by_id[key(r)] = {f: r.get(f, "") for f in FIELDS}
    # Preserve Master order, then any exceptional rows not present in Master.
    master_ids = [key(r) for r in read_csv(MASTER)]
    ordered = [by_id[i] for i in master_ids if i in by_id]
    seen = set(master_ids)
    ordered.extend(r for i, r in by_id.items() if i not in seen)
    write_csv(MAPPING, FIELDS, ordered)
    print(f"Imported {len(incoming)} reviewed rows; mapping now has {len(ordered)} rows")
    build_queue(None)


def stats():
    master = read_csv(MASTER)
    mapping = read_csv(MAPPING)
    counts = {}
    for r in mapping:
        pair = ((r.get("identity_status") or "").strip(), (r.get("fragrantica_status") or "").strip())
        counts[pair] = counts.get(pair, 0) + 1
    print(json.dumps({"master": len(master), "mapped": len(mapping), "remaining": len(master)-len(mapping), "status_pairs": {" / ".join(k): v for k, v in counts.items()}}, indent=2))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("queue")
    q.add_argument("--limit", type=int)
    i = sub.add_parser("import")
    i.add_argument("results", type=Path)
    sub.add_parser("stats")
    a = p.parse_args()
    if a.cmd == "queue": build_queue(a.limit)
    elif a.cmd == "import": import_results(a.results)
    else: stats()

if __name__ == "__main__":
    main()
