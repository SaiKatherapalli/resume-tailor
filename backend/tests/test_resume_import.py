from langchain_core.runnables import RunnableLambda

from core import resume_import
from core.resume_import import ImportedBank, extra_headings
from core.schemas import CareerBank, CustomSection

LATEX = r"""
\section{PROFESSIONAL SUMMARY}
text
\section{PROFESSIONAL EXPERIENCE}
\experienceheader{Engineer, Acme}{2024}
\section{PROJECTS}
\experienceheader{Resume Tailor \;|\; \href{https://x.app}{Live Demo}}{2026}
\section{EDUCATION}
\section{CERTIFICATIONS}
"""


def test_finds_extra_headings_in_latex():
    assert extra_headings(LATEX) == ["PROJECTS", "CERTIFICATIONS"]


def test_finds_known_headings_in_plain_text():
    text = "SAI DEEPAK\nEXPERIENCE\nstuff\nProjects\nResume Tailor\nAWARDS:\nBest dev"
    assert extra_headings(text) == ["Projects", "AWARDS"]


def test_core_headings_are_not_extra():
    assert extra_headings(r"\section{TECHNICAL SKILLS}\nSummary\nEducation") == []


def _bank(sections):
    data = {
        "name": "A",
        "contact": {"email": "a@b.c"},
        "summary": "s",
        "skills": {},
        "experiences": [{"id": "acme", "title": "t", "company": "c", "dates": "d", "bullets": ["b"]}],
        "sections": sections,
    }
    return ImportedBank.model_validate(data)


def test_sections_are_required_for_the_llm():
    assert ImportedBank.model_json_schema()["required"].count("sections") == 1
    assert "sections" not in CareerBank.model_json_schema().get("required", [])


def test_missed_section_is_recovered_with_a_second_call(monkeypatch):
    projects = CustomSection.model_validate(
        {
            "title": "Projects",
            "entries": [{"heading": "Resume Tailor", "date": "2026", "bullets": ["Built it."]}],
        }
    )
    calls = []

    def fake_llm(schema, api_key=None):
        def run(_):
            calls.append(schema.__name__)
            if schema is ImportedBank:
                return _bank([])  # the model forgot the Projects section
            return resume_import.ExtraSections(sections=[projects])

        return RunnableLambda(run)

    monkeypatch.setattr(resume_import, "get_structured_llm", fake_llm)
    bank = resume_import.import_resume(LATEX)

    assert calls == ["ImportedBank", "ExtraSections"]
    assert [s.title for s in bank.sections] == ["Projects"]


def test_no_second_call_when_nothing_is_missing(monkeypatch):
    calls = []

    def fake_llm(schema, api_key=None):
        def run(_):
            calls.append(schema.__name__)
            return _bank(
                [
                    {"title": "Projects", "entries": [{"heading": "x"}]},
                    {"title": "Certifications", "entries": [{"heading": "y"}]},
                ]
            )

        return RunnableLambda(run)

    monkeypatch.setattr(resume_import, "get_structured_llm", fake_llm)
    resume_import.import_resume(LATEX)
    assert calls == ["ImportedBank"]


def _pdf_with_link() -> bytes:
    """A one-page PDF: 'Resume Tailor | Live Demo' where 'Live Demo' is a clickable link."""
    import io

    from pypdf import PdfWriter
    from pypdf.annotations import Link
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(612, 792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 72 700 Td (Resume Tailor |) Tj ET BT /F1 12 Tf 170 700 Td (Live Demo) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_annotation(0, Link(rect=(169, 697, 235, 713), url="https://x.app/demo"))
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_pdf_link_address_is_put_back_next_to_its_text():
    text = resume_import.pdf_text(_pdf_with_link())
    assert "Resume Tailor | [Live Demo](https://x.app/demo)" in text
