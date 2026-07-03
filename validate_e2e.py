"""
Phase 10 — End-to-End Factual Verification
Tests the entire RAG pipeline against real chunks to see exactly what factual
information the LLM is successfully extracting versus what is missing from the scraped HTML.
"""

import sys
import logging
from src.retrieval.intent_classifier import Intent, classify
from src.retrieval.retriever import retrieve
from src.generation.prompt_builder import build_prompt
from src.generation.llm_client import generate
from src.generation.response_formatter import format_factual

logging.basicConfig(level=logging.ERROR) # Suppress debug logs for clean output

def main():
    print("=" * 70)
    print("End-to-End Factual Verification")
    print("=" * 70)

    # A mix of queries: some we know are in the HTML, some that might be missing (like expense ratio)
    test_queries = [
        "What is the minimum SIP amount for Groww Value Fund?",
        "What is the exit load on Groww Nifty Smallcap 250?",
        "Who is the fund manager of Groww Gold ETF FoF?",
        "What benchmark does Groww Gold ETF FoF track?",
        "What is the expense ratio of Groww Value Fund?"
    ]

    for query in test_queries:
        print(f"\n[QUERY]: {query}")
        
        # 1. Classify
        intent = classify(query)
        if intent != Intent.FACTUAL:
            print(f"  [ERROR] Expected FACTUAL, got {intent.name}")
            continue
            
        # 2. Retrieve
        chunks = retrieve(query, top_k=3)
        if not chunks:
            print("  [RESULT] No relevant context found above threshold.")
            continue
            
        # 3. Generate
        prompt = build_prompt(query, chunks)
        answer = generate(prompt)
        
        # 4. Format
        formatted = format_factual(answer, chunks[0])
        
        # Determine if LLM found the answer or used the fallback phrase
        if "I could not find this information" in formatted.answer:
            print(f"  [STATUS] [FAIL] Data Missing from HTML")
            # Replace ₹ or other unicode in answer for printing
            safe_ans = formatted.answer.encode('ascii', 'ignore').decode('ascii')
            print(f"  [ANSWER] {safe_ans}")
        else:
            print(f"  [STATUS] [PASS] Successfully Answered")
            safe_ans = formatted.answer.encode('ascii', 'ignore').decode('ascii')
            print(f"  [ANSWER] {safe_ans}")
            
    print("\n" + "=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
