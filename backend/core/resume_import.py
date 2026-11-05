"""Turn any resume text (LaTeX, plain text, text from a PDF) into a CareerBank using the LLM."""

import io
import re

import pdfplumber
from pydantic import BaseModel, Field

from core.llm import get_structured_llm
from core.prompts import import_prompt, sections_prompt
from core.schemas import CareerBank, CustomSection

# Headings the CareerBank already has its own place for
_CORE_HEADINGS = {
    "summary",
    "professional summary",
    "profile",
    "objective",
    "skills",
    "technical skills",
    "experience",
    "work experience",
    "professional experience",
    "employment",
    "education",
}

# Plain-text and PDF resumes have no \section{...}, so we also know the usual extra headings
_KNOWN_EXTRA_HEADINGS = {
    "projects",
    "academic projects",
    "personal projects",
    "technical projects",
    "certifications",
    "certificates",
    "licenses and certifications",
    "awards",
    "honors",
    "honors and awards",
    "achievements",
    "publications",
    "patents",
    "research",
    "volunteer experience",
    "volunteering",
    "leadership",
    "activities",
    "extracurricular activities",
    "training",
    "languages",
    "interests",
}


def pdf_text(data: bytes) -> str:
    """Text of a PDF, with every web link written as [visible text](url).

    A PDF keeps a link's address apart from its text: a clickable box (position + URL) lies over
    the words. We find the words inside each box and put the address back next to them.
    """
    pages = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            missing = []
            for link in page.hyperlinks:
                url = link.get("uri") or ""
                if not url.startswith(("http://", "https://")):
                    continue
                box = (
                    max(link["x0"] - 1, 0),
                    max(link["top"] - 1, 0),
                    min(link["x1"] + 1, page.width),
                    min(link["bottom"] + 1, page.height),
                )
                words = " ".join((page.within_bbox(box).extract_text() or "").split())
                if not words or url.lower().rstrip("/").endswith(words.lower().rstrip("/")):
                    continue  # no text under the box, or the text already shows the address
                marked = f"[{words}]({url})"
                if words in text:
                    text = text.replace(words, marked, 1)
                else:
                    missing.append(marked)
            pages.append("\n".join([text, *missing]))
    return "\n".join(pages)


class ImportedBank(CareerBank):
    """What the LLM fills. `sections` is REQUIRED here: when it is optional the model often skips it."""

    sections: list[CustomSection] = Field(
        description="Every resume section that is not summary, skills, experience or education "
        "(Projects, Certifications, Awards...). Empty list only if the resume has none."
    )


class ExtraSections(BaseModel):
    sections: list[CustomSection]


def extra_headings(resume_text: str) -> list[str]:
    """Section headings in the resume that the career bank has no own place for."""
    found: list[str] = []
    for line in resume_text.splitlines():
        line = line.strip()
        latex = re.match(r"\\section\*?\{(.+?)\}", line)
        title = (latex.group(1) if latex else line).strip(" :")
        key = title.lower()
        if not 2 <= len(title) <= 50 or key in _CORE_HEADINGS or key in {f.lower() for f in found}:
            continue
        if latex or key in _KNOWN_EXTRA_HEADINGS:
            found.append(title)
    return found


def import_resume(resume_text: str, api_key: str | None = None) -> CareerBank:
    chain = import_prompt | get_structured_llm(ImportedBank, api_key)
    bank = CareerBank.model_validate(chain.invoke({"resume_text": resume_text}).model_dump())

    # Safety net: a heading that is in the resume but not in the bank gets one more, focused try
    have = {s.title.strip().lower() for s in bank.sections}
    missing = [h for h in extra_headings(resume_text) if h.lower() not in have]
    if missing:
        extra = (sections_prompt | get_structured_llm(ExtraSections, api_key)).invoke(
            {"resume_text": resume_text, "headings": ", ".join(missing)}
        )
        bank.sections += [s for s in extra.sections if s.entries and s.title.strip().lower() not in have]
    return bank
