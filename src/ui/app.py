"""
src/ui/app.py
=============
Phase 9 — User Interface (Streamlit)
Pure Streamlit components — no raw HTML in the response area.
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.retrieval.retriever as _retriever_module
from src.retrieval.intent_classifier import Intent, classify
from src.retrieval.retriever import retrieve
from src.refusal.refusal_handler import get_refusal
from src.generation.prompt_builder import build_prompt
from src.generation.llm_client import generate
from src.generation.response_formatter import format_factual, format_refusal, FormattedResponse

# Force-reload FAISS index from disk on every startup
_retriever_module._cache.clear()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Groww MF Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load CSS
# ---------------------------------------------------------------------------
CSS_PATH = PROJECT_ROOT / "src" / "ui" / "style.css"
if CSS_PATH.exists():
    st.markdown(f"<style>{CSS_PATH.read_text()}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📈 MF Assistant")
    st.caption("Groww Mutual Fund FAQ")
    st.divider()

    st.markdown("**Covered Schemes**")
    schemes = [
        "Groww Value Fund",
        "Groww Nifty Smallcap 250",
        "Groww Nifty Total Market",
        "Groww Nifty EV & New Age",
        "Groww Gold ETF FoF",
        "Groww Nifty India Defence",
        "Groww Nifty Non-Cyclical",
    ]
    for scheme in schemes:
        st.markdown(f"- {scheme}")

    st.divider()
    st.markdown("**Quick Stats**")
    col1, col2 = st.columns(2)
    col1.metric("Funds", "7")
    col2.metric("Mode", "Facts")

    st.divider()
    if st.button("🔄 Reload Index", use_container_width=True,
                 help="Force-reload the FAISS index from disk"):
        _retriever_module._cache.clear()
        st.success("Index reloaded!")

    st.divider()
    st.caption("Powered by Llama 3.3 + FAISS")

# ---------------------------------------------------------------------------
# Main area header
# ---------------------------------------------------------------------------
st.title("Groww Mutual Fund FAQ Assistant")
st.markdown("Ask me anything about Groww's mutual fund offerings.")
st.warning("⚠️ This tool provides factual data only. It is **not** investment advice.", icon="⚠️")

# ---------------------------------------------------------------------------
# Example query chips using columns
# ---------------------------------------------------------------------------
EXAMPLE_QUERIES = [
    "What is the expense ratio of Groww Value Fund?",
    "What is the exit load on Groww Nifty Smallcap 250?",
    "What benchmark does Groww Gold ETF FoF track?",
    "Should I invest my life savings in Groww Value Fund?",
]

st.markdown("**Example Queries**")

if "selected_example" not in st.session_state:
    st.session_state.selected_example = None

chip_cols = st.columns(len(EXAMPLE_QUERIES))
for i, q in enumerate(EXAMPLE_QUERIES):
    with chip_cols[i]:
        if st.button(q, key=f"chip_{i}", use_container_width=True):
            st.session_state.selected_example = q

st.divider()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# Helper: Render a FormattedResponse using native Streamlit components
# ---------------------------------------------------------------------------
def render_response(resp: FormattedResponse):
    if resp.is_refusal:
        st.error(f"🚫 **Cannot Provide Advice**\n\n{resp.answer}", icon="🚫")
    else:
        st.success(resp.answer, icon="✅")

    st.caption(f"📎 **Source:** [{resp.citation_label}]({resp.citation_url})")
    st.caption(f"🕒 **Last updated:** {resp.last_updated}")
    st.info(f"⚠️ {resp.disclaimer}", icon="ℹ️")


# ---------------------------------------------------------------------------
# Render existing chat history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        if role == "user":
            st.write(msg["content"])
        else:
            render_response(msg["content"])

# ---------------------------------------------------------------------------
# Chat Input
# ---------------------------------------------------------------------------
user_input = st.chat_input("Ask about Groww Mutual Funds...")

# Support chip selection
if st.session_state.selected_example:
    user_input = st.session_state.selected_example
    st.session_state.selected_example = None

# ---------------------------------------------------------------------------
# Process query
# ---------------------------------------------------------------------------
if user_input:
    # Render user message
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            # 1. Classify intent
            intent = classify(user_input)

            # 2. Route & Generate
            if intent == Intent.FACTUAL:
                chunks = retrieve(user_input, top_k=5)
                if not chunks:
                    formatted = format_refusal(
                        "I could not find relevant information for this query in the available scheme documents."
                    )
                else:
                    prompt    = build_prompt(user_input, chunks)
                    answer    = generate(prompt)
                    formatted = format_factual(answer, chunks[0])
            else:
                refusal_msg = get_refusal(intent)
                formatted   = format_refusal(refusal_msg)

        # 3. Render response
        render_response(formatted)

    st.session_state.messages.append({"role": "assistant", "content": formatted})
