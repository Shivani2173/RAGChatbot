"""
Phase 6.3 — Validation Script
Tests prompt building and LLM generation logic.
"""

import logging
import sys
from src.generation.prompt_builder import build_prompt
from src.generation.llm_client import generate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def main():
    print("=" * 60)
    print("Phase 6.3 — Validation")
    print("=" * 60)
    
    # Fake retrieved chunks
    chunks = [
        {
            "scheme_name": "Groww Value Fund",
            "text": "The expense ratio of Groww Value Fund is 0.75%. The fund manager is Jane Doe."
        }
    ]
    
    query = "What is the expense ratio of Groww Value Fund?"
    
    print(f"Testing Query: {query}")
    prompt = build_prompt(query, chunks)
    print("Prompt built successfully. Sending to LLM...")
    
    response = generate(prompt)
    print("\n--- LLM Response ---")
    print(response)
    print("--------------------")
    
    print("\nValidation complete. Please manually verify:")
    print("1. The response is grounded in the provided context (0.75%).")
    print("2. The response is <= 3 sentences.")
    print("3. No hallucination or investment advice.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
