# Phase-Wise Implementation Plan
## Mutual Fund FAQ RAG Chatbot — Groww AMC

> **Stack**: Python 3.10+ | LangChain | FAISS | BGE Embeddings | Groq LLM | Streamlit
> **Corpus**: 7 official Groww scheme page URLs (HTML-only)
> **Principle**: Facts-only. No investment advice.

---

## Overview of Phases

| Phase | Name | Goal | Deliverable |
|---|---|---|---|
| **Phase 1** | Project Setup & Environment | Initialize project structure and dependencies | Runnable dev environment |
| **Phase 2** | Data Ingestion Pipeline | Scrape & persist raw content from 7 Groww URLs | `data/raw/` with cleaned HTML text |
| **Phase 3** | Document Processing & Chunking | Parse, clean, and chunk scraped content | `data/chunks/` JSONL files |
| **Phase 4** | Embedding & Vector Store | Embed chunks and build searchable index | `vector_store/` FAISS index |
| **Phase 5** | Query Engine (Retriever + Classifier) | Intent classification + semantic retrieval | Working retrieval pipeline |
| **Phase 6** | LLM Response Generation | Prompt construction + LLM integration | End-to-end RAG response |
| **Phase 7** | Refusal & Safety Handler | PII detection + advisory query refusals | Compliant refusal system |
| **Phase 8** | Response Formatter | Standardize output with citation + footer | Structured response envelope |
| **Phase 9** | User Interface (Streamlit) | Build the chat UI with disclaimer | Working chatbot UI |
| **Phase 10** | Integration & End-to-End Testing | Wire all phases together and validate | Full working chatbot |
| **Phase 11** | Daily Data Refresh Scheduler | Auto-trigger ingestion pipeline daily | Always-fresh FAISS index |

---

## Phase 1 — Project Setup & Environment

**Goal**: Bootstrap the project repository with all dependencies, config files, and folder structure.

### 1.1 Initialize Project Directory

Create the following folder structure (aligns with `Architecture.md § 7`):

```
RAGChatbot/
├── Docs/
├── data/
│   ├── raw/
│   ├── processed/
│   └── chunks/
├── vector_store/
│   └── faiss_index/
├── src/
│   ├── ingestion/
│   ├── retrieval/
│   ├── generation/
│   ├── refusal/
│   └── ui/
├── config/
├── .env
├── requirements.txt
└── README.md
```

### 1.2 Create `requirements.txt`

```txt
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.2.2
langchain==0.2.0
langchain-community==0.2.0
sentence-transformers==3.0.1      # for BGE model
faiss-cpu==1.8.0
groq==0.9.0                        # Groq LLM API client
python-dotenv==1.0.1
streamlit==1.35.0
pydantic==2.7.0
```

### 1.3 Create `config/urls.yaml`

```yaml
corpus:
  schemes:
    - name: "Groww Gold ETF FoF - Direct Growth"
      url: "https://groww.in/mutual-funds/groww-gold-etf-fof-direct-growth"
      category: "Gold / FoF"

    - name: "Groww Nifty India Defence ETF FoF - Direct Growth"
      url: "https://groww.in/mutual-funds/groww-nifty-india-defence-etf-fof-direct-growth"
      category: "Sectoral / Defence"

    - name: "Groww Nifty Total Market Index Fund - Direct Growth"
      url: "https://groww.in/mutual-funds/groww-nifty-total-market-index-fund-direct-growth"
      category: "Index / Broad Market"

    - name: "Groww Nifty EV & New Age Automotive ETF FoF - Direct Growth"
      url: "https://groww.in/mutual-funds/groww-nifty-ev-new-age-automotive-etf-fof-direct-growth"
      category: "Sectoral / EV & Auto"

    - name: "Groww Nifty Smallcap 250 Index Fund - Direct Growth"
      url: "https://groww.in/mutual-funds/groww-nifty-smallcap-250-index-fund-direct-growth"
      category: "Index / Small Cap"

    - name: "Groww Value Fund - Direct Growth"
      url: "https://groww.in/mutual-funds/groww-value-fund-direct-growth"
      category: "Value / Active Equity"

    - name: "Groww Nifty Non-Cyclical Consumer Index Fund - Direct Growth"
      url: "https://groww.in/mutual-funds/groww-nifty-non-cyclical-consumer-index-fund-direct-growth"
      category: "Index / Consumer"
```

