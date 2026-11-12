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
from dataclasses import asdict
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from shared.llm import ExtractedListing, LLMClient

log = logging.getLogger("phd_copilot.scraper")

MIN_REAL_CONTENT_WORDS = 500
MAX_EXTRACTION_RETRIES = 3

# The extract prompt hard-caps its CONTENT block at 12k chars, so page text
# is processed in chunks of ≤ CHUNK_CHARS. In the TEXT-FALLBACK path,
# _chunk_text overlaps chunks by CHUNK_OVERLAP so a listing straddling a
# boundary stays intact in one of them; the structured path (_pack_blocks)
# never splits a card, so it needs no overlap.
CHUNK_CHARS = 11000
CHUNK_OVERLAP = 1500
MAX_CHUNKS_PER_PAGE = 6  # cost ceiling: ~64k chars of one page fed to the LLM

# Elements that are never listing content — dropped before the text ever
# reaches the LLM so the chunk budget is spent on real content.
_BOILERPLATE_TAGS = ["script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form", "iframe"]
_BOILERPLATE_HINTS = re.compile(r"cookie|consent|gdpr|banner|breadcrumb|sidebar|menu|navbar", re.IGNORECASE)

# Vocabulary that marks a repeated DOM block as a listing card rather than
# some other repeated widget (tag clouds, related links, …).
_LISTING_KEYWORDS = re.compile(
    r"phd|doctoral|doctorate|postdoc|fellowship|position|vacancy|deadline|apply|"
    r"scholarship|studentship|research|university|thèse|doctorat|promotion",
    re.IGNORECASE,
)
MIN_REPEATED_BLOCKS = 3  # fewer repeats than this isn't a listing grid


# ----------------------------- nodes -----------------------------------


def _strip_html(html: str) -> str:
    soup = _clean_soup(html)
    if soup is not None:
        return soup.get_text("\n", strip=True)
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


async def fetch_and_strip_page(
    url: str, *, user_agent: str, playwright_enabled: bool = True
) -> str:
    """Fetch one page (simple HTTP, Playwright fallback if it looks like a
    JS shell) and return its stripped plain text. Reuses the exact same
    fetch/detect logic as the list-page crawl, for one-off detail-page
    fetches (see worker/pipeline/ingest/detail_fetch.py)."""

    state = await fetch_simple({"current_url": url}, user_agent=user_agent)
    if playwright_enabled and needs_playwright({**state, "playwright_enabled": playwright_enabled}) == "playwright":
        state = await fetch_playwright(state)
    return _strip_html(state.get("html") or "")


def _clean_soup(html: str):
    """Parse + drop boilerplate. Returns a BeautifulSoup or None without bs4."""
    try:
        from bs4 import BeautifulSoup  # lazy
    except ImportError:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_BOILERPLATE_TAGS):
        tag.decompose()
    for tag in soup.find_all(attrs={"class": _BOILERPLATE_HINTS}):
        tag.decompose()
    for tag in soup.find_all(id=_BOILERPLATE_HINTS):
        tag.decompose()
    return soup


