# Architecture: Mutual Fund FAQ RAG Chatbot

> **AMC**: Groww Mutual Fund | **Approach**: Retrieval-Augmented Generation (RAG)
> **Principle**: Facts-only. No investment advice.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture Diagram](#2-high-level-architecture-diagram)
3. [Component Breakdown](#3-component-breakdown)
   - 3.1 [Data Ingestion Pipeline](#31-data-ingestion-pipeline)
   - 3.2 [Document Processing & Chunking](#32-document-processing--chunking)
   - 3.3 [Embedding & Vector Store](#33-embedding--vector-store)
   - 3.4 [Query Understanding & Intent Classification](#34-query-understanding--intent-classification)
   - 3.5 [Retriever](#35-retriever)
   - 3.6 [LLM Response Generator](#36-llm-response-generator)
   - 3.7 [Response Formatter](#37-response-formatter)
   - 3.8 [Refusal Handler](#38-refusal-handler)
   - 3.9 [User Interface Layer](#39-user-interface-layer)
4. [Data Flow: End-to-End](#4-data-flow-end-to-end)
5. [Corpus Design](#5-corpus-design)
6. [Technology Stack](#6-technology-stack)
7. [Directory Structure](#7-directory-structure)
8. [Security & Compliance Architecture](#8-security--compliance-architecture)
9. [Scalability & Extension Points](#9-scalability--extension-points)
10. [Known Limitations](#10-known-limitations)

---

## 1. System Overview

The system is a **lightweight, offline-first RAG pipeline** that retrieves factual information from a pre-built vector store of official Groww mutual fund documents and generates short, cited responses using an LLM.

```
┌─────────────────────────────────────────────────────┐
│                OFFLINE (Build Time)                 │
│  Crawl URLs → Parse Docs → Chunk → Embed → Store   │
└─────────────────────────────────────────────────────┘
                          │
                    Vector Store
                          │
┌─────────────────────────────────────────────────────┐
│                 ONLINE (Runtime)                    │
│  User Query → Classify → Retrieve → Generate       │
└─────────────────────────────────────────────────────┘
```

The pipeline has **two phases**:

| Phase | When | Description |
|---|---|---|
| **Ingestion** | Build time / offline | Crawl, parse, chunk, embed, and store official documents |
| **Inference** | Runtime / online | Classify query, retrieve relevant chunks, generate response |

---

## 2. High-Level Architecture Diagram

```
+==============================================================+
|                     USER INTERFACE                           |
|   Welcome Message | Example Questions | Disclaimer Banner    |
+==============================================================+
                            |
                     [User Query]
                            |
                            v
+--------------------------------------------------------------+
|              QUERY UNDERSTANDING LAYER                       |
|                                                              |
|   +-----------------------+   +---------------------------+  |
|   |  Intent Classifier    |   |  Query Preprocessor       |  |
|   |  (Factual / Advisory) |   |  (normalize, clean text)  |  |
|   +-----------------------+   +---------------------------+  |
+--------------------------------------------------------------+
         |                              |
   [Advisory Query]             [Factual Query]
         |                              |
         v                              v
+----------------+         +---------------------------+
|  REFUSAL       |         |        RETRIEVER          |
|  HANDLER       |         |                           |
|                |         |  Semantic Search over     |
|  Polite msg    |         |  Vector Store (Top-K      |
|  + AMFI/SEBI   |         |  most relevant chunks)    |
|  edu link      |         +---------------------------+
+----------------+                     |
                               [Retrieved Chunks
                               + Source Metadata]
                                        |
                                        v
                          +---------------------------+
                          |    LLM RESPONSE           |
                          |    GENERATOR              |
                          |                           |
                          |  Prompt = System prompt   |
                          |  + retrieved context      |
                          |  + user query             |
                          |                           |
                          |  Output: max 3 sentences  |
                          +---------------------------+
                                        |
                                        v
                          +---------------------------+
                          |    RESPONSE FORMATTER     |
                          |                           |
                          |  - Factual answer text    |
                          |  - One citation URL       |
                          |  - Last updated footer    |
                          +---------------------------+
                                        |
                                        v
                          +==========================+
                          |     USER INTERFACE       |
                          |     (Chat Response)      |
                          +==========================+

- - - - - - - - - - - - - - - - - - - - - - - - - - -
                    OFFLINE PIPELINE
- - - - - - - - - - - - - - - - - - - - - - - - - - -

+----------------------------------------------------------+
|                  DATA INGESTION PIPELINE                 |
|                                                          |
|  [Official URLs]                                         |
|       |                                                  |
|       v                                                  |
|  [Web Scraper / PDF Downloader]                          |
|       |                                                  |
|       v                                                  |
|  [Document Parser]  (HTML → text, PDF → text)           |
|       |                                                  |
|       v                                                  |
|  [Text Chunker]  (fixed-size + overlap)                  |
|       |                                                  |
|       v                                                  |
|  [Embedding Model]  (e.g., sentence-transformers)        |
|       |                                                  |
|       v                                                  |
|  [Vector Store]  (e.g., FAISS / ChromaDB)               |
|  + Metadata: {source_url, scheme_name, doc_type, date}  |
+----------------------------------------------------------+
```

---

## 3. Component Breakdown

### 3.1 Data Ingestion Pipeline

Responsible for collecting all source documents from official public URLs.

**Input**: 7 official Groww scheme page URLs

**Steps**:
1. **URL Fetcher** — HTTP GET requests with retry logic; respects `robots.txt`
2. **HTML Content Extractor** — Extracts the main scheme page content from each URL

**Source URLs (Fixed Corpus)**:

| # | Scheme | URL |
|---|---|---|
| 1 | Groww Gold ETF FoF – Direct Growth | https://groww.in/mutual-funds/groww-gold-etf-fof-direct-growth |
| 2 | Groww Nifty India Defence ETF FoF – Direct Growth | https://groww.in/mutual-funds/groww-nifty-india-defence-etf-fof-direct-growth |
| 3 | Groww Nifty Total Market Index Fund – Direct Growth | https://groww.in/mutual-funds/groww-nifty-total-market-index-fund-direct-growth |
| 4 | Groww Nifty EV & New Age Automotive ETF FoF – Direct Growth | https://groww.in/mutual-funds/groww-nifty-ev-new-age-automotive-etf-fof-direct-growth |
| 5 | Groww Nifty Smallcap 250 Index Fund – Direct Growth | https://groww.in/mutual-funds/groww-nifty-smallcap-250-index-fund-direct-growth |
| 6 | Groww Value Fund – Direct Growth | https://groww.in/mutual-funds/groww-value-fund-direct-growth |
| 7 | Groww Nifty Non-Cyclical Consumer Index Fund – Direct Growth | https://groww.in/mutual-funds/groww-nifty-non-cyclical-consumer-index-fund-direct-growth |

**Output**: Raw HTML text with source URL metadata attached

---

### 3.2 Document Processing & Chunking

Converts raw Groww scheme page HTML into clean, retrievable text chunks.

**Steps**:
1. **HTML Parser** — Strips nav bars, ads, footers, and cookie banners; extracts main scheme content using CSS selectors
2. **Text Cleaner** — Removes boilerplate, normalizes whitespace, and strips non-factual content
3. **Chunker** — Splits text into overlapping chunks

**Chunking Strategy**:

```
Chunk Size     : 400–500 tokens
Overlap        : 50–75 tokens
Strategy       : Recursive character splitting
                 (split on paragraphs → sentences → words)
```

**Metadata per Chunk**:

```json
{
  "chunk_id": "groww_gold_etf_fof_chunk_003",
  "source_url": "https://groww.in/mutual-funds/groww-gold-etf-fof-direct-growth",
  "scheme_name": "Groww Gold ETF FoF - Direct Growth",
  "doc_type": "groww_scheme_page",
  "last_fetched": "2026-06-30",
  "text": "The expense ratio of Groww Gold ETF FoF Direct Plan is 0.10% per annum..."
}
```

**Output**: List of `(chunk_text, metadata)` pairs ready for embedding

---

### 3.3 Embedding & Vector Store

Converts text chunks into dense vector representations and stores them for semantic retrieval.

**Embedding Model**:

| Option | Model | Dimensions | Notes |
|---|---|---|---|
| **Selected** | `BAAI/bge-base-en-v1.5` | 768 | Strong retrieval quality, free, runs locally |
| Alternative | `BAAI/bge-small-en-v1.5` | 384 | Lighter version, faster but slightly lower accuracy |

**Vector Store Options**:

| Store | Type | When to Use |
|---|---|---|
| **FAISS** | In-memory / local file | Recommended for offline/local deployments |
| **ChromaDB** | Embedded persistent DB | Easy metadata filtering, good for prototyping |
| **Pinecone** | Managed cloud | If scaling to production with large corpus |

**Index Structure**:

```
Vector Store
├── Index (FAISS / ChromaDB)
│   └── [vector, chunk_id]  ×  N chunks
└── Metadata Store (JSON / SQLite)
    └── chunk_id → {source_url, scheme_name, doc_type, last_fetched, text}
```

**Output**: A persistent vector index + metadata store, queryable at inference time.

---

### 3.4 Query Understanding & Intent Classification

Classifies each incoming user query before routing it to the retriever or refusal handler.

**Intent Categories**:

| Intent | Description | Example |
|---|---|---|
| `FACTUAL` | Asks for verifiable fund facts | "What is the expense ratio of Groww Value Fund?" |
| `ADVISORY` | Seeks opinions or recommendations | "Should I invest in Groww Smallcap fund?" |
| `COMPARATIVE` | Compares funds or returns | "Which fund has better returns?" |
| `OUT_OF_SCOPE` | Unrelated to mutual funds | "What is the weather today?" |

**Classification Approach**:

```
Option A (Rule-based): Keyword matching
  - Advisory keywords: "should I", "better", "recommend", "which is best"
  - Blocked PII patterns: regex for PAN, Aadhaar, OTP

Option B (LLM-based): Zero-shot classification prompt
  - Prompt: "Classify the following query as FACTUAL, ADVISORY,
             COMPARATIVE, or OUT_OF_SCOPE. Reply with one word only."
  - More accurate, handles edge cases well
```

> **Recommended**: Combine both — rule-based as a fast pre-filter, LLM for ambiguous cases.

**Output**: `{ "intent": "FACTUAL" | "ADVISORY" | "COMPARATIVE" | "OUT_OF_SCOPE" }`

---

### 3.5 Retriever

Performs semantic search over the vector store to find the most relevant document chunks for a factual query.

**Process**:
1. Embed the user query using the same embedding model as ingestion
2. Perform ANN (Approximate Nearest Neighbor) search over the vector index
3. Return top-K chunks (K = 3–5) ranked by cosine similarity
4. Apply optional metadata filter (e.g., filter to a specific scheme if mentioned)

**Metadata Filtering Examples**:

```python
# If user asks about "Groww Gold ETF FoF", filter results to that scheme
filter = {"scheme_name": "Groww Gold ETF FoF - Direct Growth"}

# All chunks share the same doc_type since we only use Groww scheme pages
filter = {"doc_type": "groww_scheme_page"}
```

**Retrieval Parameters**:

| Parameter | Value | Notes |
|---|---|---|
| Top-K | 3–5 | More chunks = richer context but slower |
| Similarity Threshold | 0.65+ | Discard low-relevance chunks |
| Reranking | Optional (cross-encoder) | Improves precision at slight latency cost |

**Output**: Top-K `(chunk_text, metadata)` pairs with similarity scores

---

### 3.6 LLM Response Generator

Uses the retrieved chunks as grounding context and generates a concise, factual answer.

**Prompt Template**:

```
SYSTEM:
You are a facts-only mutual fund FAQ assistant for Groww Mutual Fund schemes.
Answer ONLY from the context provided below. Do NOT provide investment advice,
opinions, or recommendations. Do NOT compare funds or predict returns.
Keep your answer to a maximum of 3 sentences.
If the answer is not found in the context, say: "I could not find this
information in the official documents. Please visit [source_url]."

CONTEXT:
{retrieved_chunk_1}
{retrieved_chunk_2}
{retrieved_chunk_3}

SOURCE URL: {primary_source_url}
LAST UPDATED: {last_fetched_date}

USER QUERY:
{user_query}

ASSISTANT:
```

**LLM Options**:

| Model | Provider | Notes |
|---|---|---|
| `llama3-8b-8192` | **Groq** | Fast inference, free tier available, strong factual grounding |
| `llama3-70b-8192` | **Groq** | Higher quality, still on Groq infrastructure |
| `mixtral-8x7b-32768` | **Groq** | Larger context window, good for multi-chunk prompts |

**Output Constraints enforced in prompt**:
- Max 3 sentences
- No opinion language ("I think", "you should", "better option")
- No return calculations or future projections

---

### 3.7 Response Formatter

Packages the LLM output into a standardized response envelope.

**Response Structure**:

```json
{
  "answer": "The expense ratio of Groww Gold ETF FoF Direct Plan is 0.10% per annum as of the latest factsheet.",
  "citation": {
    "label": "Source: Groww Gold ETF FoF – Scheme Page",
    "url": "https://groww.in/mutual-funds/groww-gold-etf-fof-direct-growth"
  },
  "footer": "Last updated from sources: 2026-06-30",
  "disclaimer": "Facts-only. No investment advice."
}
```

**UI Rendering**:
```
┌─────────────────────────────────────────────────────────────┐
│  The expense ratio of Groww Gold ETF FoF Direct Plan is     │
│  0.10% per annum as of the latest factsheet.                │
│                                                             │
│  Source: Groww Gold ETF FoF – Scheme Page                   │
│  https://groww.in/mutual-funds/groww-gold-etf-fof-...       │
│                                                             │
│  Last updated from sources: 2026-06-30                      │
│  ⚠ Facts-only. No investment advice.                        │
└─────────────────────────────────────────────────────────────┘
```

---

### 3.8 Refusal Handler

Intercepts advisory, comparative, or out-of-scope queries and returns a polite, compliant refusal.

**Refusal Response Template**:

```
I'm only able to answer factual questions about Groww mutual fund schemes —
such as expense ratios, exit loads, minimum SIP amounts, or benchmark indices.

For investment guidance, please consult a SEBI-registered investment advisor.
Learn more: https://www.amfiindia.com/investor-corner/knowledge-center

Facts-only. No investment advice.
```

**Trigger Conditions**:

| Condition | Example Query | Action |
|---|---|---|
| Advisory intent | "Should I invest in Groww Smallcap?" | Standard refusal + AMFI link |
| Comparative intent | "Which Groww fund is best?" | Standard refusal + SEBI link |
| PII detected | Query contains PAN / Aadhaar pattern | Hard block + privacy notice |
| Out of scope | "What is the Sensex today?" | Scope refusal + redirect |

---

### 3.9 User Interface Layer

A clean, minimal chat interface that surfaces the FAQ assistant.

**UI Components**:

```
+----------------------------------------------------------+
|  HEADER                                                  |
|  "Groww Mutual Fund FAQ Assistant"                       |
|  ⚠ Facts-only. No investment advice.                    |
+----------------------------------------------------------+
|  WELCOME MESSAGE                                         |
|  "Ask me anything factual about Groww mutual fund        |
|   schemes. I answer from official sources only."         |
+----------------------------------------------------------+
|  EXAMPLE QUESTIONS (clickable chips)                     |
|  [What is the expense ratio of Groww Value Fund?]        |
|  [What is the exit load on Groww Smallcap 250?]          |
|  [What is the lock-in period for Groww ELSS?]            |
+----------------------------------------------------------+
|  CHAT WINDOW                                             |
|  (scrollable message history)                            |
+----------------------------------------------------------+
|  INPUT BAR                                               |
|  [ Type your question here... ]          [Send ▶]        |
+----------------------------------------------------------+
|  FOOTER DISCLAIMER                                       |
|  "Facts-only. No investment advice. Sources: AMC,        |
|   AMFI, SEBI only."                                      |
+----------------------------------------------------------+
```

**Technology**: Python (Streamlit) or HTML/CSS/JS (vanilla) — minimal, no frameworks required.

---

## 4. Data Flow: End-to-End

### Offline (Ingestion) Flow

```
Step 1: 7 Groww Scheme Page URLs (fixed corpus)
         |
Step 2: Fetch → Raw HTML per scheme page
         |
Step 3: Parse → Extract & clean main content from HTML
         |
Step 4: Chunk → (text_chunk, metadata) pairs
         |
Step 5: Embed → Dense vectors per chunk
         |
Step 6: Index → Store in FAISS/ChromaDB + metadata JSON
         |
Step 7: Persist → Save index to disk (vector_store/)
```

### Online (Inference) Flow

```
Step 1: User types query in UI
         |
Step 2: Preprocess query (strip PII, normalize)
         |
Step 3: Intent Classification
         |
         +-- ADVISORY / COMPARATIVE → Refusal Handler → Response
         |
Step 4: Embed query using same embedding model
         |
Step 5: Vector similarity search → Top-K chunks + metadata
         |
Step 6: Build prompt = system_prompt + chunks + query
         |
Step 7: LLM generates ≤3 sentence factual answer
         |
Step 8: Response Formatter → answer + citation + footer
         |
Step 9: Render in UI chat window
```

---

## 5. Corpus Design

### Source Scope

> **Only the 7 official Groww scheme pages listed below are used as the data source. No PDFs, no AMFI pages, no SEBI pages, and no external help centers.**

### Corpus URLs

| # | Scheme Name | Category | Source URL |
|---|---|---|---|
| 1 | Groww Gold ETF FoF – Direct Growth | Gold / FoF | https://groww.in/mutual-funds/groww-gold-etf-fof-direct-growth |
| 2 | Groww Nifty India Defence ETF FoF – Direct Growth | Sectoral / Defence | https://groww.in/mutual-funds/groww-nifty-india-defence-etf-fof-direct-growth |
| 3 | Groww Nifty Total Market Index Fund – Direct Growth | Index / Broad Market | https://groww.in/mutual-funds/groww-nifty-total-market-index-fund-direct-growth |
| 4 | Groww Nifty EV & New Age Automotive ETF FoF – Direct Growth | Sectoral / EV & Auto | https://groww.in/mutual-funds/groww-nifty-ev-new-age-automotive-etf-fof-direct-growth |
| 5 | Groww Nifty Smallcap 250 Index Fund – Direct Growth | Index / Small Cap | https://groww.in/mutual-funds/groww-nifty-smallcap-250-index-fund-direct-growth |
| 6 | Groww Value Fund – Direct Growth | Value / Active Equity | https://groww.in/mutual-funds/groww-value-fund-direct-growth |
| 7 | Groww Nifty Non-Cyclical Consumer Index Fund – Direct Growth | Index / Consumer | https://groww.in/mutual-funds/groww-nifty-non-cyclical-consumer-index-fund-direct-growth |

---

## 6. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.10+ | Ecosystem maturity for RAG/NLP |
| **Web Scraping** | `requests` + `BeautifulSoup4` | Lightweight HTML parsing of Groww scheme pages |
| **Text Chunking** | `LangChain` `RecursiveCharacterTextSplitter` | Flexible, battle-tested chunking |
| **Embeddings** | `sentence-transformers` (`BAAI/bge-base-en-v1.5`) | BGE model — strong retrieval quality, runs locally |
| **Vector Store** | `FAISS` (local) or `ChromaDB` | Lightweight, no server required |
| **LLM** | Groq API (`llama3-8b-8192`) | Ultra-fast inference, free tier, no GPU required |
| **LLM Orchestration** | `LangChain` or direct API calls | Chain prompt + retrieval + LLM |
| **UI** | `Streamlit` | Rapid prototyping, Python-native |
| **Config** | `python-dotenv` | API key management via `.env` |
| **Logging** | Python `logging` module | Trace queries, errors, refusals |

---

## 7. Directory Structure

```
RAGChatbot/
├── Docs/
│   ├── context.md               # Project context
│   └── Architecture.md          # This document
│
├── data/
│   ├── raw/                     # Downloaded HTML / PDFs
│   ├── processed/               # Cleaned text files per document
│   └── chunks/                  # Chunked text with metadata (JSONL)
│
├── vector_store/
│   ├── faiss_index/             # FAISS index files
│   └── metadata.json            # chunk_id → metadata mapping
│
├── src/
│   ├── ingestion/
│   │   ├── fetcher.py           # URL fetcher + PDF downloader
│   │   ├── parser.py            # HTML & PDF parser
│   │   ├── chunker.py           # Text chunking logic
│   │   └── embedder.py          # Embedding + vector store builder
│   │
│   ├── retrieval/
│   │   ├── retriever.py         # Semantic search over vector store
│   │   └── intent_classifier.py # Query intent classification
│   │
│   ├── generation/
│   │   ├── prompt_builder.py    # Prompt template construction
│   │   ├── llm_client.py        # LLM API wrapper
│   │   └── response_formatter.py# Format answer + citation + footer
│   │
│   ├── refusal/
│   │   └── refusal_handler.py   # Polite refusal responses
│   │
│   └── ui/
│       └── app.py               # Streamlit UI entrypoint
│
├── config/
│   └── urls.yaml                # All source URLs (15-25 entries)
│
├── .env                         # API keys (never committed to git)
├── requirements.txt
└── README.md
```

---

## 8. Security & Compliance Architecture

### PII Protection

```
Query Input
    |
    v
[PII Regex Scanner]
    |
    +-- PAN pattern detected?    → Hard block, return privacy notice
    +-- Aadhaar pattern?         → Hard block, return privacy notice
    +-- OTP / Account number?    → Hard block, return privacy notice
    |
    v
[Safe to proceed]
```

**PII Patterns Blocked**:
- PAN: `[A-Z]{5}[0-9]{4}[A-Z]{1}`
- Aadhaar: 12-digit numeric sequence
- Account numbers: 9–18 digit sequences
- Email: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`

### Data Handling Rules

| Rule | Implementation |
|---|---|
| No PII storage | Queries are not logged with any user identifier |
| No session persistence | Chat history lives only in-browser session memory |
| Source-only corpus | Ingestion pipeline rejects non-official domains |
| No return projections | LLM system prompt explicitly prohibits calculations |
| Refusal logging | Refusal events logged (without PII) for quality monitoring |

---

## 9. Scalability & Extension Points

| Feature | Current | Future Extension |
|---|---|---|
| AMC Coverage | Groww only | Add other AMCs (HDFC, SBI, etc.) |
| Scheme Count | 7 schemes | Expand to full AMC catalogue |
| Corpus Refresh | Manual re-ingestion | Scheduled crawler (weekly cron) |
| Vector Store | FAISS (local) | Migrate to Pinecone / Weaviate for scale |
| LLM | API-based | Fine-tune or switch to local Mistral |
| UI | Streamlit | Embed as widget in Groww Help Center |
| Language | English only | Add Hindi support via multilingual embeddings |

---

## 10. Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Static corpus | Answers may be stale if factsheets change | Add weekly re-ingestion schedule |
| PDF table parsing | Complex tables (e.g., load slabs) may parse incorrectly | Manual review of high-value PDFs |
| Embedding quality | Semantic mismatch on domain-specific jargon | Use finance-tuned embeddings or add synonyms |
| LLM hallucination | LLM may add facts not in retrieved context | Use low temperature (0.0–0.1) + strict prompt |
| No real-time NAV | NAV data is point-in-time from last crawl | Disclaim NAV figures; link to AMFI NAV page |
| Single AMC scope | Cannot answer cross-AMC comparison queries | Intentional — refusal handler covers this |
| No authentication | No user login or personalization | By design — privacy-first, no PII handling |

---

> **Disclaimer**: This system is designed for factual information retrieval only. It does not provide investment advice, financial recommendations, or performance projections. All responses are sourced exclusively from official AMC, AMFI, and SEBI documents.
