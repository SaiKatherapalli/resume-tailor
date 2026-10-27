"""Tests for the pipeline WITHOUT calling the real LLM: we plug in fake chains."""

import pytest
from langchain_core.runnables import RunnableLambda

from core.career_bank import load_career_bank
from core.chains import Chains, build_rewrite_input, build_tailor_pipeline, split_keywords
from core.config import PROJECT_ROOT
from core.embeddings import LocalEmbeddings
from core.retrieval import BulletIndex
from core.schemas import JDAnalysis, TailoredResume, bank_to_chunks

ANALYSIS = JDAnalysis(
    job_title="Backend Engineer",
    responsibilities=["Build APIs", "Run on AWS", "Write tests"],
    keywords=["FastAPI", "AWS", "Redis", "Terraform"],
)


@pytest.fixture(scope="module")
def bank():
    return load_career_bank(PROJECT_ROOT / "data" / "sample_career_bank.yaml")


@pytest.fixture(scope="module")
def index(bank):
    return BulletIndex.build(bank_to_chunks(bank), LocalEmbeddings())


def test_split_keywords(bank):
    have, missing = split_keywords(bank, ANALYSIS.keywords)
    assert have == ["FastAPI", "AWS", "Redis"]
    assert missing == ["Terraform"]


def test_pipeline_runs_with_fake_llm(bank, index):
    seen = {}

    def fake_rewrite(inputs: dict) -> TailoredResume:
        seen.update(inputs)  # remember what the "LLM" received
        return TailoredResume(summary="s", skills=[], experiences=[])

    fake = Chains(analyze=RunnableLambda(lambda _: ANALYSIS), rewrite=RunnableLambda(fake_rewrite))
    out = build_tailor_pipeline(fake).invoke({"job_description": "any", "bank": bank, "index": index})

    assert out["analysis"] == ANALYSIS
    assert set(out["candidates"]) == {"acme", "globex"}
    assert "[acme-0]" in seen["experiences"]  # bullets were sent with their ids
    assert "Terraform" not in seen["honest_keywords"]  # we never tell the LLM to claim missing skills


def test_rewrite_input_asks_for_right_bullet_count(bank, index):
    from core.chains import retrieve_candidates

    inputs = build_rewrite_input(bank, ANALYSIS, retrieve_candidates(bank, index, ANALYSIS))
    assert "acme | Software Engineer, Acme Corp | write 3 bullets" in inputs["experiences"]
    assert "globex | Junior Developer, Globex | write 2 bullets" in inputs["experiences"]
