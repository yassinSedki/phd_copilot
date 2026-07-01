"""Deterministic stub embedding provider. No SDK, no network. Same text →
same vector. Used for offline dev + tests."""

from __future__ import annotations

import hashlib
import math
import struct

from shared.embedding.base import EmbeddingProvider


def _hash_to_vector(text: str, dim: int) -> list[float]:
    """SHA-256 the text, expand into a unit-normalised vector of length `dim`."""

    out: list[float] = []
    seed = text.encode("utf-8")
    counter = 0
    while len(out) < dim:
        h = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        # 32 bytes → 8 floats
        for i in range(0, 32, 4):
            (val,) = struct.unpack(">I", h[i : i + 4])
            # Map to [-1, 1]
            out.append((val / 0x7FFFFFFF) - 1.0)
            if len(out) >= dim:
                break
        counter += 1
    norm = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / norm for x in out]


class StubEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings) -> None:
        self._model = getattr(settings, "model", "stub-embed")
        self._dim = int(getattr(settings, "dim", 384))

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dim(self) -> int:
        return self._dim

    async def embed(self, text: str, *, input_type: str = "search_query") -> list[float]:
        return _hash_to_vector(f"{input_type}:{text}", self._dim)
