"""
Phase 2.3 — Validation Script
Checks all exit criteria from ImplementationPlan.md § 2.3.
"""

import json
from src.ingestion.fetcher import validate, METADATA_PATH, RAW_DIR, PROJECT_ROOT


def main():
    print("=" * 60)
    print("Phase 2.3 — Validation")
    print("=" * 60)

    # Load metadata
    meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    # Check 1: All 7 files exist in data/raw/
    html_files = list(RAW_DIR.glob("*.html"))
    count = len(html_files)
    status1 = "PASS" if count == 7 else "FAIL"
    print(f"\n[{status1}] 1) HTML files in data/raw/: {count} (expected: 7)")

    # Check 2: Each HTML file is non-empty (> 5 KB)
    MIN_SIZE = 5 * 1024
    small_files = []
    print(f"\n[INFO] 2) File sizes (must be > 5 KB = {MIN_SIZE} bytes):")
    for entry in meta:
        path = PROJECT_ROOT / entry["file"]
        size = path.stat().st_size if path.exists() else 0
        ok = size > MIN_SIZE
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}]  {entry['slug']:50s}  {size:>10,} bytes")
        if not ok:
            small_files.append(entry["slug"])
    status2 = "PASS" if len(small_files) == 0 else "FAIL"
    print(f"  => [{status2}] Files below 5 KB: {len(small_files)}")

    # Check 3: metadata.json contains fetched_at for all 7 schemes
    missing_ts = [e["scheme_name"] for e in meta if not e.get("fetched_at")]
    status3 = "PASS" if len(missing_ts) == 0 and len(meta) == 7 else "FAIL"
    print(f"\n[{status3}] 3) metadata.json entries with fetched_at: {len(meta) - len(missing_ts)}/{len(meta)}")
    for entry in meta:
        print(f"  - {entry['scheme_name']}")
        print(f"    fetched_at: {entry.get('fetched_at', 'MISSING')}")

    # Overall
    print("\n" + "=" * 60)
    overall = all(s == "PASS" for s in [status1, status2, status3])
    print(f"Overall Phase 2.3 Validation: {'PASS' if overall else 'FAIL'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
