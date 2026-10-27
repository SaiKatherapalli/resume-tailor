"""
Hybrid search over a user's bullets.

1. Cosine similarity -> good at MEANING   ("deploy apps" ~ "CI/CD pipelines")
2. BM25              -> good at EXACT WORDS ("Kafka", "DynamoDB", "C#")
3. Merge both rankings with Reciprocal Rank Fusion (RRF):
       score = 1/(60 + rank_in_cosine) + 1/(60 + rank_in_bm25)

No vector database: one user has ~100-300 bullets, numpy searches that in under 1 ms.
"""

import re

import numpy as np
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict
from rank_bm25 import BM25Okapi

from core.schemas import BulletChunk

RRF_K = 60  # standard value; bigger = ranks matter less
_WORD = re.compile(r"[a-z0-9][a-z0-9+#./-]*")


def tokenize(text: str) -> list[str]:
    """'Built Node.js APIs, C# and CI/CD.' -> ['built', 'node.js', 'apis', 'c#', 'and', 'ci/cd']"""
    return [w.rstrip(".,/-") for w in _WORD.findall(text.lower())]


class BulletIndex:
    """All bullets of ONE user, ready to search."""

    def __init__(self, chunks: list[BulletChunk], vectors: list[list[float]], embedder: Embeddings):
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        self.chunks = chunks
        self.embedder = embedder
        matrix = np.array(vectors, dtype=np.float32)
        # Normalize once, so later cosine similarity is just a dot product (fast).
        self.matrix = matrix / np.clip(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-9, None)
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks])

    @classmethod
    def build(cls, chunks: list[BulletChunk], embedder: Embeddings) -> "BulletIndex":
        """Embed all bullets and build the index."""
        return cls(chunks, embedder.embed_documents([c.text for c in chunks]), embedder)

    def search(self, query: str, k: int, experience_id: str | None = None) -> list[tuple[BulletChunk, float]]:
        """Top k bullets for the query. experience_id = only search inside one job."""
        allowed = [i for i, c in enumerate(self.chunks) if experience_id in (None, c.experience_id)]
        if not allowed:
            return []

        # 1. ranking by meaning (cosine)
        q = np.array(self.embedder.embed_query(query), dtype=np.float32)
        q /= max(float(np.linalg.norm(q)), 1e-9)
        cosine = self.matrix[allowed] @ q
        by_meaning = [allowed[i] for i in np.argsort(-cosine)]

        # 2. ranking by exact words (BM25)
        bm25 = self.bm25.get_scores(tokenize(query))
        by_words = sorted(allowed, key=lambda i: -bm25[i])

        # 3. merge (RRF)
        score: dict[int, float] = {}
        for ranking in (by_meaning, by_words):
            for rank, i in enumerate(ranking):
                score[i] = score.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)

        best = sorted(score, key=lambda i: -score[i])[:k]
        return [(self.chunks[i], score[i]) for i in best]


class BulletRetriever(BaseRetriever):
    """LangChain wrapper, so search works like every other LangChain block:
    retriever.invoke("kafka microservices") -> list[Document]
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: BulletIndex
    k: int = 5
    experience_id: str | None = None

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return [
            Document(
                page_content=chunk.text,
                metadata={"id": chunk.id, "experience_id": chunk.experience_id, "score": round(score, 4)},
            )
            for chunk, score in self.index.search(query, self.k, self.experience_id)
        ]
