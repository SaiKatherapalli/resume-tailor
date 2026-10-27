import pytest

from core.career_bank import load_career_bank
from core.config import PROJECT_ROOT
from core.embeddings import LocalEmbeddings
from core.retrieval import BulletIndex, BulletRetriever, tokenize
from core.schemas import bank_to_chunks


@pytest.fixture(scope="module")
def index() -> BulletIndex:
    # Built once for all tests in this file (embedding takes a moment).
    bank = load_career_bank(PROJECT_ROOT / "data" / "sample_career_bank.yaml")
    return BulletIndex.build(bank_to_chunks(bank), LocalEmbeddings())


def test_tokenize_keeps_tech_words():
    assert tokenize("Built Node.js APIs, C# and CI/CD.") == ["built", "node.js", "apis", "c#", "and", "ci/cd"]


def test_finds_best_bullet(index):
    top_chunk, _ = index.search("Redis caching", k=1)[0]
    assert top_chunk.id == "acme-2"


def test_filter_by_job(index):
    results = index.search("Docker Kubernetes AWS", k=5, experience_id="globex")
    assert results
    assert all(chunk.experience_id == "globex" for chunk, _ in results)


def test_langchain_retriever(index):
    docs = BulletRetriever(index=index, k=2).invoke("pytest coverage")
    assert len(docs) == 2
    assert docs[0].metadata["id"] == "acme-3"
