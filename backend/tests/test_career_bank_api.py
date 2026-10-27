from api.routes import career_bank as route
from core.career_bank import load_career_bank
from core.config import PROJECT_ROOT
from core.llm import LLMNotConfiguredError
from tests.conftest import register_and_login

BANK = load_career_bank(PROJECT_ROOT / "data" / "sample_career_bank.yaml")
BANK_JSON = BANK.model_dump()
RESUME_TEXT = "Alex Sample, Software Engineer at Acme. " * 10


def test_no_bank_yet(client, auth):
    assert client.get("/career-bank", headers=auth).status_code == 404


def test_save_and_read(client, auth):
    assert client.put("/career-bank", json=BANK_JSON, headers=auth).status_code == 200
    assert client.get("/career-bank", headers=auth).json()["name"] == "ALEX SAMPLE"

    changed = {**BANK_JSON, "name": "NEW NAME"}
    client.put("/career-bank", json=changed, headers=auth)  # second PUT replaces it
    assert client.get("/career-bank", headers=auth).json()["name"] == "NEW NAME"


def test_invalid_bank_is_rejected(client, auth):
    bad = {**BANK_JSON, "experiences": []}  # at least 1 experience is required
    assert client.put("/career-bank", json=bad, headers=auth).status_code == 422


def test_users_only_see_their_own_bank(client, auth):
    client.put("/career-bank", json=BANK_JSON, headers=auth)
    other = register_and_login(client, email="other@example.com")
    assert client.get("/career-bank", headers=other).status_code == 404


def test_import_uses_llm_and_users_key(client, auth, monkeypatch):
    seen = {}

    def fake_import(text, api_key=None):
        seen.update(text=text, api_key=api_key)
        return BANK

    monkeypatch.setattr(route, "import_resume", fake_import)
    files = {"file": ("resume.txt", RESUME_TEXT.encode(), "text/plain")}
    r = client.post("/career-bank/import", files=files, headers={**auth, "X-Groq-Api-Key": "gsk_mine"})

    assert r.status_code == 200
    assert r.json()["name"] == "ALEX SAMPLE"
    assert seen == {"text": RESUME_TEXT, "api_key": "gsk_mine"}
    assert client.get("/career-bank", headers=auth).status_code == 404  # import does NOT save


def test_import_rejects_bad_files(client, auth):
    files = {"file": ("resume.docx", b"x" * 200, "application/octet-stream")}
    assert client.post("/career-bank/import", files=files, headers=auth).status_code == 415
    files = {"file": ("resume.txt", b"too short", "text/plain")}
    assert client.post("/career-bank/import", files=files, headers=auth).status_code == 422


def test_no_llm_key_gives_clear_error(client, auth, monkeypatch):
    def no_key(text, api_key=None):
        raise LLMNotConfiguredError("no key")

    monkeypatch.setattr(route, "import_resume", no_key)
    files = {"file": ("resume.txt", RESUME_TEXT.encode(), "text/plain")}
    r = client.post("/career-bank/import", files=files, headers=auth)
    assert r.status_code == 503
    assert "X-Groq-Api-Key" in r.json()["detail"]
