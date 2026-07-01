from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class RawListing:
    source: str
    source_key: str
    url: Optional[str]
    raw_text: str


class Scraper(Protocol):
    source: str

    def fetch(self) -> Iterator[RawListing]: ...
