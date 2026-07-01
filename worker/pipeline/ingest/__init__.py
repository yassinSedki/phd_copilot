"""Ingest layer.

The PRIMARY entry point is `run_scraper_graph(url, llm)` from `scraper_graph`:
a LangGraph agent that fetches any listing URL, falls back to Playwright on
JS-shell pages, LLM-extracts listings, validates, and paginates. See
`scraper_graph.py` docstring for the node diagram.

The old fixture / EURAXESS classes remain for tests and offline dev only.
"""

from worker.pipeline.ingest.base import RawListing, Scraper
from worker.pipeline.ingest.fixture import FixtureScraper
from worker.pipeline.ingest.scraper_graph import run_scraper_graph

__all__ = [
    "RawListing",
    "Scraper",
    "FixtureScraper",
    "run_scraper_graph",
]
