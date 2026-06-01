"""
HTML scraper module for Groww mutual fund pages.
Fetches content from Groww URLs, extracts structured fund data
from Next.js SSR data (__NEXT_DATA__), and falls back to HTML
parsing when structured data is unavailable.
"""

import json
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from datetime import date


# Default headers to avoid bot-detection blocks
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 20  # seconds


def fetch_html(url: str, timeout: int = REQUEST_TIMEOUT) -> str | None:
    """Fetch raw HTML from a URL. Returns None on failure."""
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"  [SCRAPER] Error fetching {url}: {e}")
        return None


def extract_next_data(soup: BeautifulSoup) -> dict | None:
    """Extract the __NEXT_DATA__ JSON object from a Next.js page."""
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if script_tag and script_tag.string:
        try:
            data = json.loads(script_tag.string)
            return data.get("props", {}).get("pageProps", {}).get("mfServerSideData")
        except (json.JSONDecodeError, KeyError):
            return None
    return None


def format_holdings(holdings: list[dict], max_items: int = 10) -> str:
    """Format top holdings into readable text."""
    if not holdings:
        return ""
    lines = ["Top Holdings:"]
    for h in holdings[:max_items]:
        name = h.get("company_name", h.get("name", "Unknown"))
        pct = h.get("corpus_per", h.get("percentage", ""))
        sector = h.get("sector_name", h.get("sector", ""))
        instrument = h.get("instrument_name", "")
        if sector:
            lines.append(f"  - {name} ({sector}, {instrument}): {pct}%")
        else:
            lines.append(f"  - {name}: {pct}%")
    return "\n".join(lines)


def format_return_stats(return_stats: list[dict]) -> str:
    """Format return statistics into readable text."""
    if not return_stats:
        return ""
    lines = []
    for stat in return_stats:
        title = stat.get("title", stat.get("type", ""))
        stat_1y = stat.get("stat_1y")
        stat_3y = stat.get("stat_3y")
        stat_5y = stat.get("stat_5y")
        stat_all = stat.get("stat_all")
        parts = []
        if stat_1y is not None:
            parts.append(f"1Y: {stat_1y}%")
        if stat_3y is not None:
            parts.append(f"3Y: {stat_3y}%")
        if stat_5y is not None:
            parts.append(f"5Y: {stat_5y}%")
        if stat_all is not None:
            parts.append(f"Since Inception: {stat_all}%")
        if parts:
            lines.append(f"{title}: {', '.join(parts)}")
    return "\n".join(lines) if lines else ""


def format_lock_in(lock_in: dict | None) -> str:
    """Format lock-in period."""
    if not lock_in:
        return "No lock-in period"
    years = lock_in.get("years", 0)
    months = lock_in.get("months", 0)
    days = lock_in.get("days", 0)
    parts = []
    if years:
        parts.append(f"{years} year(s)")
    if months:
        parts.append(f"{months} month(s)")
    if days:
        parts.append(f"{days} day(s)")
    return "Lock-in: " + ", ".join(parts) if parts else "No lock-in period"


def format_category_info(cat_info: dict | None) -> str:
    """Format category information."""
    if not cat_info:
        return ""
    lines = []
    definition = cat_info.get("definition", "")
    description = cat_info.get("description", "")
    tax_impact = cat_info.get("tax_impact", "")
    if definition:
        lines.append(f"Category Definition: {definition}")
    if description:
        lines.append(f"Category Description: {description}")
    if tax_impact:
        lines.append(f"Tax Impact: {tax_impact}")
    return "\n".join(lines)