### 1.4 Create `.env`

```env
# Groq API key — get yours at https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here
```

### 1.5 Verify Setup

```bash
pip install -r requirements.txt
python -c "import langchain, faiss, sentence_transformers, groq, streamlit; print('Setup OK')"
```

**Exit Criteria**: All packages install without errors; folder structure exists.

---

## Phase 2 — Data Ingestion Pipeline

**Goal**: Fetch and persist the raw HTML text content from each of the 7 Groww scheme URLs.

**Files to create**:
- `src/ingestion/fetcher.py`

### 2.1 `fetcher.py` — Logic

```
For each scheme in config/urls.yaml:
  1. Send HTTP GET to the scheme URL
     - Set User-Agent header to avoid bot-blocking
     - Retry up to 3 times on failure (with backoff)
  2. On success (HTTP 200):
     - Save raw HTML response body to data/raw/<scheme_slug>.html
     - Save metadata: {scheme_name, url, category, fetched_at}
  3. On failure:
     - Log the error and skip
     - Raise alert if more than 2 URLs fail
```

### 2.2 Key Implementation Details

| Detail | Value |
|---|---|
| HTTP timeout | 15 seconds |
| Retry attempts | 3 (with 2s exponential backoff) |
| User-Agent | `Mozilla/5.0 (compatible; RAGBot/1.0)` |
| Output format | `data/raw/groww_gold_etf_fof.html` |
| Metadata file | `data/raw/metadata.json` |

### 2.3 Validation

- All 7 files exist in `data/raw/`
- Each HTML file is non-empty (> 5 KB)
- `metadata.json` contains `fetched_at` timestamp for all 7 schemes

**Exit Criteria**: 7 HTML files saved to `data/raw/` with metadata.

---

## Phase 3 — Document Processing & Chunking

**Goal**: Parse the raw HTML, extract factual text, and split it into overlapping chunks.

**Files to create**:
- `src/ingestion/parser.py`
- `src/ingestion/chunker.py`

### 3.1 `parser.py` — Logic

```
For each .html file in data/raw/:
  1. Load HTML with BeautifulSoup (lxml parser)
  2. Remove unwanted tags:
     - <nav>, <header>, <footer>, <script>, <style>,
       <aside>, cookie-banner divs, advertisement sections
  3. Extract main content:
     - Target main scheme content area
     - Extract: fund name, category, expense ratio, exit load,
       minimum SIP, benchmark, riskometer, NAV, fund manager info
  4. Clean text:
     - Normalize whitespace (collapse multiple spaces/newlines)
     - Strip special unicode characters
     - Remove lines shorter than 15 characters (boilerplate)
  5. Save cleaned text to data/processed/<scheme_slug>.txt
```

### 3.2 `chunker.py` — Logic

```
For each .txt file in data/processed/:
  1. Load cleaned text
  2. Apply LangChain RecursiveCharacterTextSplitter:
       chunk_size = 450 tokens
       chunk_overlap = 60 tokens
       separators = ["\n\n", "\n", ". ", " "]
  3. For each chunk, attach metadata:
       {
         chunk_id: "<scheme_slug>_chunk_<index>",
         source_url: "<original groww url>",
         scheme_name: "<full scheme name>",
         doc_type: "groww_scheme_page",
         last_fetched: "<ISO date>",
         text: "<chunk text>"
       }
  4. Append all chunks to data/chunks/chunks.jsonl
```

### 3.3 Validation

