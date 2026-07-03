"""
Phase 7.2 — Validation Script
Tests refusal handler for all non-factual query types.
"""

import logging
import sys

from src.retrieval.intent_classifier import Intent, classify
from src.refusal.refusal_handler import get_refusal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def main():
    print("=" * 60)
    print("Phase 7.2 — Validation")
    print("=" * 60)

    tests = [
        ("Should I invest my life savings in Groww Value Fund?", Intent.ADVISORY),
        ("Compare Groww Value Fund and Groww Nifty Smallcap 250.", Intent.COMPARATIVE),
        ("My PAN is ABCDE1234F. What is the NAV?", Intent.PII_DETECTED),
        ("How to fix my car engine?", Intent.OUT_OF_SCOPE)
    ]

    passed = True

    for query, expected_intent in tests:
        print(f"\n[Test Query]: {query}")
        intent = classify(query)
        
        if intent != expected_intent:
            print(f"  [FAIL] Classified as {intent.value}, expected {expected_intent.value}")
            passed = False
            continue
            
        print(f"  [PASS] Correctly classified as {intent.value}")
        
        refusal_msg = get_refusal(intent)
        print("  [Refusal Message]:")
        print("    " + refusal_msg.replace("\n", "\n    "))
        
        # Verify educational link presence if applicable
        if intent in [Intent.ADVISORY, Intent.OUT_OF_SCOPE]:
            if "amfiindia.com" not in refusal_msg.lower():
                print("  [FAIL] Missing AMFI educational link!")
                passed = False
            else:
                print("  [PASS] Contains educational link.")
                
        # Confirm PII triggers correctly and early
        if intent == Intent.PII_DETECTED:
            if "collect or store any personal data" not in refusal_msg.lower():
                print("  [FAIL] PII message not polite or missing disclaimer.")
                passed = False
            else:
                print("  [PASS] PII refusal is compliant.")

    print("\n" + "=" * 60)
    print(f"Phase 7 Validation: {'PASS' if passed else 'FAIL'}")
    print("=" * 60)

    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
