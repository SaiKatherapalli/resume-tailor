import pytest

from core.career_bank import CareerBankError, load_career_bank, parse_career_bank
from core.config import PROJECT_ROOT
from core.schemas import bank_to_chunks

SAMPLE = PROJECT_ROOT / "data" / "sample_career_bank.yaml"


def test_sample_file_loads():
    bank = load_career_bank(SAMPLE)
    assert bank.name == "ALEX SAMPLE"
    assert [e.id for e in bank.experiences] == ["acme", "globex"]
    assert bank.education[0].school == "Sample University"


def test_bullets_become_chunks():
    chunks = bank_to_chunks(load_career_bank(SAMPLE))
    assert len(chunks) == 6  # 4 acme + 2 globex
    assert chunks[0].id == "acme-0"
    assert chunks[-1].id == "globex-1"


def test_missing_file():
    with pytest.raises(CareerBankError, match="not found"):
        load_career_bank("nope.yaml")


def test_broken_yaml():
    with pytest.raises(CareerBankError, match="Invalid YAML"):
        parse_career_bank("name: [unclosed")


def test_missing_required_field():
    with pytest.raises(CareerBankError, match="contact"):
        parse_career_bank("name: X\nsummary: s\nskills: {}\nexperiences: []")


def test_old_banks_without_sections_still_load():
    assert load_career_bank(SAMPLE).sections == []


def test_extra_section_text_counts_as_real_facts():
    data = load_career_bank(SAMPLE).model_dump()
    data["sections"] = [
        {"title": "Projects", "entries": [{"heading": "Tailor", "bullets": ["Used LangGraph"]}]}
    ]
    bank = type(load_career_bank(SAMPLE)).model_validate(data)
    assert "LangGraph" in bank.extra_text()


def test_contact_links_accept_old_strings_and_new_pairs():
    from core.schemas import Contact

    c = Contact(
        email="a@b.c",
        links=[
            "https://www.linkedin.com/in/me",
            "github.com/me",
            "[Portfolio](https://me.dev)",
            "Just text",
            {"label": "Blog", "url": "https://blog.me"},
        ],
    )
    assert [(link.label, link.url) for link in c.links] == [
        ("LinkedIn", "https://www.linkedin.com/in/me"),
        ("GitHub", "https://github.com/me"),
        ("Portfolio", "https://me.dev"),
        ("Just text", ""),
        ("Blog", "https://blog.me"),
    ]
