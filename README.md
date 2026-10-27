# Resume Tailor

Paste a job description, get your resume rewritten for that job, as LaTeX/PDF.
It only uses facts from your own career history: every bullet is checked against its source.

**Live site:** https://resumetailor-pro.vercel.app/

**Stack:** FastAPI · LangChain · LangGraph · Groq (free LLM) · fastembed (local embeddings) · BM25 · SQLAlchemy · Alembic · PostgreSQL · LaTeX · Docker

## How it works

```
job description
   │
   ▼
analyze ──► retrieve ──► rewrite ──► validate ──► OK ──► LaTeX ──► PDF
 (LLM)     (hybrid RAG)   (LLM)      (Python)
                            ▲            │
                            └── retry ───┘  with feedback, max 3 tries
```

1. **Analyze**: the LLM pulls out the job title, main responsibilities and ATS keywords.
2. **Retrieve**: for each job you had, hybrid search (embeddings + BM25, merged with RRF) finds your best-matching bullets.
3. **Rewrite**: the LLM rewrites those bullets for the job and must cite their source ids.
4. **Validate**: Python catches invented numbers, skills, keywords and wrong sources. Problems go back to the LLM (a LangGraph loop).
5. **Render**: the text goes into a LaTeX template. Everything is escaped, so the LLM never writes LaTeX.

| Folder | What's inside |
|---|---|
| `frontend/` | the React website (Vite + Tailwind): login, career bank, tailoring, history |
| `backend/` | everything below; run all backend commands from this folder |
| `backend/core/` | the AI logic: schemas, LLM, embeddings, retrieval, prompts, chains, graph, validation, LaTeX, CLI |
| `backend/api/` | the FastAPI backend: auth, career bank, background jobs, database |
| `backend/templates/` | LaTeX resume templates (Jinja2) |
| `backend/migrations/` | database migrations (Alembic) |
| `backend/tests/` | pytest tests (no LLM calls, except one live test that is skipped without a key) |

## Run locally

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env        # then put your GROQ_API_KEY in .env (free: https://console.groq.com/keys)
```

**CLI**
```powershell
resume-tailor import my_resume.tex --out data/career_bank.yaml   # once: resume -> career bank (check the file!)
resume-tailor check
resume-tailor tailor job.txt --show                              # -> output/tailored.tex
```

**API**
```powershell
uvicorn api.main:app --reload     # open http://127.0.0.1:8000/docs
```

**Tests**
```powershell
pytest
ruff check . ; ruff format --check .
```

## Run with Docker (API + PostgreSQL + LaTeX)

Set `GROQ_API_KEY`, `JWT_SECRET` and `POSTGRES_PASSWORD` in `.env`, then:

```bash
docker compose up --build         # open http://localhost:8000/docs
```

## API in short

| Method | Path | What it does |
|---|---|---|
| POST | `/auth/register` | create an account |
| POST | `/auth/login` | get a token (form fields: `username` = email, `password`) |
| GET | `/auth/me` | who am I |
| POST | `/career-bank/import` | upload a resume (.pdf/.tex/.txt/.md), get a career bank back (not saved) |
| PUT / GET | `/career-bank` | save / read your career bank |
| POST | `/jobs` | start tailoring, `{"job_description": "..."}` → 202 + job id |
| GET | `/jobs/{id}` | status + result (`queued` → `running` → `done` / `failed`) |
| GET | `/jobs/{id}/tex`, `/jobs/{id}/pdf` | download |
| GET / DELETE | `/jobs`, `/jobs/{id}` | list / delete |

Send `Authorization: Bearer <token>` on every call except register and login.
Optionally send `X-Groq-Api-Key: <your key>` to use your own free Groq quota. It is never stored.

## Configuration

All settings come from environment variables or `.env`. See [.env.example](.env.example).
In production: `ENVIRONMENT=prod`, a long random `JWT_SECRET`, and a PostgreSQL `DATABASE_URL`.

## Known limits (next steps for scale)

- Background jobs run inside the API process (FastAPI `BackgroundTasks`), so it runs with 1 worker.
  To scale, move jobs to a queue (Redis + arq/Celery) and the login rate limit to Redis.
- The career bank is re-embedded on every job (fast for one resume). It could be cached per user.

## Run the frontend

Start the API first (see above), then in a second terminal:

```powershell
cd frontend
npm install
npm run dev        # open http://localhost:5173
```

In dev, Vite forwards `/api/*` to `http://127.0.0.1:8000`, so no CORS setup is needed.
For a deployed site, set `VITE_API_BASE` to the API URL and add the site to `CORS_ORIGINS` in `backend/.env`.