def _find_listing_blocks(html: str, base_url: str) -> list[str]:
    """Structure-aware candidate detection: a listings page renders its items
    as REPEATED sibling elements sharing one tag+class signature (the "card").
    Group elements by that signature, pick the group that repeats enough and
    talks about positions/deadlines, and return one text block per card with
    its primary link resolved to an absolute URL.

    This beats feeding stripped page text to the LLM on two counts: the LLM
    only ever sees listing content (no pagination-blind truncation), and the
    card's real href survives — plain text-stripping deletes every link, so
    application_url could previously only come from URLs typed in the visible
    text.
    """
    soup = _clean_soup(html)
    if soup is None:
        return []

    base_path = urlparse(base_url).path.rstrip("/")

    def _primary_href(el: Any) -> Optional[str]:
        if el.name == "a" and el.get("href"):
            return el["href"]
        anchors = el.find_all("a", href=True)
        return max(anchors, key=lambda a: len(a.get_text(strip=True)))["href"] if anchors else None

    def _is_same_page_link(href: Optional[str]) -> bool:
        # A facet/filter control (e.g. EURAXESS's "?f[0]=job_is_eu_founded:5824")
        # points back at the SAME listing page with a different query string —
        # it is never itself a listing. A real card's link always resolves to
        # a different path (its own detail page or an external application URL).
        if not href:
            return False
        resolved_path = urlparse(urljoin(base_url, href)).path.rstrip("/")
        return resolved_path == base_path

    groups: dict[str, list[Any]] = {}
    for el in soup.find_all(True):
        if el.name in ("html", "body"):
            continue
        has_link = bool(el.get("href")) if el.name == "a" else el.find("a", href=True) is not None
        if not has_link:
            continue
        text = el.get_text(" ", strip=True)
        if not (40 <= len(text) <= 4000):
            continue
        parent = el.parent.name if el.parent else ""
        classes = ".".join(sorted(el.get("class") or []))
        groups.setdefault(f"{parent}>{el.name}.{classes}", []).append(el)

    best: list[Any] = []
    best_score = 0.0
    for els in groups.values():
        if len(els) < MIN_REPEATED_BLOCKS:
            continue
        # Reject groups whose links mostly just re-filter the current page
        # (faceted-search sidebars, tag clouds) — see _is_same_page_link.
        same_page_hits = sum(1 for e in els if _is_same_page_link(_primary_href(e)))
        if same_page_hits > len(els) / 2:
            continue
        sample = " ".join(e.get_text(" ", strip=True)[:300] for e in els[:5])
        keyword_hits = len(_LISTING_KEYWORDS.findall(sample))
        if keyword_hits == 0:
            continue  # repeated, but not about positions — tag clouds etc.
        score = len(els) + 2.0 * keyword_hits
        if score > best_score:
            best, best_score = els, score

    blocks: list[str] = []
    for el in best:
        text = el.get_text("\n", strip=True)
        if el.name == "a" and el.get("href"):
            href = el["href"]
        else:
            anchors = el.find_all("a", href=True)
            # the title link is almost always the one with the longest text
            href = max(anchors, key=lambda a: len(a.get_text(strip=True)))["href"] if anchors else None
        if href:
            blocks.append(f"LINK: {urljoin(base_url, href)}\n{text}")
        else:
            blocks.append(text)
    return blocks


def _pack_blocks(blocks: list[str]) -> list[list[str]]:
    """Greedily group card blocks into LLM calls of ≤ CHUNK_CHARS. Blocks are
    never split mid-card, so no listing straddles two calls. Returns the
    GROUPS (not joined strings) so the caller can map the LLM's answers back
    to their source blocks."""
    groups: list[list[str]] = []
    current: list[str] = []
    size = 0
    for block in blocks:
        block = block[:CHUNK_CHARS]
        if current and size + len(block) > CHUNK_CHARS:
            groups.append(current)
            current, size = [], 0
        current.append(block)
        size += len(block) + 20
    if current:
        groups.append(current)
    return groups


def _join_blocks(group: list[str]) -> str:
    return "\n\n=== LISTING ===\n\n".join(group)


def _backfill_from_block(listing: ExtractedListing, block: str, source_url: str) -> ExtractedListing:
    """The DOM gave us each card's link and text — the LLM is not allowed to
    lose them. A null title or an application_url that fell back to the
    search-page URL is repaired from the card block itself. (Null titles +
    everything sharing the source URL is what made whole runs dedupe into
    a handful of 'None' rows and then die in the prefilter.)"""
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    link: Optional[str] = None
    if lines and lines[0].startswith("LINK: "):
        link = lines[0][len("LINK: "):].strip()
        lines = lines[1:]
    if not listing.title and lines:
        listing.title = lines[0][:200]
    if link and (not listing.application_url or listing.application_url == source_url):
        listing.application_url = link
    return listing


