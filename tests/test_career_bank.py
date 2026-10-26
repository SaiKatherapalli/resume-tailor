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
