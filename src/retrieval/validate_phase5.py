"""
Phase 5.3 — Validation Script
Tests intent classifier + retriever against spec acceptance criteria.
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    from src.retrieval.intent_classifier import Intent, classify
    from src.retrieval.retriever import retrieve

    print("=" * 60)
    print("Phase 5.3 — Validation")
    print("=" * 60)
    passed = True

    # ── Test 1: 5 factual queries → top-1 chunk is relevant ──────────────
    factual_queries = [
        ("What is the expense ratio of Groww Value Fund?", "Value Fund"),
        ("What is the exit load on Groww Nifty Smallcap 250?", "Smallcap 250"),
        ("What benchmark does Groww Gold ETF FoF track?", "Gold ETF"),
        ("What is the minimum SIP for Groww Defence ETF FoF?", "Defence"),
        ("Who is the fund manager of Groww Gold ETF FoF?", "Gold ETF"),
    ]

    print("\n--- Factual Query Retrieval ---")
    for query, expected_substr in factual_queries:
        results = retrieve(query, top_k=3)
        if results:
            top = results[0]
            match = expected_substr.lower() in top["scheme_name"].lower()
            status = "PASS" if match else "WARN"
            if not match:
                passed = False
            print(f"  [{status}] '{query}'")
            print(f"         Top-1: {top['scheme_name']}  score={top['score']:.4f}")
        else:
            print(f"  [FAIL] '{query}' — no results returned")
            passed = False

    # ── Test 2: Advisory query → ADVISORY intent ─────────────────────────
    print("\n--- Advisory Intent Classification ---")
    advisory_tests = [
        ("Should I invest in Groww Value Fund?", Intent.ADVISORY),
        ("Which is the best fund for me?", Intent.ADVISORY),
        ("Is Groww Gold ETF a good investment?", Intent.ADVISORY),
    ]
    for query, expected in advisory_tests:
        result = classify(query)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            passed = False
        print(f"  [{status}] '{query}' -> {result.value} (expected {expected.value})")

    # ── Test 3: PII queries → PII_DETECTED intent ────────────────────────
    print("\n--- PII Detection ---")
    pii_tests = [
        ("My PAN is ABCDE1234F, help me invest", Intent.PII_DETECTED),
        ("My Aadhaar is 1234 5678 9012", Intent.PII_DETECTED),
        ("Contact me at user@example.com", Intent.PII_DETECTED),
    ]
    for query, expected in pii_tests:
        result = classify(query)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            passed = False
        print(f"  [{status}] '{query}' -> {result.value} (expected {expected.value})")

    # ── Test 4: Comparative query ─────────────────────────────────────────
    print("\n--- Comparative Intent ---")
    comp_tests = [
        ("Compare Groww Value Fund vs Groww Gold ETF", Intent.COMPARATIVE),
    ]
    for query, expected in comp_tests:
        result = classify(query)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            passed = False
        print(f"  [{status}] '{query}' -> {result.value} (expected {expected.value})")

    # ── Test 5: Out-of-scope (rule-based won't catch — needs LLM) ────────
    print("\n--- Out-of-scope (LLM fallback) ---")
    oos_tests = [
        "What is the weather today?",
    ]
    for query in oos_tests:
        result = classify(query)
        # Without a valid GROQ key, this will default to FACTUAL — that's OK
        print(f"  [INFO] '{query}' -> {result.value}")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"Phase 5.3 Validation: {'PASS' if passed else 'FAIL'}")
    print("=" * 60)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
