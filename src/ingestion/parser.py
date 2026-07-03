"""
src/ingestion/parser.py
=======================
Phase 3.1 — HTML Parser

For each raw HTML file in data/raw/, this module:
  1. Loads it with BeautifulSoup (lxml parser)
  2. Removes nav, header, footer, script, style, aside, cookie/ad elements
  3. Extracts the main scheme content area
  4. Cleans text (normalize whitespace, strip unicode, drop short lines)
  5. Saves cleaned text to data/processed/<scheme_slug>.txt

Spec reference: ImplementationPlan.md § 3.1
"""

import json
import logging
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT   = Path(__file__).resolve().parents[2]
RAW_DIR        = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR  = PROJECT_ROOT / "data" / "processed"
METADATA_PATH  = RAW_DIR / "metadata.json"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MIN_LINE_LENGTH = 15   # § 3.1 step 4: remove lines shorter than 15 chars

# Tags to strip entirely (§ 3.1 step 2)
UNWANTED_TAGS = ["nav", "header", "footer", "script", "style", "aside",
                 "noscript", "svg", "iframe", "link", "meta"]

# CSS class fragments that indicate cookie banners, ads, or chrome
UNWANTED_CLASS_FRAGMENTS = [
    "cookie", "banner", "advert", "popup", "modal", "overlay",
    "breadcrumb", "footer", "navbar", "sidebar", "dropdown",
    "calculator", "screener",
]

