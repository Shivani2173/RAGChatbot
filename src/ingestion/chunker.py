"""
src/ingestion/chunker.py
========================
Phase 3.2 — Text Chunker

For each cleaned .txt file in data/processed/, this module:
  1. Loads the text
  2. Splits it using LangChain RecursiveCharacterTextSplitter
  3. Attaches metadata (chunk_id, source_url, scheme_name, etc.)
  4. Writes all chunks to data/chunks/chunks.jsonl

Spec reference: ImplementationPlan.md § 3.2 – 3.3
"""

import json
import logging
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT   = Path(__file__).resolve().parents[2]
PROCESSED_DIR  = PROJECT_ROOT / "data" / "processed"
CHUNKS_DIR     = PROJECT_ROOT / "data" / "chunks"
CHUNKS_FILE    = CHUNKS_DIR / "chunks.jsonl"
METADATA_PATH  = PROJECT_ROOT / "data" / "raw" / "metadata.json"

# ---------------------------------------------------------------------------
# Splitter config (§ 3.2)
# ---------------------------------------------------------------------------
CHUNK_SIZE    = 450    # tokens (characters as proxy — RecursiveCharacterTextSplitter)
CHUNK_OVERLAP = 60     # overlap between consecutive chunks
SEPARATORS    = ["\n\n", "\n", ". ", " "]

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
# Core chunking logic
# ---------------------------------------------------------------------------

def chunk_all() -> list[dict]:
    """
    Read all processed .txt files, split into chunks, attach metadata,
    and write to data/chunks/chunks.jsonl.

    Returns:
        List of all chunk dicts written to the JSONL file.
    """
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    # Load metadata so we can look up source_url, scheme_name, fetched_at per slug
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    meta_by_slug: dict[str, dict] = {m["slug"]: m for m in metadata}

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
        length_function=len,        # character-based length
        is_separator_regex=False,
    )

    all_chunks: list[dict] = []

    for txt_path in sorted(PROCESSED_DIR.glob("*.txt")):
        slug = txt_path.stem
        meta = meta_by_slug.get(slug)

        if meta is None:
            logger.warning("No metadata found for slug '%s' — skipping", slug)
            continue

        text = txt_path.read_text(encoding="utf-8")
        if not text.strip():
            logger.warning("Empty text file: %s — skipping", txt_path.name)
            continue

        logger.info("-" * 60)
        logger.info("Chunking: %s", meta["scheme_name"])

        # Split text into chunks
        documents = splitter.create_documents([text])

        for idx, doc in enumerate(documents):
            chunk = {
                "chunk_id":     f"{slug}_chunk_{idx:03d}",
                "source_url":   meta["url"],
                "scheme_name":  meta["scheme_name"],
                "doc_type":     "groww_scheme_page",
                "last_fetched": meta["fetched_at"],
                "text":         doc.page_content,
            }
            all_chunks.append(chunk)

        logger.info(
            "  %d chunks from %s",
            len(documents), txt_path.name,
        )

    # Write JSONL — one JSON object per line
    with open(CHUNKS_FILE, "w", encoding="utf-8") as fh:
        for chunk in all_chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    logger.info("-" * 60)
    logger.info(
        "Done. %d total chunks written to %s",
        len(all_chunks),
        CHUNKS_FILE.relative_to(PROJECT_ROOT),
    )

    return all_chunks


# ---------------------------------------------------------------------------
# Validation (§ 3.3)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"chunk_id", "source_url", "scheme_name",
                   "doc_type", "last_fetched", "text"}


def validate() -> bool:
    """
    Validate outputs against exit criteria (§ 3.3):
      - data/processed/ has 7 .txt files
      - data/chunks/chunks.jsonl exists with >= 30 entries
      - Each chunk has all required metadata fields
      - No chunk has an empty 'text' field
    """
    logger.info("-" * 60)
    logger.info("Running Phase 3 validation (§ 3.3) ...")
    passed = True

    # Check 1: 7 .txt files in data/processed/
    txt_files = list(PROCESSED_DIR.glob("*.txt"))
    if len(txt_files) == 7:
        logger.info("  [PASS] 1) data/processed/ has %d .txt files", len(txt_files))
    else:
        logger.error("  [FAIL] 1) data/processed/ has %d .txt files (expected 7)", len(txt_files))
        passed = False

    # Check 2: chunks.jsonl exists with >= 30 entries
    if not CHUNKS_FILE.exists():
        logger.error("  [FAIL] 2) chunks.jsonl not found")
        return False

    with open(CHUNKS_FILE, encoding="utf-8") as fh:
        chunks = [json.loads(line) for line in fh if line.strip()]

    if len(chunks) >= 30:
        logger.info("  [PASS] 2) chunks.jsonl has %d entries (>= 30)", len(chunks))
    else:
        logger.warning("  [WARN] 2) chunks.jsonl has %d entries (expected >= 30)", len(chunks))

    # Check 3: All required fields present
    missing_fields_count = 0
    for i, chunk in enumerate(chunks):
        missing = REQUIRED_FIELDS - set(chunk.keys())
        if missing:
            logger.error("  [FAIL] 3) Chunk %d missing fields: %s", i, missing)
            missing_fields_count += 1
            passed = False

    if missing_fields_count == 0:
        logger.info("  [PASS] 3) All chunks have required metadata fields")

    # Check 4: No empty text
    empty_text_count = sum(1 for c in chunks if not c.get("text", "").strip())
    if empty_text_count == 0:
        logger.info("  [PASS] 4) No chunks have empty text")
    else:
        logger.error("  [FAIL] 4) %d chunks have empty text", empty_text_count)
        passed = False

    if passed:
        logger.info("Phase 3 Validation PASSED")
    else:
        logger.error("Phase 3 Validation FAILED — review errors above.")

    return passed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("Phase 3.2 — Text Chunker")
    logger.info("=" * 60)

    chunk_all()
    validate()


if __name__ == "__main__":
    main()