- `data/processed/` has 7 `.txt` files
- `data/chunks/chunks.jsonl` exists with at least 30–50 chunk entries
- Each chunk JSON has all required metadata fields
- No chunk has an empty `text` field

**Exit Criteria**: `data/chunks/chunks.jsonl` populated with clean, metadata-tagged chunks.

---

## Phase 4 — Embedding & Vector Store

**Goal**: Embed all chunks and build a persistent FAISS vector index for fast semantic retrieval.

**Files to create**:
- `src/ingestion/embedder.py`

### 4.1 `embedder.py` — Logic

```
1. Load all chunks from data/chunks/chunks.jsonl
2. Initialize BGE embedding model:
     model = SentenceTransformer("BAAI/bge-base-en-v1.5")
3. For each chunk:
     # BGE requires a query prefix for retrieval tasks
     vector = model.encode(chunk["text"], normalize_embeddings=True)
4. Build FAISS index:
     index = faiss.IndexFlatIP(768)   # 768 dims for bge-base; inner product (cosine sim)
     index.add(all_vectors)
5. Save to disk:
     faiss.write_index(index, "vector_store/faiss_index/index.faiss")
6. Save metadata separately:
     Save list of {chunk_id, source_url, scheme_name, last_fetched, text}
     to vector_store/metadata.json
     (preserves order matching FAISS index positions)
```

### 4.2 Index Design

```
vector_store/
├── faiss_index/
│   └── index.faiss          ← FAISS flat inner-product index
└── metadata.json            ← Ordered list of chunk metadata (index i = vector i)
```

### 4.3 Validation

- `vector_store/faiss_index/index.faiss` exists and is readable
- `vector_store/metadata.json` has same count of entries as chunks
- Run a smoke test: encode a test query → retrieve top-3 results → confirm they are fund-related

**Exit Criteria**: FAISS index built, persisted, and returning sensible results on test queries.

---

## Phase 5 — Query Engine (Retriever + Intent Classifier)

**Goal**: Given a user query, classify its intent and retrieve the most relevant chunks.

**Files to create**:
- `src/retrieval/intent_classifier.py`
- `src/retrieval/retriever.py`

### 5.1 `intent_classifier.py` — Logic

**Two-stage classification** (fast pre-filter + LLM fallback):

```
Stage 1 — Rule-Based Pre-filter:
  Check for advisory keywords:
    ["should I", "recommend", "which is better", "best fund",
     "should invest", "worth buying", "good investment"]
  Check for PII patterns (regex):
    PAN, Aadhaar, account number, email
  → If matched: return intent = ADVISORY | PII_DETECTED

Stage 2 — LLM Classification (for ambiguous queries):
  Prompt:
    "Classify this query as one of: FACTUAL, ADVISORY,
     COMPARATIVE, OUT_OF_SCOPE. Reply with the label only.
     Query: {user_query}"
  → Parse LLM response → return intent label
```

**Intent Enum**:

```python
class Intent(Enum):
    FACTUAL = "FACTUAL"
    ADVISORY = "ADVISORY"
    COMPARATIVE = "COMPARATIVE"
    PII_DETECTED = "PII_DETECTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
```

### 5.2 `retriever.py` — Logic

```
Input: user_query (str), optional scheme_name filter

1. Load FAISS index from vector_store/faiss_index/index.faiss
2. Load metadata from vector_store/metadata.json
3. Encode user_query:
     query_vector = model.encode(user_query)
4. Search FAISS index:
     distances, indices = index.search(query_vector, k=5)
5. Filter by similarity threshold:
     Keep only chunks with score >= 0.65
6. Optional: filter by scheme_name if query mentions a specific fund
7. Return top-K chunks as list of:
     { text, source_url, scheme_name, last_fetched, score }
```

### 5.3 Validation

- Test with 5 sample factual queries → confirm top-1 chunk is relevant
- Test advisory query → classifier returns `ADVISORY`
- Test PII-containing query → classifier returns `PII_DETECTED`

