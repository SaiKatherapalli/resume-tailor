from core.career_bank import load_career_bank
from core.config import PROJECT_ROOT
from core.schemas import JDAnalysis, TailoredResume
from core.validation import has_term, numbers_in, validate

BANK = load_career_bank(PROJECT_ROOT / "data" / "sample_career_bank.yaml")
ANALYSIS = JDAnalysis(
    job_title="Backend Engineer", responsibilities=["Build APIs"], keywords=["FastAPI", "Redis", "Terraform"]
)


def make_resume(
    acme_bullets, globex_bullets=None, skills=None, summary="Backend engineer."
) -> TailoredResume:
    globex = globex_bullets or [
        {"text": "Built Java Spring Boot billing services.", "source_ids": ["globex-0"]}
    ]
    return TailoredResume(
        summary=summary,
        skills=skills or [{"category": "Programming", "items": ["Python"]}],
        experiences=[
            {"experience_id": "acme", "bullets": acme_bullets},
            {"experience_id": "globex", "bullets": globex},
        ],
    )


GOOD = {"text": "Built FastAPI REST APIs serving 2M requests per day.", "source_ids": ["acme-0"]}


def test_helpers():
    assert numbers_in("cut 40% for 1,000 users on EC2 and S3") == {"40", "1000"}
    assert has_term("Python and Java", "java")
    assert not has_term("JavaScript", "Java")
    assert has_term("written in C# daily", "C#")


def test_good_resume_passes():
    report = validate(BANK, ANALYSIS, make_resume([GOOD]))
    assert report.ok, report.issues


def test_invented_number_is_caught():
    bad = {"text": "Built FastAPI APIs serving 5M requests per day.", "source_ids": ["acme-0"]}
    report = validate(BANK, ANALYSIS, make_resume([bad]))
    assert not report.ok
    assert "['5']" in report.issues[0]


def test_skill_not_in_source_is_caught():
    bad = {"text": "Added Redis and PostgreSQL caching to slow endpoints.", "source_ids": ["acme-2"]}
    report = validate(BANK, ANALYSIS, make_resume([bad]))
    assert any("PostgreSQL" in i for i in report.issues)


def test_wrong_or_missing_sources_are_caught():
    no_source = {"text": "Did great work.", "source_ids": []}
    other_job = {"text": "Developed Java services.", "source_ids": ["globex-0"]}
    report = validate(BANK, ANALYSIS, make_resume([no_source, other_job]))
    assert len(report.issues) == 2


def test_keyword_candidate_does_not_have_is_caught():
    report = validate(BANK, ANALYSIS, make_resume([GOOD], summary="Expert in Terraform."))
    assert any("Terraform" in i for i in report.issues)


def test_missing_experience_is_caught():
    resume = TailoredResume(
        summary="s", skills=[], experiences=[{"experience_id": "acme", "bullets": [GOOD]}]
    )
    report = validate(BANK, ANALYSIS, resume)
    assert any("'globex' is missing" in i for i in report.issues)


def test_python_fixes_small_problems():
    skills = [
        {"category": "Programming", "items": ["Python", "Mockito"]},
        {"category": "X", "items": ["Spring Cloud"]},
    ]
    report = validate(BANK, ANALYSIS, make_resume([GOOD] * 5, skills=skills))
    assert report.ok  # fixed, so no retry needed
    all_items = [i for r in report.resume.skills for i in r.items]
    assert "Mockito" not in all_items and "Spring Cloud" not in all_items  # not in the bank
    assert len(report.resume.experiences[0].bullets) == 3  # acme max_bullets
    assert len(report.fixes) == 4  # 2 fake skills, extra bullets, forgotten skills


def test_forgotten_skills_are_put_back_next_to_their_neighbours():
    report = validate(BANK, ANALYSIS, make_resume([GOOD]))  # the LLM only listed Python
    rows = {r.category: r.items for r in report.resume.skills}
    assert rows["Programming"] == ["Python", "Java", "C#"]
    assert rows["Cloud"] == ["AWS", "Docker", "Kubernetes"]
    assert rows["Databases"] == ["PostgreSQL", "Redis"]


def test_repeated_skill_stays_in_first_row_only():
    skills = [
        {"category": "A", "items": ["Python", "Docker"]},
        {"category": "B", "items": ["Docker", "AWS"]},
    ]
    report = validate(BANK, ANALYSIS, make_resume([GOOD], skills=skills))
    assert [i for r in report.resume.skills for i in r.items].count("Docker") == 1


def test_tool_named_in_a_bullet_is_a_valid_skill():
    skills = [{"category": "Testing", "items": ["pytest"]}]  # in a bullet, not in the skills list
    report = validate(BANK, ANALYSIS, make_resume([GOOD], skills=skills))
    assert report.resume.skills[0].items == ["pytest"]


def test_keyword_coverage():
    analysis = JDAnalysis(
        job_title="Backend Engineer", responsibilities=["Build APIs"], keywords=["FastAPI", "pytest"]
    )
    report = validate(BANK, analysis, make_resume([GOOD]))
    assert report.unused_keywords == ["pytest"]  # candidate has pytest (in a bullet) but didn't use it
    assert report.keyword_coverage == 0.5
