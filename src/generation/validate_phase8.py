"""
Phase 8.4 — Validation Script
Tests the response formatter for both factual and refusal envelopes.
"""

import sys
from src.generation.response_formatter import format_factual, format_refusal, render_to_terminal

def main():
    print("=" * 70)
    print("Phase 8.4 — Validation")
    print("=" * 70)

    # 1. Test Factual Response
    print("\n--- Factual Response Test ---\n")
    
    mock_chunk = {
        "scheme_name": "Groww Gold ETF FoF",
        "source_url": "https://groww.in/mutual-funds/groww-gold-etf-fof-direct-growth",
        "last_fetched": "2026-06-30T16:13:13.448981+00:00"
    }
    llm_answer = "The expense ratio of Groww Gold ETF FoF is 0.10% per annum."
    
    factual_resp = format_factual(llm_answer, mock_chunk)
    
    passed_factual = True
    if factual_resp.answer != llm_answer: passed_factual = False
    if factual_resp.citation_label != "Groww Gold ETF FoF – Groww Scheme Page": passed_factual = False
    if factual_resp.citation_url != mock_chunk["source_url"]: passed_factual = False
    if factual_resp.last_updated != "2026-06-30": passed_factual = False
    if factual_resp.is_refusal is not False: passed_factual = False
    
    print(render_to_terminal(factual_resp))
    print(f"\nFactual formatting check: {'PASS' if passed_factual else 'FAIL'}")

    # 2. Test Refusal Response
    print("\n--- Refusal Response Test ---\n")
    
    refusal_msg = "This assistant only answers factual questions about Groww mutual fund schemes."
    
    refusal_resp = format_refusal(refusal_msg)
    
    passed_refusal = True
    if refusal_resp.answer != refusal_msg: passed_refusal = False
    if refusal_resp.citation_label != "AMFI Investor Education": passed_refusal = False
    if refusal_resp.citation_url != "https://www.amfiindia.com/investor-corner": passed_refusal = False
    if refusal_resp.is_refusal is not True: passed_refusal = False
    
    print(render_to_terminal(refusal_resp))
    print(f"\nRefusal formatting check: {'PASS' if passed_refusal else 'FAIL'}")

    # Final summary
    passed_all = passed_factual and passed_refusal
    print("\n" + "=" * 70)
    print(f"Phase 8 Validation: {'PASS' if passed_all else 'FAIL'}")
    print("=" * 70)

    return 0 if passed_all else 1

if __name__ == "__main__":
    sys.exit(main())