# Footer / boilerplate sentinel phrases — any line containing these is dropped
FOOTER_SENTINELS = [
    "© 2016", "groww. all rights reserved", "version:",
    "download the app", "contact us", "careers",
    "help & support", "trust & safety", "investor relations",
    "terms and conditions", "privacy policy", "about us",
    "top gainers", "52 weeks high", "top losers",
    "nifty 50 stocks", "bse sensex stocks",
    "groww terminal", "915 terminal", "algo trading",
    "demat account", "pms",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _remove_unwanted_elements(soup: BeautifulSoup) -> None:
    """Remove boilerplate tags and ad/cookie-banner divs in-place (§ 3.1.2)."""
    # 1. Strip unwanted tags
    for tag in soup.find_all(UNWANTED_TAGS):
        tag.decompose()

    # 2. Strip divs whose class names match ad/cookie/banner patterns
    #    Snapshot the list first — decomposing during iteration mutates the tree.
    for div in list(soup.find_all("div", class_=True)):
        if div.attrs is None:
            continue  # already decomposed by a parent removal
        classes = " ".join(div.get("class", [])).lower()
        if any(frag in classes for frag in UNWANTED_CLASS_FRAGMENTS):
            div.decompose()


def _extract_text(soup: BeautifulSoup) -> str:
    """
    Extract text from the cleaned soup tree (§ 3.1.3).

    Uses newline as separator so we preserve structural boundaries
    between headings, paragraphs, and table cells.
    """
    return soup.get_text(separator="\n")


def _clean_text(raw_text: str) -> str:
    """
    Apply text-cleaning pipeline (§ 3.1.4):
      - Normalize unicode (NFKD → strip combining marks, then NFKC)
      - Collapse multiple whitespace / blank lines
      - Remove lines shorter than MIN_LINE_LENGTH
      - Remove footer / boilerplate lines
    """
    # Normalize unicode — replace fancy chars with ASCII-friendly equivalents
    text = unicodedata.normalize("NFKC", raw_text)

    # Strip zero-width and other invisible unicode characters
    text = re.sub(r"[\u200b-\u200f\u2028-\u202f\u2060\ufeff]", "", text)

    # Split into lines and clean each
    lines = text.split("\n")
    cleaned: list[str] = []

    for line in lines:
        # Collapse multiple spaces within a line
        line = re.sub(r"[ \t]+", " ", line).strip()

        # Skip empty or too-short lines
        if len(line) < MIN_LINE_LENGTH:
            continue

        # Skip footer / boilerplate lines
        if any(sentinel in line.lower() for sentinel in FOOTER_SENTINELS):
            continue

        cleaned.append(line)

    # Collapse multiple consecutive blank lines (shouldn't be any after above,
    # but just in case)
    result = "\n".join(cleaned)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def _extract_json_metrics(html: str) -> str:
    """Extract dynamic metrics (expense ratio, benchmark) from the __NEXT_DATA__ JSON block."""
    try:
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return ""
            
        data = json.loads(script.string)
        mf_data = data.get("props", {}).get("pageProps", {}).get("mfServerSideData", {})
        
        metrics = []
        if "expense_ratio" in mf_data:
            metrics.append(f"Expense Ratio: {mf_data['expense_ratio']}%")
        if "benchmark_name" in mf_data:
            metrics.append(f"Benchmark: {mf_data['benchmark_name']}")
            
        if metrics:
            return "\n".join(metrics) + "\n\n"
    except Exception as e:
        logger.warning(f"Failed to extract JSON metrics: {e}")
    return ""


# ---------------------------------------------------------------------------
# Core parsing logic
# ---------------------------------------------------------------------------

def parse_html(html_path: Path) -> str:
    """
    Parse a single raw HTML file and return cleaned text.

    Args:
        html_path: Path to the .html file in data/raw/.

    Returns:
        Cleaned text string.
    """
    html = html_path.read_text(encoding="utf-8")
    
    # Extract dynamic metrics from JSON state before the tags are decomposed
    json_metrics = _extract_json_metrics(html)
    
    soup = BeautifulSoup(html, "lxml")
    _remove_unwanted_elements(soup)
    raw_text = _extract_text(soup)
    cleaned = _clean_text(raw_text)

    # Inject metrics into body text — repeat them 3x with different phrasings
    # so they co-occur with scheme context in the same FAISS chunk and get
    # high similarity scores for expense ratio / benchmark queries.
    if json_metrics:
        # Parse out values for richer phrasing
        metric_lines = json_metrics.strip().split("\n")
        expense_line = next((l for l in metric_lines if "Expense Ratio" in l), "")
        benchmark_line = next((l for l in metric_lines if "Benchmark" in l), "")
        
        expense_val = expense_line.replace("Expense Ratio: ", "").strip() if expense_line else ""
        benchmark_val = benchmark_line.replace("Benchmark: ", "").strip() if benchmark_line else ""
        
        rich_metrics = []
        if expense_val:
            rich_metrics.append(f"The expense ratio of this fund is {expense_val}.")
            rich_metrics.append(f"Expense Ratio: {expense_val}")
        if benchmark_val:
            rich_metrics.append(f"The benchmark index tracked by this fund is {benchmark_val}.")
            rich_metrics.append(f"Benchmark Index: {benchmark_val}")
        
        metrics_block = "\n".join(rich_metrics)
        
        # Insert metrics right after the first line of the cleaned text
        lines = cleaned.split("\n")
        insert_at = min(2, len(lines))
        lines.insert(insert_at, metrics_block)
        cleaned = "\n".join(lines)
    
    return cleaned


def parse_all() -> list[dict]:
    """
    Parse all HTML files referenced in metadata.json.

    Returns:
        List of metadata dicts augmented with 'processed_file' path.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    results: list[dict] = []

    for entry in metadata:
        slug = entry["slug"]
        html_path = PROJECT_ROOT / entry["file"]

        if not html_path.exists():
            logger.error("HTML file not found: %s — skipping", html_path)
            continue

        logger.info("-" * 60)
        logger.info("Parsing: %s", entry["scheme_name"])

        cleaned_text = parse_html(html_path)

        # Save to data/processed/<slug>.txt (§ 3.1 step 5)
        out_path = PROCESSED_DIR / f"{slug}.txt"
        out_path.write_text(cleaned_text, encoding="utf-8")

        logger.info(
            "  Saved  %s  (%d chars, %d lines)",
            out_path.relative_to(PROJECT_ROOT),
            len(cleaned_text),
            cleaned_text.count("\n") + 1,
        )

        entry["processed_file"] = str(out_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        results.append(entry)

    logger.info("-" * 60)
    logger.info(
        "Parsed %d/%d schemes. Output in %s",
        len(results), len(metadata),
        PROCESSED_DIR.relative_to(PROJECT_ROOT),
    )

    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("Phase 3.1 — HTML Parser")
    logger.info("=" * 60)
    parse_all()


if __name__ == "__main__":
    main()
