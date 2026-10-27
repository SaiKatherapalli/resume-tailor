"""Test the retry loop with fake LLMs (no API calls)."""

import pytest
from langchain_core.runnables import RunnableLambda

from core.career_bank import load_career_bank
from core.chains import Chains
from core.config import PROJECT_ROOT
from core.embeddings import LocalEmbeddings
from core.graph import MAX_ATTEMPTS, build_graph
from core.retrieval import BulletIndex
from core.schemas import JDAnalysis, TailoredResume, bank_to_chunks

ANALYSIS = JDAnalysis(job_title="Backend Engineer", responsibilities=["Build APIs"], keywords=["FastAPI"])
GLOBEX = {
    "experience_id": "globex",
    "bullets": [{"text": "Built Java services.", "source_ids": ["globex-0"]}],
}
GOOD = TailoredResume(
    summary="Backend engineer.",
    skills=[],
    experiences=[
        {"experience_id": "acme", "bullets": [{"text": "Built FastAPI APIs.", "source_ids": ["acme-0"]}]},
        GLOBEX,
    ],
)
BAD = TailoredResume(  # invented number: 9M is not in acme-0
    summary="Backend engineer.",
    skills=[],
    experiences=[
        {"experience_id": "acme", "bullets": [{"text": "Served 9M requests.", "source_ids": ["acme-0"]}]},
        GLOBEX,
    ],
)


@pytest.fixture(scope="module")
def inputs():
    bank = load_career_bank(PROJECT_ROOT / "data" / "sample_career_bank.yaml")
    index = BulletIndex.build(bank_to_chunks(bank), LocalEmbeddings())
    return {"job_description": "We need a backend engineer.", "bank": bank, "index": index}


def run(inputs, answers):
    """Fake rewrite LLM: returns the given answers in order, and records the feedback it got."""
    feedbacks = []

    def fake_rewrite(x):
        feedbacks.append(x["feedback"])
        return answers[min(len(feedbacks), len(answers)) - 1]

    chains = Chains(analyze=RunnableLambda(lambda _: ANALYSIS), rewrite=RunnableLambda(fake_rewrite))
    return build_graph(chains).invoke(inputs), feedbacks


def test_good_first_time_no_retry(inputs):
    out, feedbacks = run(inputs, [GOOD])
    assert out["attempts"] == 1
    assert out["best"].ok
    assert feedbacks == [""]


def test_retries_with_feedback_then_passes(inputs):
    out, feedbacks = run(inputs, [BAD, GOOD])
    assert out["attempts"] == 2
    assert out["best"].ok
    assert "9" in feedbacks[1]  # the LLM was told what was wrong


def test_stops_after_max_attempts(inputs):
    out, _ = run(inputs, [BAD])
    assert out["attempts"] == MAX_ATTEMPTS
    assert not out["best"].ok  # we still return the best answer we got
