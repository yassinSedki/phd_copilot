"""Deep Dive research agent as a LangGraph StateGraph.

Spec: phd copilot.md → "Agent 2 — Deep Dive Research Agent".

  find_lab_url -> fetch_lab_page -> extract_research_info ->
  find_publications -> fetch_abstracts -> identify_overlap ->
  draft_email -> check_quality
                    │
                    ├── specific → END
                    └── generic  → identify_overlap (≤2 retries)

Hard rules (phd copilot.md §"Hard rules"):
- Never store an email automatically — user supplies it manually.
- Output is always a draft — user reviews + sends from their own client.
- Max 2 retry loops on quality check.

Like the scraper graph this falls back to a sequential async runner when
langgraph isn't installed. Public entry point:

    run_deep_dive_graph(prof, institution, topic, profile, llm) -> dict
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Callable, Optional

from shared.llm import LLMClient, ResearchSummary
from shared.llm.jsonx import extract_json_object
from shared.llm.prompts import (
    extract_research_info as extract_prompt,
    find_lab_url as lab_url_prompt,
    find_publications as pubs_prompt,
    identify_overlap as overlap_prompt,
)
from worker.pipeline.ingest.scraper_graph import fetch_and_strip_page

log = logging.getLogger("phd_copilot.deepdive")

MAX_QUALITY_RETRIES = 2


# ----------------------------- nodes -----------------------------------


async def _invoke_json(llm: LLMClient, system: str, user: str) -> dict[str, Any]:
    """One helper for every node: blocking provider call off the event loop,
    fenced/chatty output handled by the shared parser (bare json.loads used
    to silently turn ```json replies into {} → generic emails)."""
    out = await asyncio.to_thread(
        llm.invoke,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        json_mode=True,
    )
    return extract_json_object(out)


async def find_lab_url(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    """Ask the LLM to guess the lab URL from name + institution. Real
    web search hookup happens here in production (Tavily/DuckDuckGo/etc).
    For now: prompt-only — Claude often knows public lab URLs from training.
    """
    if state.get("lab_url"):
        return state
    try:
        data = await _invoke_json(
            llm, lab_url_prompt.SYSTEM, lab_url_prompt.build_user(state["professor_name"], state.get("institution"))
        )
        return {**state, "lab_url": data.get("lab_url")}
    except Exception as exc:
        log.warning("find_lab_url failed: %s", exc)
        return {**state, "lab_url": None}


def _page_mentions_professor(text: str, professor_name: str) -> bool:
    """The lab URL comes from LLM memory and can be hallucinated or stale —
    a page that never mentions the professor's surname is almost certainly
    the wrong page, and researching it would produce an email about someone
    else's lab. Surname check: cheap, language-agnostic enough."""
    words = [w.strip(".,") for w in professor_name.split() if len(w.strip(".,")) >= 3]
    if not words:
        return True  # nothing to verify against — don't block
    surname = words[-1].lower()
    return surname in text.lower()


async def fetch_lab_page(state: dict[str, Any], *, user_agent: str) -> dict[str, Any]:
    """Reuses the scraper's fetch (incl. the Playwright JS-shell fallback the
    old hand-rolled httpx fetch here lacked) and stores stripped text once.
    A fetched page that doesn't mention the professor is DISCARDED — wrong
    input is worse than no input here."""
    url = state.get("lab_url")
    if not url:
        return {**state, "lab_text": ""}
    try:
        text = await fetch_and_strip_page(url, user_agent=user_agent)
    except Exception as exc:
        log.warning("fetch_lab_page failed: %s", exc)
        return {**state, "lab_text": ""}

    # Only verify LLM-guessed URLs; a URL the user typed is trusted as-is.
    if text and not state.get("lab_url_from_user") and not _page_mentions_professor(text, state["professor_name"]):
        log.warning(
            "fetch_lab_page: %s never mentions %r — likely a hallucinated/stale URL, discarding",
            url, state["professor_name"],
        )
        return {**state, "lab_text": "", "lab_url": None}
    return {**state, "lab_text": text}


async def extract_research_info(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    page_text = (state.get("lab_text") or "")[:8000]
    if not page_text:
        # HONEST fallback: no verified page means no research. The old path
        # called llm.research_lab here, which returned canned stub text that
        # then flowed into the stored summary and the email as if it were
        # real. Empty is recoverable; fabricated is not.
        log.info("extract_research_info: no lab page — proceeding without research context")
        return {**state, "research_topics": [], "summary_text": ""}
    try:
        data = await _invoke_json(
            llm, extract_prompt.SYSTEM, extract_prompt.build_user(state["professor_name"], page_text)
        )
    except Exception as exc:
        log.warning("extract_research_info failed: %s", exc)
        data = {}
    topics = data.get("topics") or []
    return {**state, "research_topics": topics, "summary_text": " · ".join(topics[:5])}


async def find_publications(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    """Pull 2-3 recent paper titles from the lab page text + LLM. Production
    swaps this for a Semantic Scholar / OpenAlex API call.
    """
    text = state.get("lab_text") or ""
    # Cheap heuristic: lines that look like paper titles (Title Case + year).
    candidates = []
    for line in text.splitlines():
        line = line.strip()
        if 30 < len(line) < 200 and re.search(r"\b(19|20)\d{2}\b", line):
            candidates.append(line)
        if len(candidates) >= 6:
            break

    if not candidates:
        return {**state, "publications": []}

    try:
        data = await _invoke_json(llm, pubs_prompt.SYSTEM, pubs_prompt.build_user(candidates))
        pubs = [str(p) for p in (data.get("publications") or [])][:3]
    except Exception:
        pubs = candidates[:3]
    return {**state, "publications": pubs}


def fetch_abstracts(state: dict[str, Any]) -> dict[str, Any]:
    # In production: fetch + summarise each paper. For now the title itself
    # is the abstract proxy.
    return state


async def identify_overlap(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    """LLM matches the prof's work to the user's CV. Returns ≤3 concrete
    overlap points referencing the prof's actual topics / publications."""
    profile = state.get("user_profile") or {}
    try:
        data = await _invoke_json(
            llm,
            overlap_prompt.SYSTEM,
            overlap_prompt.build_user(
                state["professor_name"],
                state.get("research_topics") or [],
                state.get("publications") or [],
                profile,
                state.get("personal_note"),
            ),
        )
        overlaps = [str(o) for o in (data.get("overlaps") or [])][:3]
    except Exception as exc:
        log.warning("identify_overlap failed: %s", exc)
        overlaps = []
    return {**state, "overlap_points": overlaps}


def _build_research_summary(state: dict[str, Any]) -> ResearchSummary:
    return ResearchSummary(
        summary=state.get("summary_text") or "",
        overlaps=state.get("overlap_points") or [],
        recent_work=state.get("publications") or [],
        publications=state.get("publications") or [],
        lab_url=state.get("lab_url"),
        model_used="",
    )


async def draft_email(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    summary = _build_research_summary(state)

    # Retrying with IDENTICAL inputs at low temperature reproduces the same
    # generic draft — when the quality gate sent us back here, tell the
    # model what was wrong and what to cite.
    note = state.get("personal_note") or ""
    if state.get("quality") == "generic":
        citables = (state.get("publications") or []) + (state.get("overlap_points") or [])
        if citables:
            note = (
                (note + "\n\n" if note else "")
                + "REVISION: the previous draft was too generic. Explicitly mention at least one of these "
                + "by name: " + "; ".join(str(c) for c in citables[:4])
            )
        else:
            # Nothing real to cite — the previous attempt likely fabricated
            # a bracketed placeholder trying to comply anyway. Telling it
            # explicitly there is nothing to cite heads that off next round.
            note = (
                (note + "\n\n" if note else "")
                + "REVISION: the previous draft used a bracketed placeholder instead of a real citation. "
                + "No specific publication or overlap was found — do not invent one and do not use "
                + "placeholder brackets. Write a shorter, honest email grounded only in the general "
                + "research summary."
            )

    draft = await asyncio.to_thread(
        llm.draft_outreach_email, state.get("user_profile") or {}, summary, personal_note=note or None
    )
    return {
        **state,
        "email_subject": draft.subject,
        "email_draft": draft.body,
    }


_PLACEHOLDER_RE = re.compile(r"\[[^\]\n]{2,80}\]")


def check_quality(state: dict[str, Any]) -> dict[str, Any]:
    """Heuristic: does the draft mention at least one publication title or
    overlap term, AND is it free of unfilled placeholders? A model asked to
    "cite something specific" with nothing real to cite will sometimes
    fabricate a bracketed placeholder like "[paper title]" instead — that
    passes a naive citation check (it still mentions the topic) but must
    never reach the user as a final draft, so it's checked independently."""
    body = state.get("email_draft") or ""
    if not body:
        return {**state, "quality": "generic"}
    if _PLACEHOLDER_RE.search(body):
        return {**state, "quality": "generic"}
    lowered = body.lower()
    needles = [n.lower() for n in (state.get("publications") or []) + (state.get("overlap_points") or [])]
    found = any(n[:30] in lowered for n in needles if n)
    return {**state, "quality": "specific" if found else "generic"}


def quality_router(state: dict[str, Any]) -> str:
    if state.get("quality") == "specific":
        return "end"
    if state.get("attempts", 0) < MAX_QUALITY_RETRIES:
        return "retry"
    return "end"


# ----------------------------- runner ----------------------------------


# Human-readable step labels, streamed to the job's progress meta so the UI
# shows the agent's REAL process instead of a canned animation.
STEP_LABELS = {
    "find_lab_url": ("Finding the lab page", 25),
    "fetch_lab_page": ("Reading the lab page", 35),
    "extract_research_info": ("Extracting research themes", 50),
    "find_publications": ("Finding recent publications", 60),
    "identify_overlap": ("Identifying overlap with your profile", 70),
    "draft_email": ("Drafting the outreach email", 80),
    "check_quality": ("Checking the draft cites real work", 88),
}

StepCallback = Callable[[str, int], None]


def _notify(on_step: Optional[StepCallback], node: str) -> None:
    if on_step is None:
        return
    label, pct = STEP_LABELS[node]
    try:
        on_step(label, pct)
    except Exception:  # progress reporting must never kill the research
        log.debug("on_step callback failed", exc_info=True)


def _build_langgraph(llm: LLMClient, user_agent: str, on_step: Optional[StepCallback] = None):
    try:
        from langgraph.graph import END, StateGraph  # lazy
    except ImportError:
        return None

    async def _find(s):
        _notify(on_step, "find_lab_url")
        return await find_lab_url(s, llm=llm)

    async def _fetch(s):
        _notify(on_step, "fetch_lab_page")
        return await fetch_lab_page(s, user_agent=user_agent)

    async def _extract(s):
        _notify(on_step, "extract_research_info")
        return await extract_research_info(s, llm=llm)

    async def _pubs(s):
        _notify(on_step, "find_publications")
        return await find_publications(s, llm=llm)

    def _abstracts(s):
        return fetch_abstracts(s)

    async def _overlap(s):
        _notify(on_step, "identify_overlap")
        out = await identify_overlap(s, llm=llm)
        return {**out, "attempts": out.get("attempts", 0) + 1}

    async def _draft(s):
        _notify(on_step, "draft_email")
        return await draft_email(s, llm=llm)

    def _quality(s):
        _notify(on_step, "check_quality")
        return check_quality(s)

    g = StateGraph(dict)
    g.add_node("find_lab_url", _find)
    g.add_node("fetch_lab_page", _fetch)
    g.add_node("extract_research_info", _extract)
    g.add_node("find_publications", _pubs)
    g.add_node("fetch_abstracts", _abstracts)
    g.add_node("identify_overlap", _overlap)
    g.add_node("draft_email", _draft)
    g.add_node("check_quality", _quality)

    g.set_entry_point("find_lab_url")
    g.add_edge("find_lab_url", "fetch_lab_page")
    g.add_edge("fetch_lab_page", "extract_research_info")
    g.add_edge("extract_research_info", "find_publications")
    g.add_edge("find_publications", "fetch_abstracts")
    g.add_edge("fetch_abstracts", "identify_overlap")
    g.add_edge("identify_overlap", "draft_email")
    g.add_edge("draft_email", "check_quality")
    g.add_conditional_edges("check_quality", quality_router, {"retry": "identify_overlap", "end": END})
    return g.compile()


async def _run_sequential(
    initial: dict[str, Any], llm: LLMClient, user_agent: str, on_step: Optional[StepCallback] = None
) -> dict[str, Any]:
    _notify(on_step, "find_lab_url")
    state = await find_lab_url(initial, llm=llm)
    _notify(on_step, "fetch_lab_page")
    state = await fetch_lab_page(state, user_agent=user_agent)
    _notify(on_step, "extract_research_info")
    state = await extract_research_info(state, llm=llm)
    _notify(on_step, "find_publications")
    state = await find_publications(state, llm=llm)
    state = fetch_abstracts(state)
    for _ in range(MAX_QUALITY_RETRIES + 1):
        _notify(on_step, "identify_overlap")
        state = await identify_overlap(state, llm=llm)
        state["attempts"] = state.get("attempts", 0) + 1
        _notify(on_step, "draft_email")
        state = await draft_email(state, llm=llm)
        _notify(on_step, "check_quality")
        state = check_quality(state)
        if state.get("quality") == "specific":
            break
    return state


async def run_deep_dive_graph(
    *,
    professor_name: str,
    institution: Optional[str],
    topic: Optional[str],
    lab_url: Optional[str],
    user_profile: dict[str, Any],
    llm: LLMClient,
    user_agent: str = "phd-copilot/0.1",
    personal_note: Optional[str] = None,
    on_step: Optional[StepCallback] = None,
) -> dict[str, Any]:
    initial = {
        "professor_name": professor_name,
        "institution": institution,
        "topic": topic,
        "lab_url": lab_url,
        # A user-supplied URL is trusted; only LLM-guessed ones get the
        # mentions-the-professor verification.
        "lab_url_from_user": bool(lab_url),
        "user_profile": user_profile,
        "personal_note": personal_note,
        "lab_text": "",
        "research_topics": [],
        "publications": [],
        "overlap_points": [],
        "summary_text": "",
        "email_subject": None,
        "email_draft": None,
        "quality": None,
        "attempts": 0,
    }

    graph = _build_langgraph(llm, user_agent, on_step)
    if graph is not None:
        return await graph.ainvoke(initial)
    return await _run_sequential(initial, llm, user_agent, on_step)
