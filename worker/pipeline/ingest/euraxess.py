"""EURAXESS scraper. NOT YET IMPLEMENTED.

The Phase-0 spike (architecture doc, section 8 INGEST STEP 0) must be done
first: open euraxess.ec.europa.eu/jobs/search, DevTools -> Network, run a
search + paginate. If results arrive as JSON, implement Case A (httpx, loop
the page param). If as JS-rendered HTML, implement Case B (Playwright,
render each page). Save raw to storage/raw/ before parsing.

Until then, INGEST_SOURCE=fixture in .env keeps the pipeline runnable.
"""

from collections.abc import Iterator

from worker.pipeline.ingest.base import RawListing


class EuraxessScraper:
    source = "euraxess"

    def fetch(self) -> Iterator[RawListing]:
        raise NotImplementedError(
            "EURAXESS scraper not implemented yet. Do the Phase-0 DevTools spike "
            "and decide between Case A (JSON endpoint) and Case B (Playwright)."
        )
        yield  # pragma: no cover - keeps type-checkers happy
