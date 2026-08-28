#!/usr/bin/env python3
"""Resumable bulk worker for Shobi perfume identity mapping.

The worker is deliberately evidence-safe: it never manufactures an identity.
A resolver command receives one Master row as JSON on stdin and must return one
reviewed mapping row as JSON on stdout. This script supplies the production
plumbing around that resolver: timeout, retries, per-item error isolation,
immediate durable saves, checkpoints and resume.

Examples:
  python tools/shobi_identity_resolver.py stats
  python tools/shobi_identity_resolver.py queue --limit 100
  python tools/shobi_identity_resolver.py run --resolver-cmd "python tools/my_resolver.py" --limit 100
  python tools/shobi_identity_resolver.py retry-errors --resolver-cmd "python tools/my_resolver.py"
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

MASTER = Path("data/shobi-master-v1.csv")
MAPPING = Path("data/shobi-fragrantica-mapping.csv")
STATE = Path("data/identity-resolver-state.json")
QUEUE = Path("data/identity-review-queue.csv")
ERRORS = Path("data/identity-resolver-errors.csv")

FIELDS = [
    "prestashop_product_id", "shobi_code", "inspired_by", "original_brand",
    "original_perfume", "identity_status", "fragrantica_status",
    "fragrantica_id", "fragrantica_url", "evidence_note",
]
QUEUE_FIELDS = [
    "prestashop_product_id", "shobi_code", "inspired_by", "reference_prefix",
    "category", "official_description", "shobi_url",
]
ERROR_FIELDS = [
    "prestashop_product_id", "shobi_code", "attempts", "last_error",
    "last_error_utc",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def atomic_write_csv(path: Path, fields, rows):
    """Atomic replacement so interruption cannot leave a half-written CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def key(row):
    return (row.get("prestashop_product_id") or "").strip()


def master_order():
    return [key(r) for r in read_csv(MASTER) if key(r)]


def normalize_mapping_row(r):
    return {f: (r.get(f, "") if r.get(f, "") is not None else "") for f in FIELDS}


def mapping_dict():
    return {key(r): normalize_mapping_row(r) for r in read_csv(MAPPING) if key(r)}


def ordered_mapping(by_id):
    ids = master_order()
    rows = [by_id[i] for i in ids if i in by_id]
    seen = set(ids)
    rows.extend(r for i, r in by_id.items() if i not in seen)
    return rows


def save_mapping(by_id):
    atomic_write_csv(MAPPING, FIELDS, ordered_mapping(by_id))


def unresolved_master(include_error_ids=None):
    master = read_csv(MASTER)
    mapped = set(mapping_dict())
    include_error_ids = set(include_error_ids or [])
    return [
        r for r in master
        if key(r) and (key(r) not in mapped or key(r) in include_error_ids)
    ]


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
    atomic_write_csv(QUEUE, QUEUE_FIELDS, queue)
    state = state_snapshot(queue_total=len(queue))
    atomic_write_json(STATE, state)
    print(json.dumps(state, indent=2, ensure_ascii=False))


def validate_result(r, expected_id=None):
    if expected_id and key(r) != expected_id:
        raise ValueError(f"resolver returned product {key(r)!r}, expected {expected_id!r}")
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
    if not (r.get("evidence_note") or "").strip():
        raise ValueError(f"row {key(r)} requires evidence_note")


def import_results(path: Path):
    by_id = mapping_dict()
    incoming = read_csv(path)
    for r in incoming:
        if not key(r):
            raise ValueError("result row missing prestashop_product_id")
        validate_result(r)
        by_id[key(r)] = normalize_mapping_row(r)
    save_mapping(by_id)
    print(f"Imported {len(incoming)} reviewed rows; mapping now has {len(by_id)} rows")
    build_queue(None)


def load_errors():
    return {key(r): r for r in read_csv(ERRORS) if key(r)}


def save_errors(errors):
    rows = list(errors.values())
    order = {pid: i for i, pid in enumerate(master_order())}
    rows.sort(key=lambda r: order.get(key(r), 10**9))
    atomic_write_csv(ERRORS, ERROR_FIELDS, rows)


def record_error(errors, row, attempts, message):
    pid = key(row)
    errors[pid] = {
        "prestashop_product_id": pid,
        "shobi_code": row.get("shobi_code", ""),
        "attempts": str(attempts),
        "last_error": message[:2000],
        "last_error_utc": now_utc(),
    }
    save_errors(errors)


def clear_error(errors, pid):
    if pid in errors:
        del errors[pid]
        save_errors(errors)


def state_snapshot(**extra):
    master = read_csv(MASTER)
    mapping = read_csv(MAPPING)
    mapped = {key(r) for r in mapping if key(r)}
    remaining_rows = [r for r in master if key(r) and key(r) not in mapped]
    payload = {
        "updated_utc": now_utc(),
        "master_total": len(master),
        "mapping_total": len(mapping),
        "remaining_total": len(remaining_rows),
        "error_total": len(read_csv(ERRORS)),
        "next_product_id": key(remaining_rows[0]) if remaining_rows else None,
    }
    payload.update(extra)
    return payload


def save_state(**extra):
    atomic_write_json(STATE, state_snapshot(**extra))


def resolver_argv(command: str):
    argv = shlex.split(command, posix=(os.name != "nt"))
    if not argv:
        raise ValueError("empty --resolver-cmd")
    return argv


