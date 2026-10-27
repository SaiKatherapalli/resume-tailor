"""
The logged-in user's career bank.

  GET  /career-bank          read it
  PUT  /career-bank          save it (create or replace)
  POST /career-bank/import   upload a resume (.pdf/.tex/.txt/.md) -> the LLM turns it into a career bank
                             It is NOT saved: the user checks it, edits it, then saves it with PUT.
"""

import io
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import select

from api.deps import DB, CurrentUser, GroqKey
from api.models import CareerBankRecord
from core.resume_import import import_resume
from core.schemas import CareerBank

router = APIRouter(prefix="/career-bank", tags=["career bank"])

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB is plenty for a resume
TEXT_TYPES = (".tex", ".txt", ".md")


@router.get("")
def get_career_bank(user: CurrentUser, db: DB) -> CareerBank:
    record = db.scalar(select(CareerBankRecord).where(CareerBankRecord.user_id == user.id))
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No career bank yet. Import a resume or PUT one.")
    return CareerBank.model_validate(record.data)


@router.put("")
def save_career_bank(bank: CareerBank, user: CurrentUser, db: DB) -> CareerBank:
    """The body is validated by the same CareerBank model the CLI uses."""
    record = db.scalar(select(CareerBankRecord).where(CareerBankRecord.user_id == user.id))
    if record is None:
        record = CareerBankRecord(user_id=user.id, data={})
        db.add(record)
    record.data = bank.model_dump()
    db.commit()
    return bank


@router.post("/import")
def import_career_bank(
    file: Annotated[UploadFile, File(description="Your resume: .pdf, .tex, .txt or .md")],
    user: CurrentUser,
    api_key: GroqKey,
) -> CareerBank:
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "File is larger than 2 MB.")
    text = extract_text(file.filename or "", data)
    if len(text.strip()) < 100:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Could not read enough text from this file."
        )
    return import_resume(text, api_key=api_key)


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
        except Exception:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "This PDF could not be read."
            ) from None
    if name.endswith(TEXT_TYPES):
        return data.decode("utf-8", errors="replace")
    raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a .pdf, .tex, .txt or .md file.")
