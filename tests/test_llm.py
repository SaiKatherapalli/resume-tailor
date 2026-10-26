import pytest

from core.config import get_settings
from core.llm import LLMNotConfiguredError, get_chat_model, get_structured_llm
from core.schemas import JDAnalysis


def test_missing_key_gives_clear_error(monkeypatch):
    # Pretend there is no API key, and check we get OUR clear error.
    monkeypatch.setattr(get_settings(), "groq_api_key", None)
    with pytest.raises(LLMNotConfiguredError):
        get_chat_model()


@pytest.mark.skipif(get_settings().groq_api_key is None, reason="needs GROQ_API_KEY")
def test_llm_fills_jd_analysis():
    # Real call to Groq. Checks the shape of the answer, not exact words.
    result = get_structured_llm(JDAnalysis).invoke(
        "Analyze this job description: Python developer with FastAPI, Docker and AWS."
    )
    assert isinstance(result, JDAnalysis)
    assert result.job_title
    assert len(result.keywords) >= 3
    assert any("python" in k.lower() for k in result.keywords)
