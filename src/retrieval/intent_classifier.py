"""
src/retrieval/intent_classifier.py
===================================
Phase 5.1 — Intent Classifier

Two-stage classification for user queries:
  Stage 1 — Rule-based pre-filter (advisory keywords + PII regex)
  Stage 2 — LLM fallback for ambiguous queries (Groq API)

Spec reference: ImplementationPlan.md § 5.1
"""

import logging
import os
import re
from enum import Enum

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent Enum (§ 5.1)
# ---------------------------------------------------------------------------

class Intent(Enum):
    FACTUAL      = "FACTUAL"
    ADVISORY     = "ADVISORY"
    COMPARATIVE  = "COMPARATIVE"
    PII_DETECTED = "PII_DETECTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


# ---------------------------------------------------------------------------
# Stage 1 — Rule-based patterns (§ 5.1)
# ---------------------------------------------------------------------------

# Advisory keywords (case-insensitive substring match)
ADVISORY_KEYWORDS = [
    "should i",
    "recommend",
    "which is better",
    "best fund",
    "should invest",
    "worth buying",
    "good investment",
    "is it safe",
    "can i trust",
    "worth it",
    "suggest",
    "advise",
    "which one",
    "better option",
    "best option",
    "good choice",
    "right choice",
    "should i buy",
    "should i sell",
    "will it grow",
    "predict",
    "future returns",
]

# Comparative keywords
COMPARATIVE_KEYWORDS = [
    "compare",
    "comparison",
    "versus",
    " vs ",
    "which is better",
    "difference between",
    "better than",
    "worse than",
    "outperform",
]

# PII patterns (§ 5.1)
PII_PATTERNS = [
    # Indian PAN: 5 letters + 4 digits + 1 letter  (e.g. ABCDE1234F)
    re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    # Aadhaar: 12 digits (optionally space/dash separated in groups of 4)
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    # Bank account number: 9-18 consecutive digits
    re.compile(r"\b\d{9,18}\b"),
    # Email address
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    # Phone number (Indian 10 digits, optionally +91 prefix)
    re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"),
]


# ---------------------------------------------------------------------------
# Stage 2 — LLM classification prompt (§ 5.1)
# ---------------------------------------------------------------------------

CLASSIFICATION_PROMPT = """Classify this user query as exactly one of the following labels:
FACTUAL, ADVISORY, COMPARATIVE, OUT_OF_SCOPE

Rules:
- FACTUAL: The query asks for a specific fact about a Groww mutual fund scheme
  (e.g. expense ratio, exit load, NAV, benchmark, fund manager, AUM, SIP amount).
- ADVISORY: The query asks for investment advice, opinions, or recommendations.
- COMPARATIVE: The query asks to compare two or more funds or asks which fund is better.
- OUT_OF_SCOPE: The query is unrelated to Groww mutual fund schemes.

Reply with the label ONLY. No explanation.

Query: {query}"""


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def _check_pii(query: str) -> bool:
    """Return True if the query contains PII patterns."""
    for pattern in PII_PATTERNS:
        if pattern.search(query):
            return True
    return False


def _check_advisory(query: str) -> bool:
    """Return True if the query contains advisory keywords."""
    query_lower = query.lower()
    return any(kw in query_lower for kw in ADVISORY_KEYWORDS)


def _check_comparative(query: str) -> bool:
    """Return True if the query contains comparative keywords."""
    query_lower = query.lower()
    return any(kw in query_lower for kw in COMPARATIVE_KEYWORDS)


def _llm_classify(query: str) -> Intent:
    """
    Stage 2 — Use Groq LLM to classify ambiguous queries.

    Falls back to FACTUAL if the LLM returns an unexpected label
    or if the API call fails.
    """
    try:
        import groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            logger.warning("GROQ_API_KEY not set — defaulting to FACTUAL")
            return Intent.FACTUAL

        client = groq.Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": CLASSIFICATION_PROMPT.format(query=query)},
            ],
            temperature=0.0,
            max_tokens=10,
        )
        label = response.choices[0].message.content.strip().upper()

        # Map to Intent enum
        try:
            return Intent(label)
        except ValueError:
            logger.warning("LLM returned unexpected label '%s' — defaulting to FACTUAL", label)
            return Intent.FACTUAL

    except Exception as exc:
        logger.error("LLM classification failed: %s — defaulting to FACTUAL", exc)
        return Intent.FACTUAL


def classify(query: str) -> Intent:
    """
    Two-stage intent classification (§ 5.1).

    Stage 1: Rule-based pre-filter (instant, no API call)
    Stage 2: LLM fallback for ambiguous queries

    Args:
        query: The user's raw query string.

    Returns:
        An Intent enum member.
    """
    query = query.strip()

    if not query:
        return Intent.OUT_OF_SCOPE

    # ── Stage 1: Rule-based pre-filter ────────────────────────────────────

    # PII check takes highest priority (hard block)
    if _check_pii(query):
        logger.info("Intent: PII_DETECTED (rule-based)")
        return Intent.PII_DETECTED

    # Advisory check
    if _check_advisory(query):
        logger.info("Intent: ADVISORY (rule-based)")
        return Intent.ADVISORY

    # Comparative check
    if _check_comparative(query):
        logger.info("Intent: COMPARATIVE (rule-based)")
        return Intent.COMPARATIVE

    # ── Stage 2: LLM fallback ─────────────────────────────────────────────
    intent = _llm_classify(query)
    logger.info("Intent: %s (LLM)", intent.value)
    return intent