**Exit Criteria**: Retriever returns relevant chunks; classifier correctly tags all intent types.

---

## Phase 6 — LLM Response Generation

**Goal**: Use retrieved chunks as context and generate a short, factual, grounded answer.

**Files to create**:
- `src/generation/prompt_builder.py`
- `src/generation/llm_client.py`

### 6.1 `prompt_builder.py` — System Prompt Template

```python
SYSTEM_PROMPT = """
You are a facts-only FAQ assistant for Groww Mutual Fund schemes.

Rules you must follow strictly:
1. Answer ONLY using the context provided. Do not add any outside knowledge.
2. Keep your answer to a maximum of 3 sentences.
3. Do NOT give investment advice, opinions, or recommendations.
4. Do NOT compare funds or predict future returns.
5. If the answer is not found in the context, say:
   "I could not find this information in the available data. 
    Please visit [source_url] for the latest details."
6. Do not use phrases like "I think", "you should", or "it is better".
"""

def build_prompt(query: str, chunks: list[dict]) -> str:
    context_block = "\n\n".join(
        [f"[Source: {c['scheme_name']}]\n{c['text']}" for c in chunks]
    )
    return f"{SYSTEM_PROMPT}\n\nCONTEXT:\n{context_block}\n\nUSER QUESTION:\n{query}\n\nANSWER:"
```

### 6.2 `llm_client.py` — LLM API Wrapper

```
Uses Groq API with llama3-8b-8192:
  - Provider : Groq (https://console.groq.com)
  - Model    : llama3-8b-8192  (default)
  - Fallback : llama3-70b-8192 for complex queries

Config:
  temperature = 0.0   (deterministic, factual output)
  max_tokens  = 200   (enforces brevity)

def generate(prompt: str) -> str:
    client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.0,
        max_tokens=200
    )
    return response.choices[0].message.content
```

### 6.3 Validation

- Test with a factual query about expense ratio → LLM returns a grounded, ≤3 sentence answer
- Verify the LLM does NOT hallucinate facts not in the retrieved chunks
- Confirm response contains no opinion language

**Exit Criteria**: LLM returns factual, concise answers grounded in retrieved context.

---

## Phase 7 — Refusal & Safety Handler

**Goal**: Handle advisory, comparative, PII, and out-of-scope queries with compliant refusals.

**Files to create**:
- `src/refusal/refusal_handler.py`

### 7.1 Refusal Templates

```python
REFUSAL_TEMPLATES = {
    "ADVISORY": """
        I can only answer factual questions about Groww mutual fund schemes,
        such as expense ratios, exit loads, minimum SIP amounts, or benchmark indices.
        For investment guidance, please consult a SEBI-registered investment advisor.
        Learn more: https://www.amfiindia.com/investor-corner/knowledge-center
    """,

    "COMPARATIVE": """
        I'm unable to compare fund performance or recommend one fund over another.
        I can share factual details (like expense ratios or benchmarks) for each scheme individually.
        For scheme-wise data, please visit the official Groww scheme pages.
    """,

    "PII_DETECTED": """
        I noticed your message may contain sensitive personal information (such as a PAN,
        Aadhaar, or account number). For your security, please do not share this information here.
        This assistant does not collect or store any personal data.
    """,

    "OUT_OF_SCOPE": """
        This assistant only answers factual questions about Groww mutual fund schemes.
        Your question appears to be outside this scope.
        For mutual fund education, visit: https://www.amfiindia.com/investor-corner
    """
}

def get_refusal(intent: Intent) -> str:
    return REFUSAL_TEMPLATES.get(intent.value, REFUSAL_TEMPLATES["OUT_OF_SCOPE"])
```

### 7.2 Validation

- Test all 4 refusal types → confirm correct template is returned
- Confirm PII-containing queries never reach the retriever or LLM
- Verify refusal messages are polite and include a relevant educational link

