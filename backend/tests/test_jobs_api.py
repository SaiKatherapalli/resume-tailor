"""Job endpoints. tailor_resume (the LLM part) is replaced with a fake.

Note: TestClient runs background tasks before it returns, so right after POST the job is finished.
"""

import pytest
from sqlalchemy.orm import Session

from api import worker
from api.models import JobStatus, TailorJob
from core.career_bank import load_career_bank
from core.config import PROJECT_ROOT, get_settings
from core.latex import original_resume, render_resume
from core.llm import LLMNotConfiguredError
from core.schemas import JDAnalysis
from core.tailor import TailorResult
from core.validation import ValidationReport
from tests.conftest import register_and_login

BANK = load_career_bank(PROJECT_ROOT / "data" / "sample_career_bank.yaml")
JD = {"job_description": "Senior Backend Engineer. Python, AWS, Docker, Kubernetes, REST APIs. " * 2}


@pytest.fixture
def fake_llm(monkeypatch):
    calls = []

    def fake_tailor(job_description, bank, api_key=None, on_step=None):
        calls.append(api_key)
        resume = original_resume(bank)
        return TailorResult(
            analysis=JDAnalysis(job_title="Backend Engineer", responsibilities=[], keywords=["Python"]),
            report=ValidationReport(resume=resume),
            attempts=1,
            tex=render_resume(bank, resume),
        )

    monkeypatch.setattr(worker, "tailor_resume", fake_tailor)
    return calls


@pytest.fixture
def user(client, auth):
    client.put("/career-bank", json=BANK.model_dump(), headers=auth)
    return auth


def test_full_job_flow(client, user, fake_llm):
    r = client.post("/jobs", json=JD, headers={**user, "X-Groq-Api-Key": "gsk_mine"})
    assert r.status_code == 202
    job_id = r.json()["id"]

    job = client.get(f"/jobs/{job_id}", headers=user).json()
    assert job["status"] == "done"
    assert job["result"]["validation"]["ok"] is True
    assert job["result"]["analysis"]["job_title"] == "Backend Engineer"
    assert fake_llm == ["gsk_mine"]  # the user's own key reached the LLM

    tex = client.get(f"/jobs/{job_id}/tex", headers=user)
    assert tex.status_code == 200 and "ALEX SAMPLE" in tex.text
    assert [j["id"] for j in client.get("/jobs", headers=user).json()] == [job_id]

    assert client.delete(f"/jobs/{job_id}", headers=user).status_code == 204
    assert client.get(f"/jobs/{job_id}", headers=user).status_code == 404


def test_needs_career_bank_first(client, auth, fake_llm):
    assert client.post("/jobs", json=JD, headers=auth).status_code == 409


def test_short_job_description_rejected(client, user):
    assert client.post("/jobs", json={"job_description": "too short"}, headers=user).status_code == 422


def test_other_users_cannot_see_my_jobs(client, user, fake_llm):
    job_id = client.post("/jobs", json=JD, headers=user).json()["id"]
    other = register_and_login(client, email="other@example.com")
    assert client.get(f"/jobs/{job_id}", headers=other).status_code == 404
    assert client.get(f"/jobs/{job_id}/tex", headers=other).status_code == 404
    assert client.delete(f"/jobs/{job_id}", headers=other).status_code == 404
    assert client.get("/jobs", headers=other).json() == []


def test_failed_job_has_safe_error(client, user, monkeypatch):
    def broken(*args, **kwargs):
        raise LLMNotConfiguredError("secret internal details")

    monkeypatch.setattr(worker, "tailor_resume", broken)
    job_id = client.post("/jobs", json=JD, headers=user).json()["id"]
    job = client.get(f"/jobs/{job_id}", headers=user).json()
    assert job["status"] == "failed"
    assert "secret" not in job["error"]
    assert client.get(f"/jobs/{job_id}/tex", headers=user).status_code == 409


def test_daily_limit(client, user, fake_llm, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_jobs_per_day", 2)
    assert client.post("/jobs", json=JD, headers=user).status_code == 202
    assert client.post("/jobs", json=JD, headers=user).status_code == 202
    assert client.post("/jobs", json=JD, headers=user).status_code == 429


def test_restart_marks_unfinished_jobs_failed(client, user):
    engine = client.app.state.engine
    with Session(engine) as db:
        user_id = client.get("/auth/me", headers=user).json()["id"]
        db.add(TailorJob(user_id=user_id, job_description="x", status=JobStatus.RUNNING))
        db.commit()
    assert worker.fail_interrupted_jobs(engine) == 1


# ------------------------------------------------------------------ read a job link


def test_read_link_needs_login(client):
    assert client.post("/jobs/read-link", json={"url": "https://example.com/job"}).status_code == 401


def test_read_link_returns_the_job_text(client, auth, monkeypatch):
    from api.routes import jobs
    from core.job_page import JobPosting

    monkeypatch.setattr(
        jobs, "fetch_job_posting", lambda url: JobPosting(text="Job text " * 20, title="SRE", company="Acme")
    )
    r = client.post("/jobs/read-link", json={"url": "https://example.com/job"}, headers=auth)
    assert r.status_code == 200
    assert r.json() == {"job_description": "Job text " * 20, "job_title": "SRE", "company": "Acme"}


def test_read_link_explains_a_bad_link(client, auth):
    r = client.post("/jobs/read-link", json={"url": "not a link"}, headers=auth)
    assert r.status_code == 422
    assert "valid link" in r.json()["detail"]
