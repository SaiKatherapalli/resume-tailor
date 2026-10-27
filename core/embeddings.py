"""
Embeddings: text -> list of numbers that captures its meaning.

Runs locally with fastembed (no API key). We follow LangChain's `Embeddings`
interface, so it can be swapped for any other LangChain embeddings class later.
"""

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from core.config import get_settings


@lru_cache
def _load_model(name: str):
    """Load the model once (slow), then reuse it (fast)."""
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=name)


class LocalEmbeddings(Embeddings):
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or get_settings().embedding_model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """For the things we search IN (our bullets)."""
        model = _load_model(self.model_name)
        return [vector.tolist() for vector in model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        """For the thing we search FOR (the job's needs).
        bge models work better when queries get a special prefix; query_embed adds it."""
        model = _load_model(self.model_name)
        return next(iter(model.query_embed(text))).tolist()
