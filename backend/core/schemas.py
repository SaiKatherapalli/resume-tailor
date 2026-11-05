"""
Data shapes used across the project.

Two groups:
  1. Career bank: the user's TRUE facts (input we trust).
  2. LLM outputs: shapes we FORCE the LLM to fill (structured output).
     The `description` on each field is sent to the LLM as an instruction.
"""

import re

from pydantic import BaseModel, Field, field_validator

# ============================================================ 1. career bank


_MARKDOWN_LINK = re.compile(r"^\[([^\]]+)\]\(([^)\s]+)\)$")
_KNOWN_SITES = {
    "linkedin.com": "LinkedIn",
    "github.com": "GitHub",
    "gitlab.com": "GitLab",
    "leetcode.com": "LeetCode",
    "kaggle.com": "Kaggle",
    "medium.com": "Medium",
}


def link_label(url: str) -> str:
    """'https://www.linkedin.com/in/me' -> 'LinkedIn'; an unknown site -> its domain."""
    domain = re.sub(r"^https?://(www\.)?", "", url.strip().lower()).split("/")[0]
    return next((name for site, name in _KNOWN_SITES.items() if domain.endswith(site)), domain or url)


class ContactLink(BaseModel):
    """A link in the resume header: the text people see and the address behind it."""

    label: str  # "LinkedIn", "GitHub", "Portfolio"
    url: str = ""  # empty = the resume shows the text only


class Contact(BaseModel):
    """Header line of the resume. Copied as-is, the LLM never changes it."""

    email: str
    phone: str = ""
    location: str = ""
    links: list[ContactLink] = []  # LinkedIn, GitHub, portfolio...

    @field_validator("links", mode="before")
    @classmethod
    def accept_plain_strings(cls, links: list) -> list:
        """Older banks keep links as strings: '[Text](url)', 'https://github.com/me' or just 'Text'."""
        converted = []
        for item in links or []:
            if not isinstance(item, str):
                converted.append(item)
            elif m := _MARKDOWN_LINK.match(item.strip()):
                converted.append({"label": m.group(1), "url": m.group(2)})
            elif re.match(r"^(https?://|www\.|[\w-]+\.(com|io|dev|app|net|org|me)/)", item.strip(), re.I):
                url = item.strip() if item.strip().lower().startswith("http") else f"https://{item.strip()}"
                converted.append({"label": link_label(url), "url": url})
            elif item.strip():
                converted.append({"label": item.strip(), "url": ""})
        return converted


class Education(BaseModel):
    """One degree. Copied as-is, the LLM never changes it."""

    degree: str
    school: str
    date: str
    details: str = ""  # e.g. "Related Coursework: ..."


class SectionEntry(BaseModel):
    """One item of an extra section: a project, a certification, an award...
    Copied as-is, the LLM never changes it."""

    heading: str  # e.g. "Resume Tailor | resumetailor-pro.vercel.app" or "AWS Certified Developer"
    date: str = ""
    subtitle: str = ""  # e.g. the issuing organisation
    bullets: list[str] = []


class CustomSection(BaseModel):
    """Any resume section that is not summary, skills, experience or education
    (Projects, Certifications, Awards, Publications...). Copied as-is."""

    title: str  # as written on the resume, e.g. "Projects"
    entries: list[SectionEntry] = []
    after_education: bool = False  # True if the resume shows it below Education


class Experience(BaseModel):
    """One job the user has had, with ALL their bullets for it."""

    id: str = Field(pattern=r"^[a-z0-9_]+$")  # short stable name, e.g. "tmobile"
    title: str
    company: str
    location: str = ""
    dates: str
    max_bullets: int = Field(default=6, ge=1, le=15)  # how many bullets to show on the resume
    bullets: list[str] = Field(min_length=1)


class CareerBank(BaseModel):
    """Everything true about the user's career. RAG searches inside this."""

    name: str
    contact: Contact
    summary: str
    skills: dict[str, list[str]]  # {"Cloud": ["AWS", "Docker"], ...}
    experiences: list[Experience] = Field(min_length=1)
    education: list[Education] = []
    sections: list[CustomSection] = []  # every other section, in resume order

    @field_validator("experiences")
    @classmethod
    def experience_ids_are_unique(cls, experiences: list[Experience]) -> list[Experience]:
        ids = [e.id for e in experiences]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(f"duplicate experience ids: {sorted(duplicates)}")
        return experiences

    def extra_text(self) -> str:
        """Text of the extra sections. These are real facts too (e.g. tools used in a project)."""
        return " ".join(
            part for sec in self.sections for e in sec.entries for part in (e.heading, e.subtitle, *e.bullets)
        )

    def all_skills(self) -> list[str]:
        """Every skill item in one flat list."""
        return [item for items in self.skills.values() for item in items]


class BulletChunk(BaseModel):
    """One searchable piece of text. One bullet = one chunk.

    The id is '<experience_id>-<position>', e.g. 'tmobile-3'.
    The LLM must cite these ids, so we can check every new bullet came from a real one.
    """

    id: str
    experience_id: str
    text: str


def bank_to_chunks(bank: CareerBank) -> list[BulletChunk]:
    return [
        BulletChunk(id=f"{exp.id}-{i}", experience_id=exp.id, text=text)
        for exp in bank.experiences
        for i, text in enumerate(exp.bullets)
    ]


# ============================================================ 2. LLM outputs


class JDAnalysis(BaseModel):
    """What the job description really asks for."""

    job_title: str = Field(description="The job title from the job description")
    company: str = Field(
        default="",
        description="The hiring company's short, everyday name, like 'Amazon' (not 'Amazon.com Services "
        "LLC'). No legal endings such as Inc, LLC, Ltd or Services. Empty string if not stated",
    )
    job_number: str = Field(
        default="",
        description="The job ID / requisition number, copied exactly as written in the job description "
        "(for example '3012345' from 'Job ID: 3012345'), or an empty string if none is stated",
    )
    responsibilities: list[str] = Field(description="The 3 most important responsibilities")
    keywords: list[str] = Field(
        description="The 5-10 most important keywords an ATS will look for: technologies, "
        "skills and methods. Short phrases only, like 'Spring Boot' or 'microservices'."
    )


class TailoredBullet(BaseModel):
    text: str = Field(description="The rewritten bullet. Plain text, no LaTeX, no markdown.")
    source_ids: list[str] = Field(description="IDs of the original bullets this one is based on")


class TailoredExperience(BaseModel):
    experience_id: str = Field(description="Must match an experience id from the input exactly")
    bullets: list[TailoredBullet]


class SkillRow(BaseModel):
    category: str
    items: list[str]


class TailoredResume(BaseModel):
    """The rewritten resume CONTENT. Python, not the LLM, turns this into LaTeX."""

    summary: str = Field(description="Professional summary, 5-6 sentences (about 90-120 words), plain text")
    skills: list[SkillRow] = Field(
        description="8-10 skill rows named in the job's words, most relevant first"
    )
    experiences: list[TailoredExperience]
