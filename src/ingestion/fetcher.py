"""
src/ingestion/fetcher.py
========================
Phase 2 — Data Ingestion Pipeline

Fetches raw HTML from the 7 Groww scheme URLs defined in config/urls.yaml
and persists them to data/raw/<scheme_slug>.html.

Metadata for all fetched schemes is written to data/raw/metadata.json.

Spec reference: ImplementationPlan.md § 2.1 – 2.3
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

# ---------------------------------------------------------------------------
# Paths (resolved relative to project root, not this file's location)
# ---------------------------------------------------------------------------
PROJECT_ROOT  = Path(__file__).resolve().parents[2]
CONFIG_PATH   = PROJECT_ROOT / "config" / "urls.yaml"
RAW_DIR       = PROJECT_ROOT / "data" / "raw"
METADATA_PATH = RAW_DIR / "metadata.json"

# ---------------------------------------------------------------------------
# HTTP settings (§ 2.2)
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RAGBot/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
TIMEOUT_SECONDS      = 15   # § 2.2: HTTP timeout
MAX_RETRIES          = 3    # § 2.2: Retry attempts
BACKOFF_BASE_SECS    = 2    # § 2.2: 2s exponential backoff  →  2s, 4s, 8s
MAX_FAILURES_ALLOWED = 2    # § 2.1: raise alert if more than 2 URLs fail

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
# Helpers
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """
    Convert a scheme name to a filesystem-safe slug.

    Strips the common " - Direct Growth" plan-type suffix before slugifying,
    so filenames match the § 2.2 spec (e.g. ``groww_gold_etf_fof.html``).

    Example:
        "Groww Gold ETF FoF - Direct Growth"  ->  "groww_gold_etf_fof"
    """
    # Strip plan-type suffixes that all 7 schemes share
    slug = re.sub(r"\s*-\s*Direct\s+Growth\s*$", "", name, flags=re.IGNORECASE)
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)   # replace non-alphanumeric with _
    slug = slug.strip("_")
    return slug


def _fetch_with_retry(url: str) -> requests.Response:
    """
    Send HTTP GET to *url* with up to MAX_RETRIES attempts and exponential
    backoff.  Returns the first successful Response.

    Raises:
        requests.RequestException -- if all retry attempts fail.
    """
    last_exception: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("  Attempt %d/%d  GET %s", attempt, MAX_RETRIES, url)
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()     # raise on 4xx / 5xx
            logger.info(
                "  OK  HTTP %d -- %d bytes received",
                response.status_code,
                len(response.content),
            )
            return response
        except requests.RequestException as exc:
            last_exception = exc
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE_SECS ** attempt   # 2, 4, 8 …
                logger.warning(
                    "  FAIL  Attempt %d failed: %s -- retrying in %ds",
                    attempt, exc, wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "  FAIL  All %d attempts failed for %s: %s",
                    MAX_RETRIES, url, exc,
                )

    raise last_exception  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Core fetch logic
# ---------------------------------------------------------------------------

def load_schemes() -> list[dict]:
    """Load the list of scheme dicts from config/urls.yaml."""
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    schemes = data["corpus"]["schemes"]
    logger.info("Loaded %d schemes from %s", len(schemes), CONFIG_PATH)
    return schemes


def fetch_all() -> list[dict]:
    """
    Iterate over all schemes, fetch HTML, and persist to data/raw/.

    Returns:
        List of metadata dicts for successfully fetched schemes.

    Raises:
        RuntimeError -- if the number of failures exceeds MAX_FAILURES_ALLOWED.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    schemes  = load_schemes()
    metadata: list[dict] = []
    failures = 0

    for scheme in schemes:
        name     = scheme["name"]
        url      = scheme["url"]
        category = scheme["category"]
        slug     = _slugify(name)
        out_path = RAW_DIR / f"{slug}.html"

        logger.info("-" * 60)
        logger.info("Fetching: %s", name)

        try:
            response = _fetch_with_retry(url)
        except requests.RequestException as exc:
            failures += 1
            logger.error("SKIP -- could not fetch '%s': %s", name, exc)

            # § 2.1: raise alert if more than MAX_FAILURES_ALLOWED fail
            if failures > MAX_FAILURES_ALLOWED:
                raise RuntimeError(
                    f"Ingestion aborted: {failures} URLs have failed "
                    f"(threshold is {MAX_FAILURES_ALLOWED}). "
                    "Check network connectivity or URL validity."
                ) from exc
            continue

        # Persist raw HTML ─────────────────────────────────────────────────
        html_bytes = response.content
        out_path.write_bytes(html_bytes)
        logger.info(
            "  Saved  %s  (%d bytes)",
            out_path.relative_to(PROJECT_ROOT),
            len(html_bytes),
        )

        # Build metadata entry ─────────────────────────────────────────────
        entry = {
            "scheme_name": name,
            "url":         url,
            "category":    category,
            "slug":        slug,
            "file":        str(out_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "fetched_at":  datetime.now(timezone.utc).isoformat(),
            "size_bytes":  len(html_bytes),
        }
        metadata.append(entry)

    # Write / update metadata.json ─────────────────────────────────────────
    METADATA_PATH.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("-" * 60)
    logger.info(
        "Done. %d/%d schemes fetched successfully. Metadata -> %s",
        len(metadata),
        len(schemes),
        METADATA_PATH.relative_to(PROJECT_ROOT),
    )

    return metadata


# ---------------------------------------------------------------------------
# Validation helper (§ 2.3)
# ---------------------------------------------------------------------------

def validate(metadata: list[dict]) -> bool:
    """
    Validate outputs against the exit criteria (§ 2.3):
      - All files exist in data/raw/
      - Each HTML file is non-empty (> 5 KB)
      - metadata.json contains fetched_at for all schemes

    Returns:
        True if all checks pass, False otherwise.
    """
    MIN_FILE_SIZE = 5 * 1024   # 5 KB

    logger.info("-" * 60)
    logger.info("Running validation (§ 2.3) ...")
    passed = True

    for entry in metadata:
        path = PROJECT_ROOT / entry["file"]

        if not path.exists():
            logger.error("  FAIL -- file missing: %s", path)
            passed = False
            continue

        size = path.stat().st_size
        if size < MIN_FILE_SIZE:
            logger.warning(
                "  WARN -- file too small (%d bytes < 5 KB): %s", size, path.name
            )
        else:
            logger.info("  OK   -- %s  (%d bytes)", path.name, size)

        if not entry.get("fetched_at"):
            logger.error(
                "  FAIL -- missing fetched_at in metadata for: %s",
                entry["scheme_name"],
            )
            passed = False

    if passed:
        logger.info("Validation PASSED")
    else:
        logger.error("Validation FAILED -- review errors above.")

    return passed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("Phase 2 -- Data Ingestion Pipeline")
    logger.info("=" * 60)

    metadata = fetch_all()

    if metadata:
        validate(metadata)
    else:
        logger.error("No schemes were fetched successfully.")


if __name__ == "__main__":
    main()
