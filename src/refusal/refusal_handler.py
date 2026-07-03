"""
src/refusal/refusal_handler.py
==============================
Phase 7 — Refusal & Safety Handler

Provides compliant, polite refusal messages for non-factual queries.
Includes templates for ADVISORY, COMPARATIVE, PII_DETECTED, and OUT_OF_SCOPE intents.

Spec reference: ImplementationPlan.md § 7.1
"""

import logging
from src.retrieval.intent_classifier import Intent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Refusal Templates (§ 7.1)
# ---------------------------------------------------------------------------

REFUSAL_TEMPLATES = {
    "ADVISORY": (
        "I can only answer factual questions about Groww mutual fund schemes, "
        "such as expense ratios, exit loads, minimum SIP amounts, or benchmark indices.\n\n"
        "For investment guidance, please consult a SEBI-registered investment advisor. "
        "Learn more: https://www.amfiindia.com/investor-corner/knowledge-center"
    ),

    "COMPARATIVE": (
        "I'm unable to compare fund performance or recommend one fund over another.\n\n"
        "I can share factual details (like expense ratios or benchmarks) for each scheme individually. "
        "For scheme-wise data, please visit the official Groww scheme pages."
    ),

    "PII_DETECTED": (
        "I noticed your message may contain sensitive personal information (such as a PAN, "
        "Aadhaar, or account number).\n\n"
        "For your security, please do not share this information here. "
        "This assistant does not collect or store any personal data."
    ),

    "OUT_OF_SCOPE": (
        "This assistant only answers factual questions about Groww mutual fund schemes.\n\n"
        "Your question appears to be outside this scope. "
        "For mutual fund education, visit: https://www.amfiindia.com/investor-corner"
    )
}

# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def get_refusal(intent: Intent) -> str:
    """
    Return the appropriate refusal message for a given non-factual intent.
    Falls back to OUT_OF_SCOPE if the intent is missing or FACTUAL.
    """
    logger.info("Generating refusal for intent: %s", intent.value)
    
    # FACTUAL queries shouldn't reach here, but fallback to OUT_OF_SCOPE just in case.
    if intent == Intent.FACTUAL:
        logger.warning("get_refusal called with FACTUAL intent. This is unexpected.")
        return REFUSAL_TEMPLATES["OUT_OF_SCOPE"]

    return REFUSAL_TEMPLATES.get(intent.value, REFUSAL_TEMPLATES["OUT_OF_SCOPE"])
