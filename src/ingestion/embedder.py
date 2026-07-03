"""
src/ingestion/embedder.py
=========================
Phase 4 — Embedding & Vector Store

Embeds all chunks from data/chunks/chunks.jsonl using the BGE embedding model,
builds a FAISS flat inner-product index, and persists the index + metadata to disk.

Spec reference: ImplementationPlan.md § 4.1 – 4.3
"""

import json
import logging
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT    = Path(__file__).resolve().parents[2]
CHUNKS_FILE     = PROJECT_ROOT / "data" / "chunks" / "chunks.jsonl"
INDEX_DIR       = PROJECT_ROOT / "vector_store" / "faiss_index"
INDEX_PATH      = INDEX_DIR / "index.faiss"
VS_METADATA     = PROJECT_ROOT / "vector_store" / "metadata.json"

# ---------------------------------------------------------------------------
# Model config (§ 4.1)
# ---------------------------------------------------------------------------
MODEL_NAME      = "BAAI/bge-base-en-v1.5"
EMBEDDING_DIM   = 768   # bge-base output dimension

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
# Core embedding logic
# ---------------------------------------------------------------------------

def load_chunks() -> list[dict]:
    """Load all chunks from data/chunks/chunks.jsonl (§ 4.1 step 1)."""
    chunks: list[dict] = []
    with open(CHUNKS_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    logger.info("Loaded %d chunks from %s", len(chunks), CHUNKS_FILE.relative_to(PROJECT_ROOT))
    return chunks


def build_index(chunks: list[dict]) -> None:
    """
    Embed all chunks, build FAISS index, and persist to disk (§ 4.1 steps 2-6).

    The index uses IndexFlatIP (inner product) which is equivalent to
    cosine similarity when embeddings are L2-normalised.
    """
    # Step 2: Initialize BGE embedding model
    logger.info("Loading embedding model: %s ...", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Model loaded.")

    # Step 3: Encode all chunk texts with normalisation
    texts = [chunk["text"] for chunk in chunks]
    logger.info("Encoding %d chunks ...", len(texts))
    vectors = model.encode(
        texts,
        normalize_embeddings=True,   # L2 normalise so IP == cosine sim
        show_progress_bar=True,
        batch_size=32,
    )
    vectors = np.array(vectors, dtype=np.float32)
    logger.info("Embeddings shape: %s", vectors.shape)

    # Step 4: Build FAISS index — flat inner-product (§ 4.1 step 4)
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(vectors)
    logger.info("FAISS index built: %d vectors, dim=%d", index.ntotal, EMBEDDING_DIM)

    # Step 5: Save index to disk
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    logger.info("Index saved to %s", INDEX_PATH.relative_to(PROJECT_ROOT))

    # Step 6: Save ordered metadata (position i ↔ vector i)
    metadata = [
        {
            "chunk_id":     c["chunk_id"],
            "source_url":   c["source_url"],
            "scheme_name":  c["scheme_name"],
            "last_fetched": c["last_fetched"],
            "text":         c["text"],
        }
        for c in chunks
    ]
    VS_METADATA.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(
        "Metadata saved to %s (%d entries)",
        VS_METADATA.relative_to(PROJECT_ROOT), len(metadata),
    )


# ---------------------------------------------------------------------------
# Smoke test (§ 4.3)
# ---------------------------------------------------------------------------

def smoke_test() -> bool:
    """
    Validate the persisted index (§ 4.3):
      - index.faiss exists and is readable
      - metadata.json has same count as index vectors
      - Encode a test query → retrieve top-3 → confirm fund-related
    """
    logger.info("-" * 60)
    logger.info("Running Phase 4 validation (§ 4.3) ...")
    passed = True

    # Check 1: index file exists and loads
    if not INDEX_PATH.exists():
        logger.error("  [FAIL] index.faiss not found at %s", INDEX_PATH)
        return False

    index = faiss.read_index(str(INDEX_PATH))
    logger.info("  [PASS] 1) index.faiss loaded — %d vectors", index.ntotal)

    # Check 2: metadata count matches
    metadata = json.loads(VS_METADATA.read_text(encoding="utf-8"))
    if len(metadata) == index.ntotal:
        logger.info("  [PASS] 2) metadata.json has %d entries (matches index)", len(metadata))
    else:
        logger.error(
            "  [FAIL] 2) metadata count (%d) != index count (%d)",
            len(metadata), index.ntotal,
        )
        passed = False

    # Check 3: Smoke test — query → top-3 results
    test_queries = [
        "What is the expense ratio of Groww Value Fund?",
        "What is the exit load on Groww Nifty Smallcap 250?",
        "What benchmark does Groww Gold ETF FoF track?",
    ]

    model = SentenceTransformer(MODEL_NAME)

    for query in test_queries:
        query_vec = model.encode([query], normalize_embeddings=True)
        query_vec = np.array(query_vec, dtype=np.float32)
        distances, indices = index.search(query_vec, k=3)

        logger.info("  Query: '%s'", query)
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0]), 1):
            chunk_meta = metadata[idx]
            logger.info(
                "    #%d  score=%.4f  scheme=%s  chunk=%s",
                rank, dist, chunk_meta["scheme_name"], chunk_meta["chunk_id"],
            )
            # Preview first 80 chars of text
            logger.info("        text: %s...", chunk_meta["text"][:80])

    if passed:
        logger.info("Phase 4 Validation PASSED")
    else:
        logger.error("Phase 4 Validation FAILED")

    return passed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("Phase 4 — Embedding & Vector Store")
    logger.info("=" * 60)

    chunks = load_chunks()
    build_index(chunks)
    smoke_test()


if __name__ == "__main__":
    main()
