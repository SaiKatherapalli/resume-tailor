"""CLI tests. The LLM part (tailor_resume) is replaced with a fake."""

import pytest

from core import cli
from core.career_bank import load_career_bank
from core.config import PROJECT_ROOT
from core.latex import original_resume, render_resume
from core.schemas import JDAnalysis
from core.tailor import TailorResult
from core.validation import ValidationReport

SAMPLE = str(PROJECT_ROOT / "data" / "sample_career_bank.yaml")


def test_check_command(capsys):
    cli.main(["check", SAMPLE])
    out = capsys.readouterr().out
    assert "OK: ALEX SAMPLE" in out
    assert "acme: 4 bullets, shows 3" in out


def test_missing_file_gives_clear_error(tmp_path):
    with pytest.raises(SystemExit, match="not found"):
        cli.main(["tailor", str(tmp_path / "nope.txt"), "--bank", SAMPLE])


def test_tailor_writes_tex(tmp_path, monkeypatch):
    bank = load_career_bank(SAMPLE)
    resume = original_resume(bank)
    fake = TailorResult(
        analysis=JDAnalysis(job_title="Engineer", responsibilities=[], keywords=[]),
        report=ValidationReport(resume=resume),
        attempts=1,
        tex=render_resume(bank, resume),
    )
    monkeypatch.setattr(cli, "tailor_resume", lambda *a, **k: fake)

    job = tmp_path / "job.txt"
    job.write_text("We need an engineer.", encoding="utf-8")
    out = tmp_path / "out" / "resume.tex"
    cli.main(["tailor", str(job), "--bank", SAMPLE, "--out", str(out)])

    assert "ALEX SAMPLE" in out.read_text(encoding="utf-8")
