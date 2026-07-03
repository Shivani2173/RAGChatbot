"""
src/generation/response_formatter.py
====================================
Phase 8 — Response Formatter

Wraps factual and refusal responses in a standardized envelope,
providing citations, metadata, and safety disclaimers for the UI.

Spec reference: ImplementationPlan.md § 8.1 - 8.2
"""

from dataclasses import dataclass
from datetime import datetime

# ---------------------------------------------------------------------------
# Envelope Structure (§ 8.1)
# ---------------------------------------------------------------------------

@dataclass
class FormattedResponse:
    answer: str
    citation_label: str
    citation_url: str
    last_updated: str
    disclaimer: str
    is_refusal: bool

# The constant disclaimer for all responses
DISCLAIMER_TEXT = "Facts-only. No investment advice."

# ---------------------------------------------------------------------------
# Formatting Logic (§ 8.2)
# ---------------------------------------------------------------------------

def format_factual(answer: str, top_chunk: dict) -> FormattedResponse:
    """
    Format a factual response using metadata from the top-ranked retrieved chunk.
    
    Args:
        answer: The LLM-generated factual answer.
        top_chunk: The highest-scoring chunk from the retriever.
                   Must contain 'scheme_name', 'source_url', and 'last_fetched'.
    """
    # Parse last_fetched (e.g. "2026-06-30T16:13:13.448981+00:00") into YYYY-MM-DD
    last_fetched_raw = top_chunk.get("last_fetched", "")
    try:
        dt = datetime.fromisoformat(last_fetched_raw)
        last_updated = dt.strftime("%Y-%m-%d")
    except ValueError:
        # Fallback to current date if parsing fails
        last_updated = datetime.now().strftime("%Y-%m-%d")

    return FormattedResponse(
        answer=answer,
        citation_label=f"{top_chunk.get('scheme_name', 'Unknown Scheme')} – Groww Scheme Page",
        citation_url=top_chunk.get("source_url", "https://groww.in/mutual-funds"),
        last_updated=last_updated,
        disclaimer=DISCLAIMER_TEXT,
        is_refusal=False,
    )


def format_refusal(refusal_msg: str) -> FormattedResponse:
    """
    Format a refusal response with standard educational citations.
    
    Args:
        refusal_msg: The refusal text from refusal_handler.py.
    """
    return FormattedResponse(
        answer=refusal_msg,
        citation_label="AMFI Investor Education",
        citation_url="https://www.amfiindia.com/investor-corner",
        last_updated=datetime.now().strftime("%Y-%m-%d"),
        disclaimer=DISCLAIMER_TEXT,
        is_refusal=True,
    )


# ---------------------------------------------------------------------------
# Terminal Rendering Helper (For validation / debugging)
# ---------------------------------------------------------------------------

def render_to_terminal(resp: FormattedResponse) -> str:
    """Renders the envelope in a clean ASCII box for terminal output (§ 8.3)."""
    lines = [
        "+" + "-" * 70 + "+",
        f"| {resp.answer}".ljust(71) + "|",
        "|" + " " * 70 + "|",
        f"| [Source]: {resp.citation_label}".ljust(71) + "|",
        f"|    {resp.citation_url}".ljust(71) + "|",
        "|" + " " * 70 + "|",
        f"| [Last updated]: {resp.last_updated}".ljust(71) + "|",
        f"| [!] {resp.disclaimer}".ljust(71) + "|",
        "+" + "-" * 70 + "+",
    ]
    return "\n".join(lines)
