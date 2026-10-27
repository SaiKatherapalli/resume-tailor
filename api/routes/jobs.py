"""
Tailoring jobs.

Tailoring takes 20-60 seconds, too long to keep an HTTP request waiting. So:
  POST /jobs            -> 202 + job id, right away. The work starts in the background.
  GET  /jobs/{id}       -> poll until status is "done" or "failed"
  GET  /jobs/{id}/tex   -> download the LaTeX
  GET  /jobs/{id}/pdf   -> download the PDF (if the server has a LaTeX compiler)
  GET  /jobs            -> your recent jobs
  DELETE /jobs/{id}
"""

from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from sqlalchemy import func, select

from api.deps import DB, CurrentUser, GroqKey
from api.models import CareerBankRecord, JobStatus, TailorJob, now
from api.schemas import JobCreate, JobOut, JobSummary
from api.worker import run_tailor_job
from core.config import get_settings
from core.latex import compile_pdf, find_compiler

router = APIRouter(prefix="/jobs", tags=["tailor jobs"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_job(
    body: JobCreate, user: CurrentUser, db: DB, api_key: GroqKey, request: Request, tasks: BackgroundTasks
) -> JobOut:
    if db.scalar(select(CareerBankRecord.id).where(CareerBankRecord.user_id == user.id)) is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Save your career bank first (PUT /career-bank).")
    check_limits(db, user.id)

    job = TailorJob(user_id=user.id, job_description=body.job_description)
    db.add(job)
    db.commit()
    db.refresh(job)
    # Runs AFTER the response is sent. The user's key goes to the task in memory, never to the database.
    tasks.add_task(run_tailor_job, request.app.state.engine, job.id, api_key)
    return JobOut.model_validate(job)


@router.get("")
def list_jobs(user: CurrentUser, db: DB, limit: int = 20) -> list[JobSummary]:
    query = (
        select(TailorJob)
        .where(TailorJob.user_id == user.id)
        .order_by(TailorJob.created_at.desc())
        .limit(min(max(limit, 1), 100))
    )
    return [JobSummary.model_validate(j) for j in db.scalars(query)]


@router.get("/{job_id}")
def get_job(job_id: str, user: CurrentUser, db: DB) -> JobOut:
    return JobOut.model_validate(own_job(db, job_id, user.id))


@router.get("/{job_id}/tex")
def download_tex(job_id: str, user: CurrentUser, db: DB) -> Response:
    job = finished_job(db, job_id, user.id)
    return Response(
        job.tex,
        media_type="application/x-tex",
        headers={"Content-Disposition": f'attachment; filename="resume-{job.id[:8]}.tex"'},
    )


@router.get("/{job_id}/pdf")
def download_pdf(job_id: str, user: CurrentUser, db: DB) -> Response:
    job = finished_job(db, job_id, user.id)
    if find_compiler() is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PDF is not available. Download the .tex.")
    return Response(
        compile_pdf(job.tex),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="resume-{job.id[:8]}.pdf"'},
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, user: CurrentUser, db: DB) -> None:
    db.delete(own_job(db, job_id, user.id))
    db.commit()


# ------------------------------------------------------------------ helpers


def own_job(db: DB, job_id: str, user_id: str) -> TailorJob:
    """Another user's job gives 404, not 403: we don't even admit it exists."""
    job = db.get(TailorJob, job_id)
    if job is None or job.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")
    return job


def finished_job(db: DB, job_id: str, user_id: str) -> TailorJob:
    job = own_job(db, job_id, user_id)
    if job.status != JobStatus.DONE:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Job is {job.status}, not done.")
    return job


def check_limits(db: DB, user_id: str) -> None:
    """Each job costs LLM calls from a free quota, so every user gets a fair share."""
    settings = get_settings()
    mine = select(func.count()).select_from(TailorJob).where(TailorJob.user_id == user_id)

    active = db.scalar(mine.where(TailorJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING])))
    if active >= settings.max_active_jobs_per_user:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Wait for your running jobs to finish.")

    today = db.scalar(mine.where(TailorJob.created_at >= now() - timedelta(days=1)))
    if today >= settings.max_jobs_per_day:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Daily limit reached. Try again tomorrow.")
