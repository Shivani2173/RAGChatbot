"""
src/retrieval/retriever.py
==========================
Phase 5.2 — Semantic Retriever

Loads the FAISS index and metadata, encodes user queries with the BGE model,
and returns the top-K most similar chunks above a similarity threshold.

Spec reference: ImplementationPlan.md § 5.2
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
PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH   = PROJECT_ROOT / "vector_store" / "faiss_index" / "index.faiss"
VS_METADATA  = PROJECT_ROOT / "vector_store" / "metadata.json"

# ---------------------------------------------------------------------------
# Config (§ 5.2)
# ---------------------------------------------------------------------------
MODEL_NAME          = "BAAI/bge-base-en-v1.5"
DEFAULT_TOP_K       = 5       # § 5.2 step 4: k=5
SIMILARITY_THRESHOLD = 0.65   # § 5.2 step 5: keep only score >= 0.65

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Singleton-ish resource cache (avoid reloading on every query)
# ---------------------------------------------------------------------------
_cache: dict = {}


def _get_model() -> SentenceTransformer:
    """Load (or return cached) SentenceTransformer model."""
    if "model" not in _cache:
        logger.info("Loading embedding model: %s ...", MODEL_NAME)
        _cache["model"] = SentenceTransformer(MODEL_NAME)
    return _cache["model"]


def _get_index():
    """Load (or return cached) FAISS index."""
    if "index" not in _cache:
        logger.info("Loading FAISS index from %s ...", INDEX_PATH)
        _cache["index"] = faiss.read_index(str(INDEX_PATH))
        logger.info("Index loaded: %d vectors", _cache["index"].ntotal)
    return _cache["index"]


def _get_metadata() -> list[dict]:
    """Load (or return cached) chunk metadata."""
    if "metadata" not in _cache:
        _cache["metadata"] = json.loads(VS_METADATA.read_text(encoding="utf-8"))
        logger.info("Metadata loaded: %d entries", len(_cache["metadata"]))
    return _cache["metadata"]


# ---------------------------------------------------------------------------
# Core retrieval
# ---------------------------------------------------------------------------

def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    scheme_name: str | None = None,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict]:
    """
    Retrieve the most relevant chunks for a user query (§ 5.2).

    Args:
        query:       The user's natural-language question.
        top_k:       Maximum number of results to return.
        scheme_name: Optional filter — keep only chunks from this scheme.
        threshold:   Minimum similarity score to include a result.

    Returns:
        List of dicts, each containing:
          { text, source_url, scheme_name, last_fetched, score }
        Ordered by descending similarity score.
    """
    model    = _get_model()
    index    = _get_index()
    metadata = _get_metadata()

    # Step 3: Encode query (§ 5.2)
    query_vec = model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec, dtype=np.float32)

    # Step 4: Search FAISS index
    # Over-fetch when filtering by scheme_name so we still get enough results
    search_k = top_k * 3 if scheme_name else top_k
    distances, indices = index.search(query_vec, k=min(search_k, index.ntotal))

    # Step 5 & 6: Filter by threshold + optional scheme_name filter
    results: list[dict] = []

    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue  # FAISS sentinel for fewer results than k

        score = float(dist)
        if score < threshold:
            continue  # Step 5: below similarity threshold

        chunk_meta = metadata[idx]

        # Step 6: Optional scheme filter (case-insensitive substring match)
        if scheme_name:
            if scheme_name.lower() not in chunk_meta["scheme_name"].lower():
                continue

        results.append({
            "text":         chunk_meta["text"],
            "source_url":   chunk_meta["source_url"],
            "scheme_name":  chunk_meta["scheme_name"],
            "last_fetched": chunk_meta["last_fetched"],
            "score":        score,
        })

        if len(results) >= top_k:
            break

    logger.info(
        "Retrieved %d chunks for query '%s' (threshold=%.2f)",
        len(results), query[:60], threshold,
    )

    return results