def build_structured_text(mf_data: dict) -> str:
    """
    Build a comprehensive text document from the structured
    Groww mutual fund data (from __NEXT_DATA__).
    """
    sections = []

    # ─── Basic Fund Information ────────────────────────────────
    basic = [
        f"Fund Name: {mf_data.get('fund_name', '')}",
        f"Scheme Name: {mf_data.get('scheme_name', '')}",
        f"Fund House: {mf_data.get('fund_house', '')}",
        f"AMC: {mf_data.get('amc', '')}",
        f"Category: {mf_data.get('category', '')}",
        f"Sub-Category: {mf_data.get('sub_category', '')}",
        f"Plan Type: {mf_data.get('plan_type', '')}",
        f"Scheme Type: {mf_data.get('scheme_type', '')}",
        f"Launch Date: {mf_data.get('launch_date', '')}",
    ]
    sections.append("=== Fund Information ===\n" + "\n".join(basic))

    # ─── Key Metrics ───────────────────────────────────────────
    metrics = [
        f"Expense Ratio: {mf_data.get('expense_ratio', 'N/A')}%",
        f"Exit Load: {mf_data.get('exit_load', 'N/A')}",
        f"NAV: {mf_data.get('nav', 'N/A')} (as of {mf_data.get('nav_date', 'N/A')})",
        f"AUM: ₹{mf_data.get('aum', 'N/A')} crores",
        f"Benchmark: {mf_data.get('benchmark', 'N/A')}",
        f"Benchmark Name: {mf_data.get('benchmark_name', 'N/A')}",
        f"Riskometer: {mf_data.get('nfo_risk', 'N/A')}",
        f"Groww Rating: {mf_data.get('groww_rating', 'N/A')}/5",
        f"Portfolio Turnover: {mf_data.get('portfolio_turnover', 'N/A')}%",
        f"Stamp Duty: {mf_data.get('stamp_duty', 'N/A')}",
    ]
    sections.append("=== Key Metrics ===\n" + "\n".join(metrics))

    # ─── Investment Details ────────────────────────────────────
    investment = [
        f"Minimum Investment (Lumpsum): ₹{mf_data.get('min_investment_amount', 'N/A')}",
        f"Minimum SIP Amount: ₹{mf_data.get('min_sip_investment', 'N/A')}",
        f"Maximum SIP Investment: ₹{mf_data.get('max_sip_investment', 'N/A')}",
        f"Minimum Withdrawal: ₹{mf_data.get('min_withdrawal', 'N/A')}",
        f"Minimum Additional Investment: ₹{mf_data.get('mini_additional_investment', 'N/A')}",
        format_lock_in(mf_data.get("lock_in")),
        f"SIP Allowed: {'Yes' if mf_data.get('sip_allowed') else 'No'}",
        f"Lumpsum Allowed: {'Yes' if mf_data.get('lumpsum_allowed') else 'No'}",
    ]
    sections.append("=== Investment Details ===\n" + "\n".join(investment))

    # ─── Fund Manager ──────────────────────────────────────────
    fm = mf_data.get("fund_manager", "")
    if fm:
        sections.append(f"=== Fund Manager ===\nFund Manager: {fm}")

    # ─── Description ───────────────────────────────────────────
    desc = mf_data.get("description", "")
    if desc:
        sections.append(f"=== Scheme Objective ===\n{desc}")

    # ─── Category Info ─────────────────────────────────────────
    cat_info = format_category_info(mf_data.get("category_info"))
    if cat_info:
        sections.append(f"=== Category Details ===\n{cat_info}")

    # ─── Registrar & RTA ───────────────────────────────────────
    registrar = mf_data.get("registrar_agent", "")
    rta = mf_data.get("rta_details", {})
    rta_lines = [f"Registrar: {registrar}"]
    if rta:
        if rta.get("rta_name"):
            rta_lines.append(f"RTA Name: {rta['rta_name']}")
        if rta.get("custodian_name"):
            rta_lines.append(f"Custodian: {rta['custodian_name']}")
    sections.append("=== Operational Details ===\n" + "\n".join(rta_lines))

    # ─── Holdings ──────────────────────────────────────────────
    holdings_text = format_holdings(mf_data.get("holdings", []))
    if holdings_text:
        sections.append(holdings_text)

    # ─── Return Stats ──────────────────────────────────────────
    return_text = format_return_stats(mf_data.get("stats", []))
    if return_text:
        sections.append(return_text)

    return "\n\n".join(sections)


def extract_html_fallback(soup: BeautifulSoup) -> str:
    """
    Fallback: extract text from HTML when __NEXT_DATA__ is unavailable.
    Strips non-content elements and extracts paragraphs, tables, and lists.
    """
    # Strip non-content tags
    strip_tags = {"script", "style", "nav", "footer", "header", "noscript", "iframe", "aside"}
    for tag in list(soup.find_all(strip_tags)):
        tag.decompose()

    text_parts = []

    # Extract title
    title_tag = soup.find("h1")
    if title_tag:
        text_parts.append(f"Fund: {title_tag.get_text(strip=True)}")

    # Extract tables
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            cell_texts = [c.get_text(strip=True) for c in cells if c.get_text(strip=True)]
            if cell_texts:
                text_parts.append(" | ".join(cell_texts))

    # Extract paragraphs
    for p in soup.find_all("p"):
        p_text = p.get_text(strip=True)
        if p_text and len(p_text) > 20:
            text_parts.append(p_text)

    # Extract list items
    for ul in soup.find_all("ul"):
        items = [li.get_text(strip=True) for li in ul.find_all("li") if li.get_text(strip=True)]
        if items:
            text_parts.append("• " + " • ".join(items))

    return "\n".join(text_parts)


def scrape_source(source: dict) -> Document | None:
    """
    Scrape a Groww mutual fund page and return a LangChain Document
    with extracted text and metadata.

    Tries to extract structured data from __NEXT_DATA__ first,
    falls back to HTML parsing if unavailable.

    Args:
        source: A source entry from sources.json with id, url, type, scheme,
                category, format, title fields.

    Returns:
        A Document object or None if scraping fails.
    """
    url = source["url"]
    print(f"  [SCRAPER] Fetching: {url}")

    html = fetch_html(url)
    if html is None:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Try structured data extraction first
    mf_data = extract_next_data(soup)
    if mf_data:
        text = build_structured_text(mf_data)
        print(f"  [SCRAPER] Extracted structured data from __NEXT_DATA__")
    else:
        print(f"  [SCRAPER] No __NEXT_DATA__ found, using HTML fallback")
        text = extract_html_fallback(soup)

    if not text or len(text.strip()) < 50:
        print(f"  [SCRAPER] Warning: Very little content extracted from {url}")
        # Final fallback: get all visible text
        text = soup.get_text(separator="\n", strip=True)

    # Build metadata
    metadata = {
        "source_id": source["id"],
        "url": url,
        "title": source["title"],
        "scheme": source["scheme"],
        "category": source["category"],
        "type": source["type"],
        "scrape_date": str(date.today()),
    }

    # Enrich metadata from structured data if available
    if mf_data:
        metadata["expense_ratio"] = str(mf_data.get("expense_ratio", ""))
        metadata["riskometer"] = mf_data.get("nfo_risk", "")
        metadata["nav"] = str(mf_data.get("nav", ""))

    print(f"  [SCRAPER] Extracted {len(text)} characters from {source['id']}")

    return Document(page_content=text, metadata=metadata)