def call_resolver(command: str, row, timeout: float):
    """Send one Master row as JSON stdin; expect one mapping JSON object stdout."""
    payload = json.dumps(row, ensure_ascii=False)
    cp = subprocess.run(
        resolver_argv(command),
        input=payload,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if cp.returncode != 0:
        stderr = (cp.stderr or "").strip()
        raise RuntimeError(f"resolver exit {cp.returncode}: {stderr or 'no stderr'}")
    stdout = (cp.stdout or "").strip()
    if not stdout:
        raise RuntimeError("resolver returned empty stdout")
    # Permit informational lines before the final JSON object.
    candidate = stdout.splitlines()[-1]
    try:
        result = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"resolver output is not JSON: {candidate[:500]}") from e
    if not isinstance(result, dict):
        raise RuntimeError("resolver JSON must be an object")
    return result


def run_worker(command: str, limit: int | None, timeout: float, retries: int,
               retry_delay: float, retry_errors_only: bool = False):
    errors = load_errors()
    if retry_errors_only:
        error_ids = set(errors)
        work = [r for r in read_csv(MASTER) if key(r) in error_ids]
    else:
        work = unresolved_master()
    if limit is not None:
        work = work[:limit]

    total = len(work)
    print(f"Worker start: {total} item(s), timeout={timeout}s, retries={retries}")
    save_state(run_status="RUNNING", run_total=total, run_done=0)

    done = 0
    failed = 0
    for row in work:
        pid = key(row)
        # Resume protection: check again immediately before doing network/research work.
        if not retry_errors_only and pid in mapping_dict():
            continue

        result = None
        last_error = None
        attempts = 0
        for attempt in range(1, retries + 2):
            attempts = attempt
            try:
                result = call_resolver(command, row, timeout)
                # Fill source identity fields from Master when resolver omits them.
                result.setdefault("prestashop_product_id", pid)
                result.setdefault("shobi_code", row.get("shobi_code", ""))
                result.setdefault("inspired_by", row.get("inspired_by", ""))
                validate_result(result, expected_id=pid)
                break
            except subprocess.TimeoutExpired:
                last_error = f"timeout after {timeout}s"
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"

            if attempt <= retries:
                wait = retry_delay * (2 ** (attempt - 1))
                print(f"[{pid}] attempt {attempt} failed: {last_error}; retry in {wait:.1f}s")
                time.sleep(wait)

        if result is None:
            failed += 1
            record_error(errors, row, attempts, last_error or "unknown error")
            print(f"[{pid}] ERROR after {attempts} attempt(s); saved and continuing")
        else:
            # Immediate durable checkpoint after EVERY successful perfume.
            by_id = mapping_dict()
            by_id[pid] = normalize_mapping_row(result)
            save_mapping(by_id)
            clear_error(errors, pid)
            done += 1
            print(f"[{pid}] SAVED {result.get('identity_status')} / {result.get('fragrantica_status')}")

        save_state(
            run_status="RUNNING",
            run_total=total,
            run_done=done,
            run_failed=failed,
            current_product_id=pid,
        )

    save_state(
        run_status="COMPLETE",
        run_total=total,
        run_done=done,
        run_failed=failed,
        current_product_id=None,
    )
    print(f"Worker complete: saved={done}, errors={failed}. Safe to rerun/resume.")


def stats():
    master = read_csv(MASTER)
    mapping = read_csv(MAPPING)
    counts = {}
    for r in mapping:
        pair = ((r.get("identity_status") or "").strip(), (r.get("fragrantica_status") or "").strip())
        counts[pair] = counts.get(pair, 0) + 1
    print(json.dumps({
        "master": len(master),
        "mapped": len(mapping),
        "remaining": len(master) - len(mapping),
        "errors": len(read_csv(ERRORS)),
        "status_pairs": {" / ".join(k): v for k, v in counts.items()},
    }, indent=2, ensure_ascii=False))


def add_worker_args(p):
    p.add_argument("--resolver-cmd", required=True,
                   help="command that reads one Master JSON object from stdin and prints one verified mapping JSON object")
    p.add_argument("--limit", type=int, help="process at most N items this run")
    p.add_argument("--timeout", type=float, default=90.0, help="seconds allowed per resolver attempt (default: 90)")
    p.add_argument("--retries", type=int, default=3, help="retries after first failure (default: 3)")
    p.add_argument("--retry-delay", type=float, default=2.0, help="initial retry delay; exponential backoff (default: 2s)")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("queue")
    q.add_argument("--limit", type=int)

    i = sub.add_parser("import")
    i.add_argument("results", type=Path)

    sub.add_parser("stats")

    r = sub.add_parser("run", help="process unresolved Master rows with checkpoint/resume")
    add_worker_args(r)

    rr = sub.add_parser("retry-errors", help="retry only rows currently in the error ledger")
    add_worker_args(rr)

    a = p.parse_args()
    if a.cmd == "queue":
        build_queue(a.limit)
    elif a.cmd == "import":
        import_results(a.results)
    elif a.cmd == "stats":
        stats()
    elif a.cmd == "run":
        run_worker(a.resolver_cmd, a.limit, a.timeout, a.retries, a.retry_delay, False)
    elif a.cmd == "retry-errors":
        run_worker(a.resolver_cmd, a.limit, a.timeout, a.retries, a.retry_delay, True)


if __name__ == "__main__":
    main()
