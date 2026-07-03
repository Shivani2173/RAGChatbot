"""
Direct LLM test — bypasses retriever (no network needed for model load).
Uses the actual chunk text to test if the LLM can answer from it.
"""
import os
from dotenv import load_dotenv
load_dotenv()

import groq
from src.generation.prompt_builder import SYSTEM_PROMPT, build_prompt

# Manually craft the chunk that the retriever SHOULD be returning
test_chunk = {
    "scheme_name": "Groww Value Fund - Direct Growth",
    "text": """Groww Value Fund Direct Growth - NAV, Mutual Fund Performance & Portfolio
NAV: 29 Jun 26
The expense ratio of this fund is 1.57%.
Expense Ratio: 1.57%
The benchmark index tracked by this fund is NIFTY 500 Total Return Index.
Benchmark Index: NIFTY 500 Total Return Index
Fund size (AUM)
Net Receivables
The Groww Value Fund Direct Growth is rated Very High risk. Minimum SIP Investment is set to 500. Minimum Lumpsum Investment is 500. Exit load of 1% if redeemed within 1 year."""
}

query = "What is the expense ratio of Groww Value Fund?"
prompt = build_prompt(query, [test_chunk])

print("=== PROMPT SENT TO LLM ===")
print(prompt)
print()

api_key = os.getenv("GROQ_API_KEY")
client = groq.Groq(api_key=api_key)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ],
    temperature=0.0,
    max_tokens=200,
)
print("=== LLM ANSWER ===")
answer = response.choices[0].message.content.strip()
safe = answer.encode('ascii', 'ignore').decode('ascii')
print(safe)
