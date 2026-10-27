"""
Runs one tailoring job in the background, after the API already answered "202 Accepted".

Flow:   queued -> running -> done   (result saved)
                          -> failed (safe error message saved, full error in the logs)

Uses its OWN database sessions: the request's session is already closed by now.
"""

import logging

from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session

from api.errors import llm_error_message
from api.models import CareerBankRecord, JobStatus, TailorJob, now
from core.schemas import CareerBank
from core.tailor import tailor_resume

log = logging.getLogger(__name__)


def run_tailor_job(engine: Engine, job_id: str, api_key: str | None = None) -> None:
    # 1. Mark as running, read what we need, close the session (the LLM part takes ~30s)
    with Session(engine) as db:
        job = db.get(TailorJob, job_id)
        if job is None:
            return
        job.status = JobStatus.RUNNING
        record = db.scalar(select(CareerBankRecord).where(CareerBankRecord.user_id == job.user_id))
        job_description = job.job_description
        bank_data = record.data if record else None
        db.commit()

    # 2. The slow part
    values: dict
    try:
        if bank_data is None:
            raise ValueError("No career bank")
        result = tailor_resume(job_description, CareerBank.model_validate(bank_data), api_key=api_key)
        report = result.report
        values = {
            "status": JobStatus.DONE,
            "tex": result.tex,
            "result": {
                "analysis": result.analysis.model_dump(),
                "resume": result.resume.model_dump(),
                "validation": {
                    "ok": report.ok,
                    "issues": report.issues,
                    "fixes": report.fixes,
                    "keyword_coverage": report.keyword_coverage,
                    "unused_keywords": report.unused_keywords,
                },
                "attempts": result.attempts,
            },
        }
        log.info("job %s done in %d attempt(s), ok=%s", job_id, result.attempts, report.ok)
    except Exception as e:
        log.exception("job %s failed", job_id)  # full details for us, in the logs
        _, message = llm_error_message(e)  # short, safe message for the user
        values = {"status": JobStatus.FAILED, "error": message}

    # 3. Save the outcome
    with Session(engine) as db:
        db.execute(update(TailorJob).where(TailorJob.id == job_id).values(**values, finished_at=now()))
        db.commit()


def fail_interrupted_jobs(engine: Engine) -> int:
    """At startup: jobs left 'queued'/'running' were killed by a restart. Mark them failed."""
    with Session(engine) as db:
        result = db.execute(
            update(TailorJob)
            .where(TailorJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
            .values(
                status=JobStatus.FAILED, error="The server restarted. Please try again.", finished_at=now()
            )
        )
        db.commit()
        return result.rowcount
