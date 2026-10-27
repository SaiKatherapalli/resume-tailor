"""Turn any resume text (LaTeX, plain text, text from a PDF) into a CareerBank using the LLM."""

from core.llm import get_structured_llm
from core.prompts import import_prompt
from core.schemas import CareerBank


def import_resume(resume_text: str, api_key: str | None = None) -> CareerBank:
    chain = import_prompt | get_structured_llm(CareerBank, api_key)
    return chain.invoke({"resume_text": resume_text})