**Exit Criteria**: All non-factual query types produce appropriate, compliant refusal responses.

---

## Phase 8 — Response Formatter

**Goal**: Wrap every response (factual or refusal) in a standardized envelope with citation and footer.

**Files to create**:
- `src/generation/response_formatter.py`

### 8.1 Response Envelope Structure

```python
@dataclass
class FormattedResponse:
    answer: str           # The factual answer text (or refusal message)
    citation_label: str   # e.g., "Groww Gold ETF FoF – Scheme Page"
    citation_url: str     # e.g., "https://groww.in/mutual-funds/..."
    last_updated: str     # e.g., "2026-06-30"
    disclaimer: str       # Always: "Facts-only. No investment advice."
    is_refusal: bool      # True if this is a refusal response
```

### 8.2 Formatter Logic

```
For factual responses:
  - answer       = LLM-generated text
  - citation_url = source_url of the top-ranked retrieved chunk
  - citation_label = scheme_name + " – Groww Scheme Page"
  - last_updated = last_fetched date from chunk metadata
  - is_refusal   = False

For refusal responses:
  - answer       = refusal template text
  - citation_url = AMFI / SEBI educational link
  - citation_label = "AMFI Investor Education"
  - last_updated = current date
  - is_refusal   = True
```

### 8.3 Rendered Output Example

```
┌─────────────────────────────────────────────────────────────┐
│  The expense ratio of Groww Gold ETF FoF (Direct) is        │
│  0.10% per annum as of the latest available data.           │
│                                                             │
│  📎 Source: Groww Gold ETF FoF – Groww Scheme Page          │
│     https://groww.in/mutual-funds/groww-gold-etf-fof-...    │
│                                                             │
│  🕒 Last updated from sources: 2026-06-30                   │
│  ⚠ Facts-only. No investment advice.                        │
└─────────────────────────────────────────────────────────────┘
```

**Exit Criteria**: Every response object has all 5 fields populated correctly.

---

## Phase 9 — User Interface (Streamlit)

**Goal**: Build the minimal, compliant chatbot UI described in `Architecture.md § 3.9`.

**Files to create**:
- `src/ui/app.py`

### 9.1 UI Layout

```
+----------------------------------------------------------+
|  HEADER                                                  |
|  "Groww Mutual Fund FAQ Assistant"                       |
|  Subtitle: "Powered by official Groww scheme data only"  |
|  ⚠ Banner: "Facts-only. No investment advice."          |
+----------------------------------------------------------+
|  WELCOME MESSAGE                                         |
|  "Ask me anything factual about Groww mutual fund        |
|   schemes. I answer from official Groww pages only."     |
+----------------------------------------------------------+
|  EXAMPLE QUESTION CHIPS (clickable buttons)              |
|  [What is the expense ratio of Groww Value Fund?]        |
|  [What is the exit load on Groww Smallcap 250?]          |
|  [What benchmark does Groww Gold ETF FoF track?]         |
+----------------------------------------------------------+
|  CHAT HISTORY (st.chat_message)                          |
|  (scrollable, user + assistant bubbles)                  |
+----------------------------------------------------------+
|  INPUT: st.chat_input("Ask a factual question...")       |
+----------------------------------------------------------+
|  SIDEBAR                                                 |
|  - About this tool                                       |
|  - Covered schemes list (7 links)                        |
|  - Disclaimer                                            |
+----------------------------------------------------------+
```

### 9.2 App Flow (Streamlit)

