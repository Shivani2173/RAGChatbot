"""
src/generation/llm_client.py
=============================
Phase 6.2 -- LLM API Wrapper

Wraps the Groq API with rate-limiting, retry logic, and token budgeting
to stay within the free-tier limits of llama-3.3-70b-versatile.

Groq rate limits (user-specified):
    - 30 requests / minute
    - 1,000 requests / day
    - 12,000 tokens / minute
    - 100,000 tokens / day

Spec reference: ImplementationPlan.md SS 6.2
"""

import logging
import os
import time
import threading
from collections import deque
from datetime import datetime, timezone

import groq
from dotenv import load_dotenv

from src.generation.prompt_builder import SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Streamlit Cloud secrets support
# When deployed on Streamlit Community Cloud, inject st.secrets into os.environ
# so the rest of the code can use os.getenv("GROQ_API_KEY") unchanged.
# Locally, python-dotenv (above) handles the .env file.
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
        os.environ.setdefault("GROQ_API_KEY", st.secrets["GROQ_API_KEY"])
except Exception:
    pass  # Not running in Streamlit context (e.g. pipeline_runner, tests)

# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------
PRIMARY_MODEL = "llama-3.3-70b-versatile"   # user-specified model
TEMPERATURE   = 0.0    # deterministic, factual output (SS 6.2)
MAX_TOKENS    = 200    # enforces brevity (SS 6.2)

# ---------------------------------------------------------------------------
# Rate-limit config (Groq free tier)
# ---------------------------------------------------------------------------
RPM_LIMIT         = 30       # requests per minute
RPD_LIMIT         = 1_000    # requests per day
TPM_LIMIT         = 12_000   # tokens per minute
TPD_LIMIT         = 100_000  # tokens per day
RETRY_WAIT_SECS   = 5        # wait before retrying on rate-limit error
MAX_RETRIES       = 3        # max retry attempts on rate-limit / transient errors

# Approximate tokens-per-character ratio for budget estimation
CHARS_PER_TOKEN = 4

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class _RateLimiter:
    """
    Thread-safe sliding-window rate limiter that tracks both request count
    and token usage across minute and day windows.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Sliding windows: deque of (timestamp, token_count)
        self._minute_log: deque[tuple[float, int]] = deque()
        self._day_log: deque[tuple[float, int]] = deque()

    def _prune(self, window: deque, max_age_secs: float, now: float) -> None:
        """Remove entries older than max_age_secs."""
        while window and (now - window[0][0]) > max_age_secs:
            window.popleft()

    def check_and_wait(self, estimated_tokens: int) -> None:
        """
        Block until the request can proceed within rate limits.
        Raises RuntimeError if the daily limit is exhausted.
        """
        while True:
            with self._lock:
                now = time.time()

                # Prune old entries
                self._prune(self._minute_log, 60.0, now)
                self._prune(self._day_log, 86_400.0, now)

                # Daily limits (hard stop)
                day_requests = len(self._day_log)
                day_tokens = sum(t for _, t in self._day_log)

                if day_requests >= RPD_LIMIT:
                    raise RuntimeError(
                        f"Groq daily request limit reached ({RPD_LIMIT} RPD). "
                        "Try again tomorrow."
                    )
                if day_tokens + estimated_tokens > TPD_LIMIT:
                    raise RuntimeError(
                        f"Groq daily token limit approaching ({day_tokens}/{TPD_LIMIT} TPD). "
                        "Try again tomorrow."
                    )

                # Per-minute limits (wait if exceeded)
                min_requests = len(self._minute_log)
                min_tokens = sum(t for _, t in self._minute_log)

                if min_requests < RPM_LIMIT and (min_tokens + estimated_tokens) < TPM_LIMIT:
                    # Within limits — proceed
                    return

            # Outside per-minute limits — wait and retry
            wait = 2.0
            logger.info(
                "Rate limit: %d/%d RPM, %d/%d TPM — waiting %.0fs",
                min_requests, RPM_LIMIT, min_tokens, TPM_LIMIT, wait,
            )
            time.sleep(wait)

    def record(self, tokens_used: int) -> None:
        """Record a completed request and its token usage."""
        with self._lock:
            now = time.time()
            self._minute_log.append((now, tokens_used))
            self._day_log.append((now, tokens_used))


# Module-level singleton
_limiter = _RateLimiter()


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1 token per 4 characters."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def generate(prompt: str) -> str:
    """
    Send the prompt to Groq LLM and return the generated answer.

    Uses the system prompt from prompt_builder as the system message,
    and the user-built prompt (context + question) as the user message.

    Handles:
      - Rate limiting (RPM, TPM, RPD, TPD)
      - Retry with backoff on transient / rate-limit errors
      - Graceful fallback message on failure

    Args:
        prompt: The user-role prompt string (from build_prompt).

    Returns:
        The LLM-generated answer text.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        return (
            "LLM is not configured. Please set GROQ_API_KEY in your .env file. "
            "Get a free key at https://console.groq.com"
        )

    client = groq.Groq(api_key=api_key)

    # Estimate total tokens (system + user prompt + max completion)
    est_input_tokens = _estimate_tokens(SYSTEM_PROMPT) + _estimate_tokens(prompt)
    est_total_tokens = est_input_tokens + MAX_TOKENS

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Check rate limits before sending
            _limiter.check_and_wait(est_total_tokens)

            logger.info(
                "LLM request (attempt %d/%d): model=%s, est_tokens=%d",
                attempt, MAX_RETRIES, PRIMARY_MODEL, est_total_tokens,
            )

            response = client.chat.completions.create(
                model=PRIMARY_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )

            answer = response.choices[0].message.content.strip()

            # Record actual token usage
            usage = response.usage
            actual_tokens = (usage.total_tokens if usage else est_total_tokens)
            _limiter.record(actual_tokens)

            logger.info(
                "LLM response received: %d tokens used (prompt=%s, completion=%s)",
                actual_tokens,
                getattr(usage, "prompt_tokens", "?"),
                getattr(usage, "completion_tokens", "?"),
            )

            return answer

        except groq.RateLimitError as exc:
            last_error = exc
            wait = RETRY_WAIT_SECS * attempt
            logger.warning(
                "Rate limited by Groq (attempt %d/%d): %s — waiting %ds",
                attempt, MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)

        except groq.APIStatusError as exc:
            last_error = exc
            if exc.status_code in (500, 502, 503, 529):
                wait = RETRY_WAIT_SECS * attempt
                logger.warning(
                    "Groq server error %d (attempt %d/%d) — retrying in %ds",
                    exc.status_code, attempt, MAX_RETRIES, wait,
                )
                time.sleep(wait)
            else:
                logger.error("Groq API error (non-retryable): %s", exc)
                break

        except RuntimeError as exc:
            # Daily limit exhausted
            logger.error("Rate limiter: %s", exc)
            return str(exc)

        except Exception as exc:
            last_error = exc
            logger.error("Unexpected LLM error: %s", exc)
            break

    # All retries exhausted
    logger.error("LLM generation failed after %d attempts: %s", MAX_RETRIES, last_error)
    return (
        "I'm temporarily unable to process your request due to API limits. "
        "Please try again in a moment."
    )
