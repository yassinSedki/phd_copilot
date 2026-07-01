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

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin

from shared.llm import LLMClient, ResearchSummary
from shared.llm.prompts import (
    extract_research_info as extract_prompt,
    find_lab_url as lab_url_prompt,
    find_publications as pubs_prompt,
    identify_overlap as overlap_prompt,
)

log = logging.getLogger("phd_copilot.deepdive")

MAX_QUALITY_RETRIES = 2


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
        return re.sub(r"<[^>]+>", " ", text)


async def find_lab_url(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    """Ask the LLM to guess the lab URL from name + institution. Real
    web search hookup happens here in production (Tavily/DuckDuckGo/etc).
    For now: prompt-only — Claude often knows public lab URLs from training.
    """
    if state.get("lab_url"):
        return state
    try:
        out = llm.invoke(
            [
                {"role": "system", "content": lab_url_prompt.SYSTEM},
                {"role": "user", "content": lab_url_prompt.build_user(state["professor_name"], state.get("institution"))},
            ],
            json_mode=True,
        )
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {}
        return {**state, "lab_url": data.get("lab_url")}
    except Exception as exc:
        log.warning("find_lab_url failed: %s", exc)
        return {**state, "lab_url": None}


async def fetch_lab_page(state: dict[str, Any], *, user_agent: str) -> dict[str, Any]:
    url = state.get("lab_url")
    if not url:
        return {**state, "lab_html": ""}
    try:
        import httpx  # lazy

        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15.0, headers={"User-Agent": user_agent}
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return {**state, "lab_html": resp.text}
    except Exception as exc:
        log.warning("fetch_lab_page failed: %s", exc)
        return {**state, "lab_html": ""}


async def extract_research_info(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    page_text = _strip_html(state.get("lab_html") or "")[:8000]
    if not page_text:
        # Fall back to a topic-only summary.
        summary = llm.research_lab(
            state["professor_name"], state.get("institution"), state.get("topic")
        )
        return {
            **state,
            "research_topics": [summary.summary],
            "summary_text": summary.summary,
        }
    try:
        out = llm.invoke(
            [
                {"role": "system", "content": extract_prompt.SYSTEM},
                {"role": "user", "content": extract_prompt.build_user(state["professor_name"], page_text)},
            ],
            json_mode=True,
        )
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {}
    except Exception as exc:
        log.warning("extract_research_info failed: %s", exc)
        data = {}
    topics = data.get("topics") or []
    return {**state, "research_topics": topics, "summary_text": " · ".join(topics[:5])}


async def find_publications(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    """Pull 2-3 recent paper titles from the lab page text + LLM. Production
    swaps this for a Semantic Scholar / OpenAlex API call.
    """
    text = _strip_html(state.get("lab_html") or "")
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
        out = llm.invoke(
            [
                {"role": "system", "content": pubs_prompt.SYSTEM},
                {"role": "user", "content": pubs_prompt.build_user(candidates)},
            ],
            json_mode=True,
        )
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {}
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
        out = llm.invoke(
            [
                {"role": "system", "content": overlap_prompt.SYSTEM},
                {
                    "role": "user",
                    "content": overlap_prompt.build_user(
                        state["professor_name"],
                        state.get("research_topics") or [],
                        state.get("publications") or [],
                        profile,
                    ),
                },
            ],
            json_mode=True,
        )
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {}
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


def draft_email(state: dict[str, Any], *, llm: LLMClient) -> dict[str, Any]:
    summary = _build_research_summary(state)
    draft = llm.draft_outreach_email(state.get("user_profile") or {}, summary)
    return {
        **state,
        "email_subject": draft.subject,
        "email_draft": draft.body,
    }


def check_quality(state: dict[str, Any]) -> dict[str, Any]:
    """Heuristic: does the draft mention at least one publication title or
    overlap term? If not, flag as generic and retry."""
    body = (state.get("email_draft") or "").lower()
    if not body:
        return {**state, "quality": "generic"}
    needles = [n.lower() for n in (state.get("publications") or []) + (state.get("overlap_points") or [])]
    found = any(n[:30] in body for n in needles if n)
    return {**state, "quality": "specific" if found else "generic"}


def quality_router(state: dict[str, Any]) -> str:
    if state.get("quality") == "specific":
        return "end"
    if state.get("attempts", 0) < MAX_QUALITY_RETRIES:
        return "retry"
    return "end"


# ----------------------------- runner ----------------------------------


def _build_langgraph(llm: LLMClient, user_agent: str):
    try:
        from langgraph.graph import END, StateGraph  # lazy
    except ImportError:
        return None

    async def _find(s):
        return await find_lab_url(s, llm=llm)

    async def _fetch(s):
        return await fetch_lab_page(s, user_agent=user_agent)

    async def _extract(s):
        return await extract_research_info(s, llm=llm)

    async def _pubs(s):
        return await find_publications(s, llm=llm)

    def _abstracts(s):
        return fetch_abstracts(s)

    async def _overlap(s):
        out = await identify_overlap(s, llm=llm)
        return {**out, "attempts": out.get("attempts", 0) + 1}

    def _draft(s):
        return draft_email(s, llm=llm)

    def _quality(s):
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


async def _run_sequential(initial: dict[str, Any], llm: LLMClient, user_agent: str) -> dict[str, Any]:
    state = await find_lab_url(initial, llm=llm)
    state = await fetch_lab_page(state, user_agent=user_agent)
    state = await extract_research_info(state, llm=llm)
    state = await find_publications(state, llm=llm)
    state = fetch_abstracts(state)
    for _ in range(MAX_QUALITY_RETRIES + 1):
        state = await identify_overlap(state, llm=llm)
        state["attempts"] = state.get("attempts", 0) + 1
        state = draft_email(state, llm=llm)
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
) -> dict[str, Any]:
    initial = {
        "professor_name": professor_name,
        "institution": institution,
        "topic": topic,
        "lab_url": lab_url,
        "user_profile": user_profile,
        "lab_html": "",
        "research_topics": [],
        "publications": [],
        "overlap_points": [],
        "summary_text": "",
        "email_subject": None,
        "email_draft": None,
        "quality": None,
        "attempts": 0,
    }

    graph = _build_langgraph(llm, user_agent)
    if graph is not None:
        return await graph.ainvoke(initial)
    return await _run_sequential(initial, llm, user_agent)
