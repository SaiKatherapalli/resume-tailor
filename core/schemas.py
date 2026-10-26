"""
Data shapes used across the project.

Two groups:
  1. Career bank: the user's TRUE facts (input we trust).
  2. LLM outputs: shapes we FORCE the LLM to fill (structured output).
     The `description` on each field is sent to the LLM as an instruction.
"""

from pydantic import BaseModel, Field, field_validator

# ============================================================ 1. career bank


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
    summary: str
    skills: dict[str, list[str]]  # {"Cloud": ["AWS", "Docker"], ...}
    experiences: list[Experience] = Field(min_length=1)

    @field_validator("experiences")
    @classmethod
    def experience_ids_are_unique(cls, experiences: list[Experience]) -> list[Experience]:
        ids = [e.id for e in experiences]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(f"duplicate experience ids: {sorted(duplicates)}")
        return experiences


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

    summary: str = Field(description="Professional summary, 3-4 sentences, plain text")
    skills: list[SkillRow] = Field(description="Skill rows, most relevant categories first")
    experiences: list[TailoredExperience]