def _chunk_text(text: str) -> list[str]:
    if len(text) <= CHUNK_CHARS:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text) and len(chunks) < MAX_CHUNKS_PER_PAGE:
        chunks.append(text[start : start + CHUNK_CHARS])
        start += CHUNK_CHARS - CHUNK_OVERLAP
    return chunks


def _listing_key(listing: ExtractedListing) -> tuple[str, str]:
    """In-run identity of a listing: normalized (title, application_url)."""
    return ((listing.title or "").strip().lower(), (listing.application_url or "").strip().lower())


def _dedupe_listings(listings: list[ExtractedListing]) -> list[ExtractedListing]:
    """Chunk overlap (and sloppy pages) produce duplicates — keep the first
    occurrence of each (title, application_url) identity."""
    seen: set[tuple[str, str]] = set()
    out: list[ExtractedListing] = []
    for item in listings:
        key = _listing_key(item)
        if key == ("", "") or key not in seen:
            seen.add(key)
            out.append(item)
    return out


async def extract_listings(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    attempts = state.get("attempt", 0) + 1
    # A failed Playwright escalation leaves the HTML unchanged — re-running
    # the LLM on identical text can only give the same answer, so skip it.
    if attempts > 1 and state.get("rendering") == "playwright_failed":
        return {**state, "attempt": attempts}

    html = state.get("html") or ""

    # Structure first: find the page's repeated listing-card elements and
    # send exactly those (with their hrefs) to the LLM. Fall back to
    # chunked full-page text when the page has no detectable card grid.
    source_url = state["current_url"]
    blocks = _find_listing_blocks(html, source_url)
    groups: list[list[str]] = []
    if len(blocks) >= MIN_REPEATED_BLOCKS:
        mode = "structured"
        text_chars = sum(len(b) for b in blocks)
        groups = _pack_blocks(blocks)
        chunks = [_join_blocks(g) for g in groups]
    else:
        mode = "text"
        text = _strip_html(html)
        text_chars = len(text)
        chunks = _chunk_text(text)
        if text_chars > CHUNK_CHARS * MAX_CHUNKS_PER_PAGE:
            log.warning(
                "extract_listings: page text is %d chars — only the first %d chunk(s) are scanned",
                text_chars, MAX_CHUNKS_PER_PAGE,
            )
    log.info(
        "extract_listings attempt=%s mode=%s blocks=%d chars=%d chunks=%d",
        attempts, mode, len(blocks), text_chars, len(chunks),
    )

    listings: list[ExtractedListing] = []
    error: Optional[str] = None
    for i, chunk in enumerate(chunks):
        try:
            chunk_listings = llm.extract_listings_from_html(chunk, source_url)
        except Exception as exc:
            # One bad chunk must not sink the listings already extracted
            # from the other chunks.
            log.warning("extract_listings: chunk %d/%d failed: %s", i + 1, len(chunks), exc)
            error = str(exc)
            continue
        # Structured mode: when the model answered one listing per card (the
        # prompt demands it), repair any titles/links it dropped from the
        # authoritative DOM blocks.
        if mode == "structured" and len(chunk_listings) == len(groups[i]):
            chunk_listings = [
                _backfill_from_block(listing, block, source_url)
                for listing, block in zip(chunk_listings, groups[i])
            ]
        listings.extend(chunk_listings)
    listings = _dedupe_listings(listings)

    diagnostics = list(state.get("diagnostics") or [])
    diagnostics.append(
        {
            "page": state.get("page", 1),
            "url": state["current_url"],
            "rendering": state.get("rendering", "simple"),
            "mode": mode,
            "card_blocks": len(blocks),
            "text_chars": text_chars,
            "chunks": len(chunks),
            "listings": len(listings),
            **({"error": error} if error else {}),
        }
    )
    return {**state, "attempt": attempts, "listings": listings, "error": error, "diagnostics": diagnostics}


def extraction_valid(state: dict[str, Any]) -> str:
    """Zero listings from a simple fetch usually means a JS-rendered page
    that slipped past the shell heuristic — escalate to Playwright once
    (new content) instead of re-running the LLM on identical text."""
    if state.get("listings"):
        return "ok"
    if (
        state.get("rendering") == "simple"
        and state.get("playwright_enabled", True)
        and state.get("attempt", 0) < MAX_EXTRACTION_RETRIES
    ):
        return "escalate"
    return "ok"  # give up, treat as page-done


_PAGE_PARAM = re.compile(r"([?&])(page|p|pg)=(\d+)", re.IGNORECASE)


def _increment_page_param(url: str) -> Optional[str]:
    """AGENT.md §3.2 strategy 1: a page=/p= cursor in the input URL is a pure
    increment — no DOM inspection, no LLM (the EURAXESS case)."""
    match = _PAGE_PARAM.search(url)
    if not match:
        return None
    return url[: match.start(3)] + str(int(match.group(3)) + 1) + url[match.end(3) :]


def _find_next_link(html: str, base_url: str) -> Optional[str]:
    """DOM 'next page' link detection — conservative, only anchors whose
    text/rel/class clearly mean pagination."""
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
                return urljoin(base_url, href)
    except ImportError:
        match = re.search(r'href="([^"]+)"[^>]*>\s*(?:Next|next|next page)', html)
        if match:
            return urljoin(base_url, match.group(1))
    return None


def check_pagination(state: dict[str, Any]) -> dict[str, Any]:
    """Next-page cursor with hard stop conditions (AGENT.md §3.2).
    Strategy order: URL page-param increment → DOM 'next' detection.

    `stop_reason` records WHY there's no next_url (or why we're pausing
    despite one existing), so the end of a run is never silent:
    - "no_results"    this page had nothing (results ran out)
    - "loop_detected" the site started repeating already-seen listings
    - "exhausted"     no next-page link/param found — genuinely done
    - "page_limit"    hit the per-run page ceiling, but a next page exists —
                       this now PAUSES for confirmation instead of dead-ending,
                       so a large site is never silently cut off.
    """
    html = state.get("html") or ""
    page = state.get("page", 1)

    # Stop: a page that yields nothing means the results ran out (or the
    # site is stonewalling) — following "next" would burn budget blindly.
    current = list(state.get("listings") or [])
    if not current:
        return {**state, "next_url": None, "stop_reason": "no_results"}

    # Loop guard: some boards serve the last page forever. If ≥95% of this
    # page's listings were already seen on earlier pages, stop.
    all_listings = list(state.get("all_listings") or [])
    prev = all_listings[: len(all_listings) - len(current)]
    if prev:
        prev_keys = {_listing_key(lst) for lst in prev}
        overlap = sum(1 for lst in current if _listing_key(lst) in prev_keys)
        if overlap / len(current) >= 0.95:
            log.info("check_pagination: page %d is ≥95%% repeats — loop guard stop", page)
            return {**state, "next_url": None, "stop_reason": "loop_detected"}

    next_url = _increment_page_param(state["current_url"]) or _find_next_link(html, state["current_url"])
    if not next_url:
        return {**state, "next_url": None, "stop_reason": "exhausted"}

    if page >= state.get("max_pages", 10):
        return {**state, "next_url": next_url, "stop_reason": "page_limit"}

    return {**state, "next_url": next_url, "stop_reason": None}


# ----------------------------- runner ----------------------------------


async def _run_without_langgraph(
    initial: dict[str, Any], *, llm: LLMClient, user_agent: str
) -> dict[str, Any]:
    state = initial
    while True:
        state = await fetch_simple(state, user_agent=user_agent)
        if needs_playwright(state) == "playwright":
            state = await fetch_playwright(state)

        state = await extract_listings(state, llm=llm)
        while extraction_valid(state) == "escalate":
            state = await fetch_playwright(state)
            state = await extract_listings(state, llm=llm)

        state["all_listings"] = state.get("all_listings", []) + list(state.get("listings") or [])

        state = check_pagination(state)
        next_url = state.get("next_url")
        if not next_url:
            state["needs_continue_prompt"] = False
            break

        pause_after = state.get("pause_after_pages")
        page = state.get("page", 1)
        # Reaching the periodic checkpoint OR the hard page-count ceiling
        # both pause for confirmation — neither should silently end the run
        # when more pages genuinely exist.
        if (pause_after and page >= pause_after) or state.get("stop_reason") == "page_limit":
            state["needs_continue_prompt"] = True
            state["next_url"] = next_url
            break

        state["current_url"] = next_url
        state["page"] = page + 1
        state["attempt"] = 0

    return state


def serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    """JSON-safe snapshot of a paused run — enough to resume from."""

    return {
        "url": state.get("url"),
        "current_url": state.get("next_url") or state.get("current_url"),
        "page": (state.get("page", 1) + 1) if state.get("next_url") else state.get("page", 1),
        "attempt": 0,
        "all_listings": [asdict(x) for x in state.get("all_listings", [])],
        "max_pages": state.get("max_pages", 10),
        "playwright_enabled": state.get("playwright_enabled", True),
    }


def deserialize_state(resume_state: dict[str, Any]) -> dict[str, Any]:
    listings = [ExtractedListing(**d) for d in resume_state.get("all_listings", [])]
    return {
        "url": resume_state.get("url"),
        "current_url": resume_state.get("current_url"),
        "html": None,
        "listings": [],
        "all_listings": listings,
        "attempt": 0,
        "page": resume_state.get("page", 1),
        "max_pages": resume_state.get("max_pages", 10),
        "error": None,
        "rendering": "simple",
        "playwright_enabled": resume_state.get("playwright_enabled", True),
    }


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
        next_url = out.get("next_url")
        if not next_url:
            return {**out, "needs_continue_prompt": False}

        pause_after = out.get("pause_after_pages")
        page = out.get("page", 1)
        # Reaching the periodic checkpoint OR the hard page-count ceiling
        # both pause for confirmation — neither should silently end the run
        # when more pages genuinely exist.
        if (pause_after and page >= pause_after) or out.get("stop_reason") == "page_limit":
            return {**out, "needs_continue_prompt": True}

        return {**out, "current_url": next_url, "page": page + 1, "attempt": 0}

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
        "escalate": "fetch_playwright",
        "ok": "accumulate",
    })
    g.add_edge("accumulate", "pagination")
    g.add_conditional_edges(
        "pagination",
        lambda s: "end" if not s.get("next_url") or s.get("needs_continue_prompt") else "next",
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
    pause_after_pages: Optional[int] = None,
    resume_state: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Returns {"listings": [...], "paused": bool, "resume_state": dict|None}.

    `pause_after_pages` implements the Phase 04 human-in-the-loop pagination
    checkpoint: after that many pages, stop and hand back a JSON-serializable
    `resume_state` instead of continuing silently. Pass it back in via
    `resume_state` to pick up where the run left off.
    """

    if resume_state is not None:
        initial = deserialize_state(resume_state)
        initial["pause_after_pages"] = (pause_after_pages or 0) + resume_state.get("page", 1) - 1
    else:
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
            "pause_after_pages": pause_after_pages,
        }

    graph = _build_langgraph(llm, user_agent)
    if graph is not None:
        final = await graph.ainvoke(initial)
    else:
        log.info("langgraph not installed — using sequential runner")
        final = await _run_without_langgraph(initial, llm=llm, user_agent=user_agent)

    paused = bool(final.get("needs_continue_prompt"))
    return {
        "listings": _dedupe_listings(list(final.get("all_listings") or [])),
        "paused": paused,
        "resume_state": serialize_state(final) if paused else None,
        "pages_processed": final.get("page", 1),
        "diagnostics": list(final.get("diagnostics") or []),
        # Why the run stopped/paused here — None only for very old code paths;
        # always set by check_pagination now. See its docstring for values.
        "stop_reason": final.get("stop_reason"),
    }
