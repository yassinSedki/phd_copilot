"""Embedding factory. Mirror of shared.llm but simpler — embeddings have
no roles, just queries vs documents (input_type).

Usage:

    from shared.embedding import get_embedding_provider

    provider = get_embedding_provider()
    vec = await provider.embed("what is X?", input_type="search_query")
    docs = await provider.embed_batch(["doc 1", "doc 2"])
"""

from shared.embedding.base import EmbeddingProvider
from shared.embedding.factory import get_embedding_provider, reset_embedding_provider

__all__ = ["EmbeddingProvider", "get_embedding_provider", "reset_embedding_provider"]
