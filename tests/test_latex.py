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
        summary="s", skills=[],
        experiences=[{"experience_id": "globex", "bullets": [{"text": "x", "source_ids": []}]}],
    )
    tex = render_resume(BANK, resume)
    assert "Jun 2021 -- Dec 2022" in tex
    assert "Acme Corp" not in tex  # acme had no tailored bullets, so it is skipped
