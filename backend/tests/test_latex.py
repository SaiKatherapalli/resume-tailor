from core.career_bank import load_career_bank
from core.config import PROJECT_ROOT
from core.latex import escape_latex, original_resume, render_resume
from core.schemas import SkillRow, TailoredResume

BANK = load_career_bank(PROJECT_ROOT / "data" / "sample_career_bank.yaml")


def test_escape_special_characters():
    assert escape_latex("30% & $5 #1 a_b") == r"30\% \& \$5 \#1 a\_b"
    assert escape_latex("C# {x}") == r"C\# \{x\}"


def test_escape_unicode_from_llm():
    assert escape_latex("Java‑based “fast”") == "Java-based ``fast''"


def test_render_has_all_sections():
    tex = render_resume(BANK, original_resume(BANK))
    assert r"\begin{document}" in tex and r"\end{document}" in tex
    assert "ALEX SAMPLE" in tex
    assert "Austin, TX | alex@example.com" in tex
    assert "Software Engineer, Acme Corp, USA" in tex
    assert "Sample University" in tex
    assert r"\VAR" not in tex and r"\BLOCK" not in tex  # every blank was filled


def test_llm_text_is_escaped_in_output():
    resume = TailoredResume(
        summary="Cut cost by 40% & time",
        skills=[SkillRow(category="Programming", items=["C#"])],
        experiences=[{"experience_id": "acme", "bullets": [{"text": "Saved $5k", "source_ids": ["acme-0"]}]}],
    )
    tex = render_resume(BANK, resume)
    assert r"Cut cost by 40\% \& time" in tex
    assert r"C\#" in tex
    assert r"Saved \$5k" in tex


def test_dates_and_titles_come_from_bank_not_llm():
    resume = TailoredResume(
        summary="s",
        skills=[],
        experiences=[{"experience_id": "globex", "bullets": [{"text": "x", "source_ids": []}]}],
    )
    tex = render_resume(BANK, resume)
    assert "Jun 2021 -- Dec 2022" in tex
    assert "Acme Corp" not in tex  # acme had no tailored bullets, so it is skipped


def _bank_with_sections():
    return type(BANK).model_validate(
        {
            **BANK.model_dump(),
            "sections": [
                {
                    "title": "Projects",
                    "entries": [
                        {
                            "heading": "Resume Tailor | demo.app",
                            "date": "2026",
                            "bullets": ["Built an app with 100% LangGraph."],
                        }
                    ],
                },
                {
                    "title": "Certifications",
                    "after_education": True,
                    "entries": [{"heading": "AWS Developer", "date": "2025", "subtitle": "Amazon & Co"}],
                },
                {"title": "Empty", "entries": []},
            ],
        }
    )


def test_extra_sections_are_copied_as_is_in_order():
    bank = _bank_with_sections()
    tex = render_resume(bank, original_resume(bank))
    assert (
        tex.index("PROFESSIONAL EXPERIENCE")
        < tex.index("PROJECTS")
        < tex.index("EDUCATION")
        < tex.index("CERTIFICATIONS")
    )
    assert r"Built an app with 100\% LangGraph." in tex
    assert r"Amazon \& Co" in tex
    assert "EMPTY" not in tex
    assert r"\VAR" not in tex and r"\BLOCK" not in tex


def test_no_extra_sections_means_no_extra_output():
    tex = render_resume(BANK, original_resume(BANK))
    assert "PROJECTS" not in tex


def test_markdown_link_becomes_a_real_latex_link():
    out = escape_latex("Resume Tailor | [Live Demo](https://app.vercel.app/a_b?x=1&y=2#top) & more_")
    assert out == (r"Resume Tailor | \href{https://app.vercel.app/a_b?x=1&y=2\#top}{Live Demo} \& more\_")


def test_link_in_extra_section_heading_is_rendered():
    bank = type(BANK).model_validate(
        {
            **BANK.model_dump(),
            "sections": [
                {"title": "Projects", "entries": [{"heading": "Tailor | [Live Demo](https://x.app)"}]}
            ],
        }
    )
    tex = render_resume(bank, original_resume(bank))
    assert r"Tailor | \href{https://x.app}{Live Demo}" in tex


def test_header_links_are_real_links_in_the_pdf():
    bank = type(BANK).model_validate(
        {
            **BANK.model_dump(),
            "contact": {
                "email": "a@b.c",
                "links": [{"label": "LinkedIn", "url": "https://linkedin.com/in/me"}, {"label": "Portfolio"}],
            },
        }
    )
    tex = render_resume(bank, original_resume(bank))
    assert r"a@b.c | \href{https://linkedin.com/in/me}{LinkedIn}" in tex
    assert "Portfolio" not in tex  # no address, so it is left off


def test_project_link_is_its_own_pair_and_renders_as_a_link():
    bank = type(BANK).model_validate(
        {
            **BANK.model_dump(),
            "sections": [
                {
                    "title": "Projects",
                    "entries": [
                        {"heading": "Tailor", "link_label": "Live Demo", "link_url": "https://x.app"},
                        {"heading": "No link", "link_label": "Live Demo"},
                    ],
                }
            ],
        }
    )
    tex = render_resume(bank, original_resume(bank))
    assert r"Tailor | \href{https://x.app}{Live Demo}" in tex
    assert "No link}" in tex and "Live Demo}" not in tex.split("No link")[1]  # label alone is not shown


def test_old_heading_with_markdown_link_is_split_into_the_pair():
    from core.schemas import SectionEntry

    e = SectionEntry(heading="Resume Tailor -- AI App | [Live Demo](https://x.app/)")
    assert (e.heading, e.link_label, e.link_url) == ("Resume Tailor -- AI App", "Live Demo", "https://x.app/")
    assert e.heading_with_link == "Resume Tailor -- AI App | [Live Demo](https://x.app/)"
