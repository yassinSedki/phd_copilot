"""EmbeddingProvider ABC. Factory guide §11.

The interface is deliberately thin: embed one text, embed many. The base
class supplies a loop-based `embed_batch` so providers without native
batching get correct behaviour for free.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def dim(self) -> int:
        """Vector length. Used when sizing the vector store column."""

    @abstractmethod
    async def embed(self, text: str, *, input_type: str = "search_query") -> list[float]:
        ...

    async def embed_batch(
        self, texts: list[str], *, input_type: str = "search_document"
    ) -> list[list[float]]:
        """Default implementation loops over `embed`. Override for native
        batching (Cohere supports up to 96/call — see CohereEmbeddingProvider)."""

        return [await self.embed(t, input_type=input_type) for t in texts]
