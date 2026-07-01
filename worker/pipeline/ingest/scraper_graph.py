"""Universal URL scraper as a LangGraph StateGraph.

Replaces the fixture/EURAXESS scrapers. The user pastes any listing URL;
the graph fetches the page, detects JS-rendered shells, falls back to
Playwright when needed, LLM-extracts listings from the resulting HTML,
validates, and paginates up to MAX_PAGES_PER_URL.

If `langgraph` is not installed we fall back to a hand-rolled async
runner that drives the same nodes in the same order. Same external
interface either way: `run_scraper_graph(url, llm, *, max_pages)
-> list[ExtractedListing]`.

Spec: see phd copilot.md → "Agent 1 — Universal Scraper Agent".

       ┌──────────────┐
       │ fetch_simple │ httpx + BeautifulSoup
       └──────┬───────┘
              │
       ┌──────▼──────────────────┐
       │ is content real?         │
       │ >500 words of real text? │
       └──────┬───────────────────┘
              │ yes      │ no (JS shell)
              │          ▼
              │    ┌────────────────┐
              │    │ fetch_playwright│ Chromium headless
              │    └────────┬───────┘
              ▼             │
       ┌──────────────────┐ │
       │ extract_listings │◄┘  LLM parses arbitrary HTML
       └──────┬───────────┘
              │
       ┌──────▼──────────┐
       │ valid JSON?      │
       └──────┬──────────┘
              │ yes        │ no (max 3 retries)
              ▼            └──► extract_listings
       ┌──────────────────┐
       │ check_pagination │
       └──────┬──────────┘
              │ has next page?
              ├─yes──► fetch_simple (next page)
              └─no───► END
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin

from shared.llm import ExtractedListing, LLMClient

log = logging.getLogger("phd_copilot.scraper")

MIN_REAL_CONTENT_WORDS = 500
MAX_EXTRACTION_RETRIES = 3


# ----------------------------- nodes -----------------------------------


def _strip_html(html: str) -> str:
    try:
        from bs4 import BeautifulSoup  # lazy

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        return soup.get_text("\n", strip=True)
    except ImportError:
        text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()


def _word_count(text: str) -> int:
    return len(text.split())


def _looks_js_shell(text: str) -> bool:
    if _word_count(text) < MIN_REAL_CONTENT_WORDS:
        return True
    lowered = text.lower()
    return "please enable javascript" in lowered or "loading…" in lowered or "loading..." in lowered


async def fetch_simple(state: dict[str, Any], *, user_agent: str) -> dict[str, Any]:
    url = state["current_url"]
    log.info("fetch_simple %s", url)
    try:
        import httpx  # lazy

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=20.0,
            headers={"User-Agent": user_agent},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:
        log.warning("fetch_simple failed: %s", exc)
        return {**state, "html": None, "rendering": "simple", "error": str(exc)}
    return {**state, "html": html, "rendering": "simple", "error": None}


async def fetch_playwright(state: dict[str, Any]) -> dict[str, Any]:
    url = state["current_url"]
    log.info("fetch_playwright %s", url)
    try:
        from playwright.async_api import async_playwright  # lazy

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                html = await page.content()
            finally:
                await browser.close()
    except Exception as exc:
        log.warning("fetch_playwright failed: %s", exc)
        return {**state, "html": state.get("html"), "rendering": "playwright_failed", "error": str(exc)}
    return {**state, "html": html, "rendering": "playwright", "error": None}


def needs_playwright(state: dict[str, Any]) -> str:
    html = state.get("html") or ""
    text = _strip_html(html)
    if _looks_js_shell(text) and state.get("playwright_enabled", True):
        return "playwright"
    return "extract"


async def extract_listings(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    html = state.get("html") or ""
    text = _strip_html(html)
    attempts = state.get("attempt", 0) + 1
    log.info("extract_listings attempt=%s len(text)=%d", attempts, len(text))
    try:
        listings = llm.extract_listings_from_html(text[:20000], state["current_url"])
    except Exception as exc:
        log.warning("extract_listings failed: %s", exc)
        return {**state, "attempt": attempts, "listings": [], "error": str(exc)}
    return {**state, "attempt": attempts, "listings": listings, "error": None}


def extraction_valid(state: dict[str, Any]) -> str:
    if state.get("listings"):
        return "ok"
    if state.get("attempt", 0) < MAX_EXTRACTION_RETRIES:
        return "retry"
    return "ok"  # give up, treat as page-done


def check_pagination(state: dict[str, Any]) -> dict[str, Any]:
    """Find a 'next page' link in the HTML. Conservative — only follows
    anchors whose text or class looks like next/pagination.
    """
    html = state.get("html") or ""
    page = state.get("page", 1)
    if page >= state.get("max_pages", 10):
        return {**state, "next_url": None}

    next_url: Optional[str] = None
    try:
        from bs4 import BeautifulSoup  # lazy

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a"):
            text = (a.get_text() or "").strip().lower()
            rel = " ".join(a.get("rel") or []).lower()
            cls = " ".join(a.get("class") or []).lower()
            href = a.get("href") or ""
            if not href:
                continue
            if (
                rel == "next"
                or text in {"next", "next page", "next ›", ">", "→"}
                or "next" in cls
                or "pagination__next" in cls
            ):
                next_url = urljoin(state["current_url"], href)
                break
    except ImportError:
        match = re.search(r'href="([^"]+)"[^>]*>\s*(?:Next|next|next page)', html)
        if match:
            next_url = urljoin(state["current_url"], match.group(1))

    return {**state, "next_url": next_url}


# ----------------------------- runner ----------------------------------


async def _run_without_langgraph(
    initial: dict[str, Any], *, llm: LLMClient, user_agent: str
) -> dict[str, Any]:
    state = initial
    while True:
        state = await fetch_simple(state, user_agent=user_agent)
        if needs_playwright(state) == "playwright":
            state = await fetch_playwright(state)

        for _ in range(MAX_EXTRACTION_RETRIES):
            state = await extract_listings(state, llm=llm)
            if state.get("listings"):
                break

        state["all_listings"] = state.get("all_listings", []) + list(state.get("listings") or [])

        state = check_pagination(state)
        next_url = state.get("next_url")
        if not next_url:
            break
        state["current_url"] = next_url
        state["page"] = state.get("page", 1) + 1
        state["attempt"] = 0

    return state


def _build_langgraph(llm: LLMClient, user_agent: str):
    """Build the actual StateGraph if langgraph is importable. Returns the
    compiled graph or None if langgraph isn't installed.
    """
    try:
        from langgraph.graph import END, StateGraph  # lazy
    except ImportError:
        return None

    async def _fetch_simple(state):
        return await fetch_simple(state, user_agent=user_agent)

    async def _fetch_playwright(state):
        return await fetch_playwright(state)

    async def _extract(state):
        return await extract_listings(state, llm=llm)

    def _pagination(state):
        out = check_pagination(state)
        if out.get("next_url"):
            return {**out, "current_url": out["next_url"], "page": out.get("page", 1) + 1, "attempt": 0}
        return out

    def _accumulate(state):
        return {
            **state,
            "all_listings": list(state.get("all_listings") or []) + list(state.get("listings") or []),
        }

    g = StateGraph(dict)
    g.add_node("fetch_simple", _fetch_simple)
    g.add_node("fetch_playwright", _fetch_playwright)
    g.add_node("extract", _extract)
    g.add_node("accumulate", _accumulate)
    g.add_node("pagination", _pagination)

    g.set_entry_point("fetch_simple")
    g.add_conditional_edges("fetch_simple", needs_playwright, {
        "playwright": "fetch_playwright",
        "extract": "extract",
    })
    g.add_edge("fetch_playwright", "extract")
    g.add_conditional_edges("extract", extraction_valid, {
        "retry": "extract",
        "ok": "accumulate",
    })
    g.add_edge("accumulate", "pagination")
    g.add_conditional_edges(
        "pagination",
        lambda s: "next" if s.get("next_url") else "end",
        {"next": "fetch_simple", "end": END},
    )
    return g.compile()


async def run_scraper_graph(
    url: str,
    llm: LLMClient,
    *,
    max_pages: int = 10,
    user_agent: str = "phd-copilot/0.1",
    playwright_enabled: bool = True,
) -> list[ExtractedListing]:
    initial = {
        "url": url,
        "current_url": url,
        "html": None,
        "listings": [],
        "all_listings": [],
        "attempt": 0,
        "page": 1,
        "max_pages": max_pages,
        "error": None,
        "rendering": "simple",
        "playwright_enabled": playwright_enabled,
    }

    graph = _build_langgraph(llm, user_agent)
    if graph is not None:
        final = await graph.ainvoke(initial)
    else:
        log.info("langgraph not installed — using sequential runner")
        final = await _run_without_langgraph(initial, llm=llm, user_agent=user_agent)

    return list(final.get("all_listings") or [])
