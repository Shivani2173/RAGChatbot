"""
src/generation/prompt_builder.py
================================
Phase 6.1 -- Prompt Builder

Constructs the system prompt and user prompt for the LLM,
embedding retrieved chunks as grounding context.

Spec reference: ImplementationPlan.md SS 6.1
"""

# ---------------------------------------------------------------------------
# System prompt (SS 6.1)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a facts-only FAQ assistant for Groww Mutual Fund schemes.

Rules you must follow strictly:
1. Answer ONLY using the context provided. Do not add any outside knowledge.
2. Keep your answer to a maximum of 3 sentences.
3. Do NOT give investment advice, opinions, or recommendations.
4. Do NOT compare funds or predict future returns.
5. If the answer is not found in the context, say:
   "I could not find this information in the available data.
    Please visit [source_url] for the latest details."
6. Do not use phrases like "I think", "you should", or "it is better"."""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(query: str, chunks: list[dict]) -> str:
    """
    Build the user-role prompt that includes context and the question.

    The system prompt is sent separately as the system message.
    This function builds only the user-facing portion so the LLM client
    can set ``messages`` correctly.

    Args:
        query:  The user's natural-language question.
        chunks: Retrieved chunks from the vector store (each has 'scheme_name' and 'text').

    Returns:
        A formatted string combining CONTEXT + USER QUESTION.
    """
    context_block = "\n\n".join(
        f"[Source: {c['scheme_name']}]\n{c['text']}" for c in chunks
    )
    return f"CONTEXT:\n{context_block}\n\nUSER QUESTION:\n{query}\n\nANSWER:"