```python
# Pseudocode for app.py

st.title("Groww Mutual Fund FAQ Assistant")
st.caption("Facts-only | Powered by official Groww scheme pages")
st.warning("⚠ This tool provides factual information only. It does not offer investment advice.")

# Example question chips
example_qs = [
    "What is the expense ratio of Groww Value Fund?",
    "What is the exit load on Groww Nifty Smallcap 250?",
    "What benchmark does Groww Gold ETF FoF track?"
]
for q in example_qs:
    if st.button(q):
        user_input = q

# Chat input
user_input = st.chat_input("Ask a factual question about Groww mutual funds...")

if user_input:
    # 1. Classify intent
    intent = classify_intent(user_input)

    # 2. Route
    if intent == Intent.FACTUAL:
        chunks = retrieve(user_input, top_k=5)
        answer = generate(user_input, chunks)
        response = format_response(answer, chunks)
    else:
        response = format_refusal(intent)

    # 3. Render
    st.chat_message("user").write(user_input)
    with st.chat_message("assistant"):
        st.write(response.answer)
        st.caption(f"📎 {response.citation_label}")
        st.markdown(f"[{response.citation_url}]({response.citation_url})")
        st.caption(f"🕒 {response.last_updated}")
        st.info(response.disclaimer)
```

### 9.3 Validation

- App launches with `streamlit run src/ui/app.py`
- All 3 example chips trigger correct responses
- Disclaimer banner always visible
- UI renders correctly on desktop screen

**Exit Criteria**: Chatbot UI launches, accepts input, and renders formatted responses.

---

## Phase 10 — Integration & End-to-End Testing

**Goal**: Wire all phases together into a working pipeline and validate against acceptance criteria.

### 10.1 Integration Checklist

```
[ ] Phase 2 output (data/raw/) feeds Phase 3 (parser)
[ ] Phase 3 output (data/chunks/) feeds Phase 4 (embedder)
[ ] Phase 4 output (vector_store/) loads correctly in Phase 5 (retriever)
[ ] Phase 5 output (chunks) feeds Phase 6 (LLM generator)
[ ] Phase 6 output (answer) feeds Phase 8 (formatter)
[ ] Phase 7 (refusal) feeds Phase 8 (formatter) for non-factual queries
[ ] Phase 8 output (FormattedResponse) renders in Phase 9 (UI)
```

### 10.2 Test Cases

| # | Test Query | Expected Behaviour |
|---|---|---|
| 1 | "What is the expense ratio of Groww Value Fund?" | Factual answer + Groww URL citation |
| 2 | "What is the exit load on Groww Nifty Smallcap 250?" | Factual answer + Groww URL citation |
| 3 | "What benchmark does Groww Gold ETF FoF track?" | Factual answer + Groww URL citation |
| 4 | "What is the minimum SIP for Groww Nifty Defence ETF FoF?" | Factual answer + Groww URL citation |
| 5 | "Should I invest in Groww Value Fund?" | Polite refusal (ADVISORY) + AMFI link |
| 6 | "Which Groww fund is the best?" | Polite refusal (COMPARATIVE) + SEBI link |
| 7 | "My PAN is ABCDE1234F, help me invest" | Hard block (PII_DETECTED) + privacy notice |
| 8 | "What is the weather today?" | Out-of-scope refusal |
| 9 | "Tell me about a fund not in your corpus" | "Could not find information" + scheme URL |
| 10 | (Empty input) | Graceful handling, no crash |

### 10.3 Success Criteria Verification

| Criterion | Verified By |
|---|---|
| Accurate factual retrieval | Test cases 1–4 pass |
| Strict facts-only responses | LLM output reviewed for opinion language |
| Valid source citations | All responses include a working Groww URL |
| Proper advisory refusals | Test cases 5–8 pass |
| Clean, minimal UI | Manual review in browser |

### 10.4 Run Commands

```bash
# Step 1: Ingest data
python -m src.ingestion.fetcher

# Step 2: Process and chunk
python -m src.ingestion.parser
python -m src.ingestion.chunker

# Step 3: Build vector store
python -m src.ingestion.embedder

# Step 4: Launch chatbot
streamlit run src/ui/app.py
```

**Exit Criteria**: All 10 test cases produce expected output; chatbot is demo-ready.

---

## Dependency Map Between Phases

