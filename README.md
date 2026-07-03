# Groww Mutual Fund FAQ RAG Chatbot

🚀 **Live App:** [https://groww-mf-assistant.streamlit.app/](https://groww-mf-assistant.streamlit.app/)

A **facts-only FAQ assistant** for Groww mutual fund schemes, built using
Retrieval-Augmented Generation (RAG).

## Stack
- **Embeddings**: `BAAI/bge-base-en-v1.5` (sentence-transformers)
- **Vector Store**: FAISS (local)
- **LLM**: Groq (`llama3-8b-8192`)
- **UI**: Streamlit
- **Corpus**: 7 official Groww scheme pages (HTML only)

## Disclaimer
> Facts-only. No investment advice.

---

## Setup

### 1. Clone the repository and navigate into it

```bash
cd RAGChatbot
```

### 2. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS / Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
copy .env.example .env     # Windows
# cp .env.example .env     # macOS / Linux
```

Edit `.env` and add your [Groq API key](https://console.groq.com):

```
GROQ_API_KEY=your_groq_api_key_here
```

### 5. Run the ingestion pipeline (build the vector store)

```bash
python -m src.ingestion.fetcher
python -m src.ingestion.parser
python -m src.ingestion.chunker
python -m src.ingestion.embedder
```

### 6. Launch the chatbot

```bash
streamlit run src/ui/app.py
```

---

## Selected AMC & Schemes

**AMC**: Groww Mutual Fund (Groww Asset Management Ltd.)

| # | Scheme | Category |
|---|---|---|
| 1 | Groww Gold ETF FoF – Direct Growth | Gold / FoF |
| 2 | Groww Nifty India Defence ETF FoF – Direct Growth | Sectoral / Defence |
| 3 | Groww Nifty Total Market Index Fund – Direct Growth | Index / Broad Market |
| 4 | Groww Nifty EV & New Age Automotive ETF FoF – Direct Growth | Sectoral / EV & Auto |
| 5 | Groww Nifty Smallcap 250 Index Fund – Direct Growth | Index / Small Cap |
| 6 | Groww Value Fund – Direct Growth | Value / Active Equity |
| 7 | Groww Nifty Non-Cyclical Consumer Index Fund – Direct Growth | Index / Consumer |

---

## Architecture Overview

```
User Query
    |
    v
Intent Classifier (FACTUAL / ADVISORY / COMPARATIVE / PII / OUT_OF_SCOPE)
    |
    +-- Non-FACTUAL --> Refusal Handler --> Formatted Response
    |
    +-- FACTUAL --> BGE Embedder --> FAISS Retriever (Top-K chunks)
                                            |
                                            v
                                  Groq LLM (llama3-8b-8192)
                                            |
                                            v
                              Response Formatter (answer + citation + footer)
                                            |
                                            v
                                    Streamlit UI
```

---

## Project Structure

```
RAGChatbot/
├── Docs/                   # Project documentation
├── config/
│   └── urls.yaml           # 7 Groww scheme URLs
├── data/
│   ├── raw/                # Fetched HTML files
│   ├── processed/          # Cleaned text files
│   └── chunks/             # Chunked JSONL data
├── vector_store/
│   └── faiss_index/        # FAISS index + metadata
├── src/
│   ├── ingestion/          # Fetcher, parser, chunker, embedder
│   ├── retrieval/          # Intent classifier + retriever
│   ├── generation/         # Prompt builder + LLM client + formatter
│   ├── refusal/            # Refusal handler
│   └── ui/                 # Streamlit app
├── .env                    # API keys (not committed)
├── .env.example            # Template for .env
├── requirements.txt
└── README.md
```

---

## Known Limitations

- **Data Freshness**: The vector database is refreshed automatically every day at 10:30 AM IST via a GitHub Actions cron job.
- **No real-time NAV**: While data is updated daily, there is no real-time (minute-by-minute) NAV data stream. Mutual fund NAVs are officially updated once per day after market close.
- Only 7 Groww schemes are covered; other funds will return "not found"
- English queries only

---

## Disclaimer

This tool provides factual information only. It does **not** provide investment advice,
financial recommendations, or performance projections.
All data is sourced exclusively from official Groww scheme pages.
