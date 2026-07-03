# Project Context: Mutual Fund FAQ Assistant

## Overview

This project builds a **facts-only FAQ assistant** for mutual fund schemes, using **Groww** as the reference product context. The assistant answers objective, verifiable queries about mutual funds by retrieving information exclusively from official public sources (AMC websites, AMFI, and SEBI).

> **Core Principle**: The system must strictly avoid providing investment advice, opinions, or recommendations. Every response must include a single, clear source citation and a "last updated" footer.

---

## Objective

Design and implement a lightweight **Retrieval-Augmented Generation (RAG)**-based assistant that:
- Answers **factual queries** about mutual fund schemes
- Uses a **curated corpus** of official documents
- Provides **concise, source-backed** responses (max 3 sentences per answer)

---

## Target Users

| User Type | Use Case |
|---|---|
| Retail Investors | Comparing mutual fund schemes objectively |
| Customer Support Teams | Handling repetitive mutual fund queries |
| Content Teams | Quickly referencing factual fund details |

---

## Scope of Work

### 1. Corpus Definition

- **Selected AMC**: Groww Mutual Fund (Groww Asset Management Ltd.)
- **Number of Schemes**: 7 schemes across diverse fund categories
- Collect **15–25 official public URLs**, including:
  - Scheme Factsheets
  - KIM (Key Information Memorandum)
  - SID (Scheme Information Document)
  - AMC FAQ / Help Pages
  - AMFI / SEBI Guidance Pages
  - Statement and tax document download guides

### 2. FAQ Assistant Requirements

The assistant must answer **facts-only queries** such as:
- Expense ratio of a scheme
- Exit load details
- Minimum SIP amount
- ELSS lock-in period
- Riskometer classification
- Benchmark index
- Process to download statements or capital gains reports

**Response Format Rules:**
- Maximum **3 sentences** per response
- Exactly **one citation link** per response
- Footer: `"Last updated from sources: <date>"`

### 3. Refusal Handling

The assistant must **refuse** non-factual or advisory queries, such as:
- *"Should I invest in this fund?"*
- *"Which fund is better?"*

Refusal responses must:
- Be polite and clearly worded
- Reinforce the facts-only limitation
- Provide a relevant educational link (e.g., AMFI or SEBI resource)

### 4. User Interface

A minimal UI including:
- A **welcome message**
- **Three example questions**
- A visible disclaimer: `"Facts-only. No investment advice."`

---

## Selected AMC & Fund Schemes

**AMC**: [Groww Mutual Fund](https://groww.in/mutual-funds)

The following **7 Groww schemes** form the corpus for this RAG chatbot:

| # | Scheme Name | Category | Groww URL |
|---|---|---|---|
| 1 | Groww Gold ETF FoF – Direct Growth | Gold / FoF | [Link](https://groww.in/mutual-funds/groww-gold-etf-fof-direct-growth) |
| 2 | Groww Nifty India Defence ETF FoF – Direct Growth | Sectoral / Defence | [Link](https://groww.in/mutual-funds/groww-nifty-india-defence-etf-fof-direct-growth) |
| 3 | Groww Nifty Total Market Index Fund – Direct Growth | Index / Broad Market | [Link](https://groww.in/mutual-funds/groww-nifty-total-market-index-fund-direct-growth) |
| 4 | Groww Nifty EV & New Age Automotive ETF FoF – Direct Growth | Sectoral / EV & Auto | [Link](https://groww.in/mutual-funds/groww-nifty-ev-new-age-automotive-etf-fof-direct-growth) |
| 5 | Groww Nifty Smallcap 250 Index Fund – Direct Growth | Index / Small Cap | [Link](https://groww.in/mutual-funds/groww-nifty-smallcap-250-index-fund-direct-growth) |
| 6 | Groww Value Fund – Direct Growth | Value / Active Equity | [Link](https://groww.in/mutual-funds/groww-value-fund-direct-growth) |
| 7 | Groww Nifty Non-Cyclical Consumer Index Fund – Direct Growth | Index / Consumer | [Link](https://groww.in/mutual-funds/groww-nifty-non-cyclical-consumer-index-fund-direct-growth) |

### Why These Schemes?

- **Category diversity**: Gold, Defence, Total Market, EV/Auto, Smallcap, Value, and Consumer sectors
- **Mix of passive and active**: Index funds, ETF FoFs, and an actively managed value fund
- **All Direct Growth plans**: Ensures low-cost, no-commission variants for unbiased factual reference
- **All from a single AMC**: Keeps the corpus focused and consistent for retrieval

---

## Constraints

### Data & Sources
- Use **only official public sources**: AMC, AMFI, SEBI
- Do **not** use third-party blogs or aggregator websites

### Privacy & Security
Do **not** collect, store, or process any of the following:
- PAN or Aadhaar numbers
- Account numbers
- OTPs
- Email addresses or phone numbers

### Content Restrictions
- No investment advice or recommendations
- No performance comparisons or return calculations
- For performance-related queries → provide a link to the official factsheet only

### Transparency
- Responses must be short, factual, and verifiable
- Every answer must include a **source link** and **last updated date**

---

## Architecture Overview (RAG Approach)

```
User Query
    |
    v
Query Understanding / Intent Classification
    |
    +-- Advisory Query? --> Polite Refusal + Educational Link
    |
    +-- Factual Query?
            |
            v
      Vector Store (Official Docs: Factsheets, KIM, SID, AMFI, SEBI)
            |
            v
      Retriever (Semantic Search over embedded documents)
            |
            v
      LLM Response Generation (facts-only, max 3 sentences)
            |
            v
      Response + Citation Link + "Last updated: <date>" Footer
```

---

## Expected Deliverables

| Deliverable | Details |
|---|---|
| **README** | Setup instructions, selected AMC & schemes, architecture overview, known limitations |
| **RAG Application** | Working chatbot with retrieval and generation pipeline |
| **Disclaimer Snippet** | `"Facts-only. No investment advice."` |

---

## Success Criteria

- Accurate retrieval of factual mutual fund information
- Strict adherence to facts-only responses
- Consistent inclusion of valid source citations
- Proper refusal of advisory queries
- Clean, minimal, and user-friendly interface

---

## Key Design Principles

1. **Accuracy over Intelligence** — Prefer verified facts over inferred answers
2. **Transparency** — Every answer must be traceable to a source
3. **Compliance** — No advisory content, no personal data handling
4. **Minimalism** — Simple UI, concise responses, no clutter

---

## Summary

The goal is to build a **trustworthy, transparent, and compliant** mutual fund FAQ assistant that prioritizes **accuracy over intelligence**. The system ensures users receive only verified, source-backed financial information — without any advisory bias or speculative content.
