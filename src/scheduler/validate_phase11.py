"""
src/scheduler/validate_phase11.py
==================================
Phase 11 Validation

Verifies that the GitHub Actions scheduler infrastructure is correctly
set up and that the pipeline runner works end-to-end.

Checks:
    1. pipeline_runner.py can be imported without errors
    2. logs/ directory exists (or can be created)
    3. .github/workflows/daily_refresh.yml exists and is valid YAML
    4. pipeline_runner.run_pipeline() executes successfully (dry run)
    5. logs/refresh_log.jsonl was created/updated with status="success"
    6. vector_store/faiss_index/ mtime was updated after the run

Usage:
    python src/scheduler/validate_phase11.py

Exit codes:
    0 — all checks PASSED
    1 — one or more checks FAILED

Spec reference: ImplementationPlan.md § 11.7
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Ensure project root is on sys.path so 'src.*' imports resolve
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    tag = PASS if ok else FAIL
    line = f"  [{tag}] {name}"
    if detail:
        line += f"\n         {detail}"
    print(line)
    results.append((name, ok, detail))
    return ok


def main() -> int:
    print("\n" + "=" * 60)
    print("  Phase 11 Validation — Daily Data Refresh Scheduler")
    print("=" * 60 + "\n")

    # ── Check 1: Import pipeline_runner ──────────────────────────────────
    try:
        from src.scheduler import pipeline_runner  # noqa: F401
        check("Import pipeline_runner", True)
    except Exception as exc:
        check("Import pipeline_runner", False, str(exc))

    # ── Check 2: logs/ directory ─────────────────────────────────────────
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    check("logs/ directory exists", log_dir.is_dir(), str(log_dir))

    # ── Check 3: GitHub Actions workflow file ────────────────────────────
    wf_path = PROJECT_ROOT / ".github" / "workflows" / "daily_refresh.yml"
    wf_exists = wf_path.is_file()
    check("daily_refresh.yml exists", wf_exists, str(wf_path))

    if wf_exists:
        try:
            import yaml  # type: ignore
            with wf_path.open(encoding="utf-8") as f:
                yaml.safe_load(f)
            check("daily_refresh.yml is valid YAML", True)
        except ImportError:
            # PyYAML not installed — do a basic text sanity check instead
            content = wf_path.read_text(encoding="utf-8")
            has_cron   = "cron:" in content
            has_python = "setup-python" in content
            has_push   = "git push" in content
            ok = has_cron and has_python and has_push
            check(
                "daily_refresh.yml contains required fields",
                ok,
                "cron: %s  setup-python: %s  git push: %s"
                % (has_cron, has_python, has_push),
            )
        except Exception as exc:
            check("daily_refresh.yml is valid YAML", False, str(exc))

    # ── Check 4 & 5: Run the pipeline and inspect the log ────────────────
    log_file     = PROJECT_ROOT / "logs" / "refresh_log.jsonl"
    faiss_index  = PROJECT_ROOT / "vector_store" / "faiss_index" / "index.faiss"

    faiss_mtime_before = faiss_index.stat().st_mtime if faiss_index.exists() else 0.0
    run_start = time.time()

    print("\n  Running pipeline_runner.run_pipeline() — this may take ~60s ...\n")

    try:
        from src.scheduler.pipeline_runner import run_pipeline
        success = run_pipeline()
    except Exception as exc:
        check("pipeline_runner.run_pipeline() executes", False, str(exc))
        success = False

    if success:
        check("pipeline_runner.run_pipeline() executes", True)
    else:
        check("pipeline_runner.run_pipeline() executes", False,
              "run_pipeline() returned False — see logs/refresh_log.jsonl")

    # Check the log file
    if log_file.exists():
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        last_record = json.loads(lines[-1]) if lines else {}
        last_status = last_record.get("status", "unknown")
        last_run_at = last_record.get("run_at", "")
        check(
            "logs/refresh_log.jsonl updated with status=success",
            last_status == "success",
            f"status={last_status!r}  run_at={last_run_at}",
        )
    else:
        check("logs/refresh_log.jsonl exists", False,
              "File was not created by run_pipeline()")

    # ── Check 6: FAISS index mtime updated ───────────────────────────────
    if faiss_index.exists():
        faiss_mtime_after = faiss_index.stat().st_mtime
        index_updated = faiss_mtime_after > faiss_mtime_before
        updated_at = datetime.fromtimestamp(faiss_mtime_after, tz=timezone.utc).isoformat()
        check(
            "vector_store/faiss_index/ mtime updated after run",
            index_updated,
            f"mtime after run: {updated_at}",
        )
    else:
        check("vector_store/faiss_index/index.faiss exists", False,
              "FAISS index not found — did embed_all() succeed?")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total  = len(results)
    print(f"  Result: {passed}/{total} checks passed")
    if passed == total:
        print(f"  {PASS} Phase 11 Validation PASSED")
    else:
        print(f"  {FAIL} Phase 11 Validation FAILED")
    print("=" * 60 + "\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