```
Phase 1 (Setup)
    └──► Phase 2 (Ingestion)
              └──► Phase 3 (Processing & Chunking)
                        └──► Phase 4 (Embedding & Vector Store)
                                  └──► Phase 5 (Retriever + Classifier)
                                            ├──► Phase 6 (LLM Generation)
                                            │         └──► Phase 8 (Formatter)
                                            └──► Phase 7 (Refusal Handler)
                                                          └──► Phase 8 (Formatter)
                                                                    └──► Phase 9 (UI)
                                                                              └──► Phase 10 (Testing)

Phase 11 (Scheduler) — runs independently on a daily cron:
    └──► Phase 2 (Fetcher)  →  Phase 3 (Parser + Chunker)  →  Phase 4 (Embedder)
              (Rebuilds the FAISS index; Phase 9 UI auto-reloads on next query)
```

---

## Phase 11 — Daily Data Refresh via GitHub Actions

**Goal**: Automatically trigger the full ingestion pipeline (Phases 2→3→4) on a daily GitHub Actions cron schedule so the FAISS vector index always reflects the latest Groww scheme data — with no local server or APScheduler process required.

**Files to create**:
- `.github/workflows/daily_refresh.yml` — GitHub Actions workflow definition
- `src/scheduler/pipeline_runner.py` — Python script that runs the full pipeline
- `src/scheduler/validate_phase11.py` — validation script
- `logs/` — directory (tracked via `.gitkeep`) to persist run logs

### 11.1 Architecture

```
GitHub Actions (hosted runner)
         │
         │  Cron trigger: 0 5 * * * (UTC) = 10:30 IST daily
         ▼
┌─────────────────────────────────────────────────┐
│          daily_refresh.yml Workflow              │
│                                                  │
│  1. actions/checkout@v4                          │
│  2. actions/setup-python@v5  (Python 3.11)       │
│  3. pip install -r requirements.txt              │
│  4. python -m src.scheduler.pipeline_runner      │
│       ├─ fetcher   (Phase 2)                     │
│       ├─ parser    (Phase 3.1)                   │
│       ├─ chunker   (Phase 3.2)                   │
│       └─ embedder  (Phase 4)                     │
│  5. Write logs/refresh_log.jsonl                 │
│  6. git commit & push refreshed index + logs     │
└─────────────────────────────────────────────────┘
         │
         ▼
  Updated vector_store/ committed to repo
  Phase 9 UI picks up fresh index on next startup
```

### 11.2 `pipeline_runner.py` — Logic

```python
"""
src/scheduler/pipeline_runner.py
=================================
Runs the full ingestion pipeline (Phases 2→3→4) end-to-end.
Called by the GitHub Actions workflow and can also be run manually.

Usage:
    python -m src.scheduler.pipeline_runner
"""

import json, logging, sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE     = PROJECT_ROOT / "logs" / "refresh_log.jsonl"

def run_pipeline():
    LOG_FILE.parent.mkdir(exist_ok=True)
    start = datetime.now(timezone.utc)
    record = {"run_at": start.isoformat(), "status": "running", "chunks": 0}
    try:
        from src.ingestion.fetcher  import fetch_all
        from src.ingestion.parser   import parse_all
        from src.ingestion.chunker  import chunk_all
        from src.ingestion.embedder import embed_all

        fetch_all()
        parse_all()
        chunks = chunk_all()
        embed_all()

        record["status"] = "success"
        record["chunks"] = len(chunks)
    except Exception as exc:
        record["status"] = "error"
        record["error"]  = str(exc)
        logging.exception("Pipeline failed")
    finally:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    return record["status"] == "success"

if __name__ == "__main__":
    sys.exit(0 if run_pipeline() else 1)
```

### 11.3 `.github/workflows/daily_refresh.yml` — Workflow

