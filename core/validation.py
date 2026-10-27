"""
Check the LLM's work before we trust it.

Python can't judge writing style, but it CAN catch made-up facts:
  - a bullet with no source, or a source from another job
  - a number that is not in its source bullets       ("cut cost by 40%" from nowhere)
  - a skill that is not in its source bullets         ("PostgreSQL" added to a bullet)
  - a job keyword the candidate doesn't have at all   ("Terraform" anywhere)

Small problems Python fixes by itself (fake skills removed, extra bullets cut).
Big problems become feedback, so the LLM can try again (Step 13).
"""

import re
from dataclasses import dataclass, field

from core.chains import split_keywords
from core.schemas import CareerBank, JDAnalysis, SkillRow, TailoredExperience, TailoredResume, bank_to_chunks

# A number not glued to a letter: "40%", "2M", "1,000" match; "EC2", "S3", "OAuth2" don't
_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*")


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


def has_term(text: str, term: str) -> bool:
    """Whole-word, case-insensitive. 'Java' is NOT found inside 'JavaScript'."""
    pattern = rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])"
    return re.search(pattern, text.lower()) is not None


@dataclass
class ValidationReport:
    resume: TailoredResume  # the cleaned resume (small problems already fixed)
    issues: list[str] = field(default_factory=list)  # problems only the LLM can fix
    fixes: list[str] = field(default_factory=list)  # what Python fixed by itself
    keyword_coverage: float = 1.0  # share of the candidate's real job keywords used in the resume
    unused_keywords: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def feedback(self) -> str:
        """Text we send back to the LLM on retry."""
        return "Your previous answer had these problems. Fix all of them:\n" + "\n".join(
            f"- {i}" for i in self.issues
        )


def validate(bank: CareerBank, analysis: JDAnalysis, resume: TailoredResume) -> ValidationReport:
    chunks = {c.id: c for c in bank_to_chunks(bank)}
    bank_skills = bank.all_skills()
    have, missing = split_keywords(bank, analysis.keywords)
    issues: list[str] = []
    fixes: list[str] = []

    # 1. Experiences: every real job once, no invented ones
    bank_exps = {e.id: e for e in bank.experiences}
    returned = {e.experience_id for e in resume.experiences}
    for exp_id in sorted(returned - bank_exps.keys()):
        fixes.append(f"removed unknown experience '{exp_id}'")
    for exp_id in [e.id for e in bank.experiences if e.id not in returned]:
        issues.append(f"experience '{exp_id}' is missing. Include every experience.")

    experiences: list[TailoredExperience] = []
    for exp in resume.experiences:
        if exp.experience_id not in bank_exps:
            continue
        limit = bank_exps[exp.experience_id].max_bullets
        if len(exp.bullets) > limit:
            fixes.append(f"cut '{exp.experience_id}' from {len(exp.bullets)} to {limit} bullets")
        bullets = exp.bullets[:limit]
        experiences.append(TailoredExperience(experience_id=exp.experience_id, bullets=bullets))

        # 2. Every bullet must be grounded in real bullets of the SAME job
        for b in bullets:
            short = f'"{b.text[:60]}..."' if len(b.text) > 60 else f'"{b.text}"'
            bad_ids = [
                s for s in b.source_ids if s not in chunks or chunks[s].experience_id != exp.experience_id
            ]
            if not b.source_ids:
                issues.append(f"{short} has no source_ids.")
                continue
            if bad_ids:
                issues.append(f"{short} cites {bad_ids}, which are not bullets of '{exp.experience_id}'.")
                continue
            source = " ".join(chunks[s].text for s in b.source_ids)

            new_numbers = sorted(numbers_in(b.text) - numbers_in(source))
            if new_numbers:
                issues.append(
                    f"{short} has numbers {new_numbers} that are not in its sources {b.source_ids}."
                )

            new_skills = [s for s in bank_skills if has_term(b.text, s) and not has_term(source, s)]
            if new_skills:
                issues.append(f"{short} mentions {new_skills}, not in its sources {b.source_ids}.")

    # 3. Skills: keep only skills from the bank (Python fixes this, no retry needed)
    allowed = {s.lower() for s in bank_skills}
    skills: list[SkillRow] = []
    for row in resume.skills:
        kept = [i for i in row.items if i.lower() in allowed]
        dropped = [i for i in row.items if i.lower() not in allowed]
        if dropped:
            fixes.append(f"removed skills not in the bank: {dropped}")
        if kept:
            skills.append(SkillRow(category=row.category, items=kept))

    cleaned = TailoredResume(summary=resume.summary, skills=skills, experiences=experiences)

    # 4. Keywords the candidate does NOT have must not appear anywhere
    full_text = " ".join(
        [
            cleaned.summary,
            *(i for r in cleaned.skills for i in r.items),
            *(b.text for e in cleaned.experiences for b in e.bullets),
        ]
    )
    faked = [k for k in missing if has_term(full_text, k)]
    if faked:
        issues.append(
            f"The resume claims {faked}, but the candidate has no experience with them. Remove them."
        )

    # 5. Score: how many of the candidate's REAL job keywords made it in (info, not an error)
    unused = [k for k in have if not has_term(full_text, k)]
    coverage = 1 - len(unused) / len(have) if have else 1.0

    return ValidationReport(
        resume=cleaned, issues=issues, fixes=fixes, keyword_coverage=coverage, unused_keywords=unused
    )
