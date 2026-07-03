"""
src/scheduler/pipeline_runner.py
=================================
Phase 11 — Daily Data Refresh Pipeline Runner

Orchestrates the full ingestion pipeline (Phases 2→3→4):
    fetch_all()   → Phase 2: Download raw HTML from Groww URLs
    parse_all()   → Phase 3.1: Parse + clean HTML to text
    chunk_all()   → Phase 3.2: Split text into overlapping chunks
    embed_all()   → Phase 4: Embed chunks and build FAISS index

Called by the GitHub Actions workflow (.github/workflows/daily_refresh.yml)
and can also be triggered manually for testing.

Usage:
    python -m src.scheduler.pipeline_runner

Exit codes:
    0 — pipeline completed successfully
    1 — pipeline failed (see logs/refresh_log.jsonl for details)

Spec reference: ImplementationPlan.md § 11.2
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR      = PROJECT_ROOT / "logs"
LOG_FILE     = LOG_DIR / "refresh_log.jsonl"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline() -> bool:
    """
    Execute the full ingestion pipeline end-to-end and log the result.

    Returns:
        True  if all stages completed without error.
        False if any stage raised an exception.
    """
    # Ensure the log directory exists (may not exist on a fresh checkout)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    start_time = datetime.now(timezone.utc)
    record: dict = {
        "run_at":  start_time.isoformat(),
        "status":  "running",
        "chunks":  0,
        "error":   None,
    }

    logger.info("=" * 60)
    logger.info("Phase 11 — Daily Data Refresh starting")
    logger.info("Run started at: %s", start_time.isoformat())
    logger.info("=" * 60)

    try:
        # ── Stage 1: Fetch ────────────────────────────────────────────────
        logger.info("[Stage 1/4] Fetching raw HTML from Groww URLs ...")
        from src.ingestion.fetcher import fetch_all  # noqa: PLC0415
        fetch_all()
        logger.info("[Stage 1/4] Fetch complete.")

        # ── Stage 2: Parse ────────────────────────────────────────────────
        logger.info("[Stage 2/4] Parsing + cleaning HTML to text ...")
        from src.ingestion.parser import parse_all   # noqa: PLC0415
        parse_all()
        logger.info("[Stage 2/4] Parse complete.")

        # ── Stage 3: Chunk ────────────────────────────────────────────────
        logger.info("[Stage 3/4] Chunking text into overlapping segments ...")
        from src.ingestion.chunker import chunk_all  # noqa: PLC0415
        chunks = chunk_all()
        logger.info("[Stage 3/4] Chunking complete. Total chunks: %d", len(chunks))

        # ── Stage 4: Embed ────────────────────────────────────────────────
        logger.info("[Stage 4/4] Embedding chunks and rebuilding FAISS index ...")
        from src.ingestion.embedder import load_chunks, build_index  # noqa: PLC0415
        embed_chunks = load_chunks()
        build_index(embed_chunks)
        logger.info("[Stage 4/4] Embedding complete.")


        # ── Success ───────────────────────────────────────────────────────
        end_time = datetime.now(timezone.utc)
        duration_s = (end_time - start_time).total_seconds()
        record["status"]      = "success"
        record["chunks"]      = len(chunks)
        record["finished_at"] = end_time.isoformat()
        record["duration_s"]  = round(duration_s, 1)

        logger.info("=" * 60)
        logger.info("Pipeline SUCCEEDED in %.1f seconds. Chunks: %d", duration_s, len(chunks))
        logger.info("=" * 60)

    except Exception as exc:
        end_time = datetime.now(timezone.utc)
        duration_s = (end_time - start_time).total_seconds()
        record["status"]      = "error"
        record["error"]       = str(exc)
        record["finished_at"] = end_time.isoformat()
        record["duration_s"]  = round(duration_s, 1)

        logger.error("=" * 60)
        logger.exception("Pipeline FAILED after %.1f seconds: %s", duration_s, exc)
        logger.error("=" * 60)

    finally:
        # Always write the run record to the append-only log file
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        logger.info("Run record written to %s", LOG_FILE)

    return record["status"] == "success"


# ---------------------------------------------------------------------------
# Entrypoint (python -m src.scheduler.pipeline_runner)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
