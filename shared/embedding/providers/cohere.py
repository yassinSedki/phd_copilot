"""Cohere embedding provider — factory guide §11.

LRU cache uses `OrderedDict` so the same text in the same role doesn't
re-hit the API. Cache key includes model + input_type so a query embedding
and a document embedding of the same text are stored separately (Cohere's
embed-english-v3 is asymmetric — `search_query` and `search_document` are
trained as different encoders).

`embed_batch` only calls the API for texts that aren't cached.
"""

from __future__ import annotations

from collections import OrderedDict

from shared.embedding.base import EmbeddingProvider
from shared.llm.errors import LLMError, LLMErrorCode


def _translate(exc: Exception) -> LLMError:
    name = exc.__class__.__name__.lower()
    msg = str(exc)
    if "toomanyrequests" in name or "ratelimit" in name or "429" in msg:
        return LLMError(LLMErrorCode.RATE_LIMIT, msg)
    if "timeout" in name:
        return LLMError(LLMErrorCode.TIMEOUT, msg)
    if "unauthorized" in name or "401" in msg or "invalid api key" in msg.lower():
        return LLMError(LLMErrorCode.AUTH, msg)
    return LLMError(LLMErrorCode.PROVIDER_ERROR, msg)


_DIM_BY_MODEL = {
    "embed-english-v3.0": 1024,
    "embed-multilingual-v3.0": 1024,
    "embed-english-light-v3.0": 384,
    "embed-multilingual-light-v3.0": 384,
}


class CohereEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings) -> None:
        api_key = getattr(settings, "api_key", "") or ""
        if not api_key:
            raise LLMError(LLMErrorCode.AUTH, "EMBEDDING__API_KEY / COHERE_API_KEY is not set.")

        try:
            import cohere  # lazy
        except ImportError as exc:
            raise LLMError(
                LLMErrorCode.PROVIDER_ERROR,
                "cohere SDK is not installed. `poetry add cohere`.",
            ) from exc

        self._model = getattr(settings, "model", "embed-english-v3.0") or "embed-english-v3.0"
        self._dim = _DIM_BY_MODEL.get(self._model, int(getattr(settings, "dim", 1024)))
        self._batch_limit = int(getattr(settings, "batch_size", 96))
        cache_size = int(getattr(settings, "cache_size", 1000))

        self._client = cohere.AsyncClientV2(api_key=api_key)
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._cache_max = cache_size

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dim(self) -> int:
        return self._dim

    # ---- LRU cache helpers

    def _cache_key(self, text: str, input_type: str) -> str:
        return f"{self._model}:{input_type}:{text}"

    def _cache_get(self, key: str):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def _cache_set(self, key: str, value: list[float]) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)

    # ---- public

    async def embed(self, text: str, *, input_type: str = "search_query") -> list[float]:
        key = self._cache_key(text, input_type)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        try:
            response = await self._client.embed(
                texts=[text],
                model=self._model,
                input_type=input_type,
                embedding_types=["float"],
            )
        except Exception as exc:
            raise _translate(exc) from exc
        vec = response.embeddings.float_[0]
        self._cache_set(key, vec)
        return vec

    async def embed_batch(
        self, texts: list[str], *, input_type: str = "search_document"
    ) -> list[list[float]]:
        if not texts:
            return []
        keys = [self._cache_key(t, input_type) for t in texts]
        results: list[list[float] | None] = [self._cache_get(k) for k in keys]
        missing = [i for i, r in enumerate(results) if r is None]
        if not missing:
            return results  # type: ignore[return-value]

        # Cohere's API batch limit is 96 per call.
        for chunk_start in range(0, len(missing), self._batch_limit):
            chunk_idx = missing[chunk_start : chunk_start + self._batch_limit]
            chunk_texts = [texts[i] for i in chunk_idx]
            try:
                response = await self._client.embed(
                    texts=chunk_texts,
                    model=self._model,
                    input_type=input_type,
                    embedding_types=["float"],
                )
            except Exception as exc:
                raise _translate(exc) from exc
            for idx, vec in zip(chunk_idx, response.embeddings.float_):
                results[idx] = vec
                self._cache_set(keys[idx], vec)
        return results  # type: ignore[return-value]
