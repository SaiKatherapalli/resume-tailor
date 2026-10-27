"""
Plain text -> LaTeX -> PDF.

The LLM never writes LaTeX. Python puts its plain text into a template and
escapes every value, so the LLM can never break the resume design.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import jinja2

from core.config import PROJECT_ROOT
from core.schemas import CareerBank, SkillRow, TailoredBullet, TailoredExperience, TailoredResume

TEMPLATES_DIR = PROJECT_ROOT / "templates"

# ------------------------------------------------------------------ 1. escape

_REPLACE = {
    # LaTeX special characters
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    # Unicode that LLMs often produce
    "‐": "-", "‑": "-",       # hyphen, non-breaking hyphen
    "–": "--", "—": "---",    # en dash, em dash
    "‘": "`", "’": "'",       # curly single quotes
    "“": "``", "”": "''",     # curly double quotes
    " ": " ", " ": " ",       # non-breaking spaces
    "•": "",                       # stray bullet symbol
}
_PATTERN = re.compile("|".join(re.escape(k) for k in _REPLACE))


def escape_latex(value: object) -> str:
    """'Cut time by 30% & cost' -> 'Cut time by 30\\% \\& cost'"""
    if value is None:
        return ""
    return _PATTERN.sub(lambda m: _REPLACE[m.group()], str(value))


# ------------------------------------------------------------------ 2. render

_jinja = jinja2.Environment(
    block_start_string=r"\BLOCK{", block_end_string="}",
    variable_start_string=r"\VAR{", variable_end_string="}",
    comment_start_string=r"\#{", comment_end_string="}",
    trim_blocks=True, lstrip_blocks=True,
    finalize=escape_latex,             # runs on EVERY \VAR{...}: auto-escape
    undefined=jinja2.StrictUndefined,  # typo in template -> clear error, not a silent blank
)


def build_context(bank: CareerBank, resume: TailoredResume) -> dict:
    """Mix fixed facts (from the bank) with tailored text (from the LLM)."""
    by_id = {e.experience_id: e for e in resume.experiences}
    experiences = []
    for exp in bank.experiences:  # bank order = real job order; dates/titles never come from the LLM
        tailored = by_id.get(exp.id)
        if not tailored or not tailored.bullets:
            continue
        place = ", ".join(p for p in (exp.company, exp.location) if p)
        experiences.append({
            "heading": f"{exp.title}, {place}",
            "dates": exp.dates,
            "bullets": [b.text for b in tailored.bullets],
        })

    contact = bank.contact
    return {
        "name": bank.name,
        "contact_parts": [p for p in (contact.location, contact.phone, contact.email, *contact.links) if p],
        "summary": resume.summary,
        "skills": resume.skills,
        "experiences": experiences,
        "education": bank.education,
    }


def render_resume(bank: CareerBank, resume: TailoredResume, template: str = "classic.tex.j2") -> str:
    template_text = (TEMPLATES_DIR / template).read_text(encoding="utf-8")
    return _jinja.from_string(template_text).render(**build_context(bank, resume))


def original_resume(bank: CareerBank) -> TailoredResume:
    """The bank as-is (no LLM). Useful to check the template looks right."""
    return TailoredResume(
        summary=bank.summary,
        skills=[SkillRow(category=c, items=i) for c, i in bank.skills.items()],
        experiences=[
            TailoredExperience(
                experience_id=e.id,
                bullets=[TailoredBullet(text=b, source_ids=[]) for b in e.bullets[: e.max_bullets]],
            )
            for e in bank.experiences
        ],
    )


# ------------------------------------------------------------------ 3. compile to PDF


def find_compiler() -> str | None:
    for name in ("tectonic", "pdflatex"):
        if shutil.which(name):
            return name
    return None


def compile_pdf(tex: str, timeout: int = 90) -> bytes:
    """
    .tex text -> PDF bytes.

    Safety: LaTeX can run shell commands and read files. We turn shell commands off,
    block reading/writing outside the temp folder, and set a time limit.
    """
    compiler = find_compiler()
    if compiler is None:
        raise RuntimeError("No LaTeX compiler found. Install Tectonic or MiKTeX.")

    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "resume.tex").write_text(tex, encoding="utf-8")
        if compiler == "tectonic":
            cmd = ["tectonic", "--untrusted", "--chatter", "minimal", "resume.tex"]
        else:
            cmd = ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"]

        env = {**os.environ, "openin_any": "p", "openout_any": "p"}
        result = subprocess.run(
            cmd, cwd=tmp, env=env, capture_output=True, text=True, errors="replace", timeout=timeout
        )
        pdf = Path(tmp, "resume.pdf")
        if result.returncode != 0 or not pdf.exists():
            log = (result.stdout + result.stderr)[-2000:]
            raise RuntimeError(f"LaTeX failed:\n{log}")
        return pdf.read_bytes()