```yaml
name: Daily Data Refresh

on:
  schedule:
    - cron: "0 5 * * *"   # 05:00 UTC = 10:30 IST
  workflow_dispatch:          # Allow manual trigger from GitHub UI

permissions:
  contents: write             # Needed to commit refreshed index back

jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run ingestion pipeline
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: python -m src.scheduler.pipeline_runner

      - name: Commit refreshed index and logs
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add vector_store/ data/ logs/
          git diff --cached --quiet || git commit -m "chore: daily FAISS index refresh [skip ci]"
          git push
```

> **Note**: `[skip ci]` in the commit message prevents an infinite loop of re-triggering the workflow.

### 11.4 Key Implementation Details

| Detail | Value |
|---|---|
| Trigger | GitHub Actions cron `0 5 * * *` (10:30 IST) |
| Manual trigger | "Run workflow" button on GitHub Actions tab |
| Runner | `ubuntu-latest` (GitHub-hosted, free tier) |
| Secrets needed | `GROQ_API_KEY` stored in repo Settings → Secrets |
| Artifacts committed | `vector_store/`, `data/processed/`, `data/chunks/`, `logs/` |
| Run log | `logs/refresh_log.jsonl` — one JSON line per run, committed to repo |
| Error handling | Pipeline exits with code 1 on failure; GitHub marks the job as failed and sends email alert |
| No server needed | Zero infrastructure — GitHub hosts the cron runner for free |
| UI integration | `app.py` calls `_cache.clear()` on startup so it always loads the latest committed index |

### 11.5 `requirements.txt` changes

No new dependencies needed — APScheduler is **not** required. GitHub Actions handles scheduling natively.

### 11.6 Repository secrets to configure

Navigate to `Settings → Secrets and variables → Actions` in the GitHub repo and add:

| Secret Name | Value |
|---|---|
| `GROQ_API_KEY` | Your Groq API key from console.groq.com |

### 11.7 Validation (`validate_phase11.py`)

```
1. Verify pipeline_runner.py can be imported without errors
2. Run pipeline_runner.run_pipeline() manually (dry run)
3. Verify logs/refresh_log.jsonl was created with status="success"
4. Verify vector_store/faiss_index/ mtime was updated after the run
5. Verify the workflow YAML is syntactically valid (yamllint)
6. Print PASS / FAIL
```

**Exit Criteria**: `pipeline_runner.run_pipeline()` completes successfully; `logs/refresh_log.jsonl` contains a `"status": "success"` record; the GitHub Actions workflow YAML passes lint; the job appears under the "Actions" tab and runs successfully on the next cron tick.


---

## Estimated Effort

| Phase | Effort | Notes |
|---|---|---|
| Phase 1 — Setup | 0.5 day | One-time, mostly file creation |
| Phase 2 — Ingestion | 0.5 day | Simple HTTP + file I/O |
| Phase 3 — Processing | 1 day | HTML parsing can be tricky for dynamic pages |
| Phase 4 — Embedding | 0.5 day | Straightforward with sentence-transformers + FAISS |
| Phase 5 — Query Engine | 1 day | Intent classification needs careful tuning |
| Phase 6 — LLM Generation | 1 day | Prompt engineering iteration |
| Phase 7 — Refusal Handler | 0.5 day | Template-based, low complexity |
| Phase 8 — Formatter | 0.5 day | Dataclass + render logic |
| Phase 9 — Streamlit UI | 1 day | Layout + chat UX |
| Phase 10 — Testing | 1 day | Integration + edge case validation |
| Phase 11 — Scheduler | 0.5 day | GitHub Actions workflow + pipeline runner + run log |
| **Total** | **~8 days** | Solo developer estimate |

---

> **Note**: Phases 2–4 (offline pipeline) are run once to build the index. Only Phases 5–9 run at inference time per user query.
>
> **Phase 11** is powered by a GitHub Actions cron workflow (`.github/workflows/daily_refresh.yml`). It re-executes Phases 2–4 nightly on a free GitHub-hosted runner, commits the refreshed FAISS index back to the repo, and requires **no local server or APScheduler process**.
