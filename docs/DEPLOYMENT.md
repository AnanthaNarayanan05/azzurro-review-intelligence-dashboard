# Deployment

Status: **Local setup verified (also from a fresh clone of the repository). PostgreSQL compatibility verified locally.
Hosted deployment is NOT done, by the owner's final decision (2026-11-24).** The owner briefly asked for a live demo,
chose free hosts, then decided not to host. The deployment files (`render.yaml`, `docs/GO_LIVE.md`) are kept as an optional,
unused option; none of the hosted steps has been executed and no accounts were created.

## Environment requirements

| Tool | Version used | Notes |
|---|---|---|
| Python | 3.11.9 | 3.11+ required |
| Node.js | 24.19 | Next.js 16 requires a current LTS; `@types/node` is pinned to v24 to match |
| npm | 11.17 | |
| Git | 2.55 | |

## Local setup (verified on Windows 11, PowerShell)

All commands run from the repository root unless stated otherwise.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- Creates the SQLite database at `data/processed/azzurro.db` (git-ignored).
- API: http://localhost:8000/api/health · interactive docs: http://localhost:8000/docs
- Tools are invoked as `python -m <tool>` rather than through `.venv\Scripts\*.exe` launchers – see Troubleshooting.

### 2. Frontend (second terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 – it redirects to `/overview`, and the header shows **Service connected**
when the backend is reachable.

### 3. Configuration

- **Backend:** optional. Copy `.env.example` to `.env` in the repository root. Every setting has a safe
  default (SQLite, VADER, LLM disabled); no secrets are needed for local development.
- **Frontend:** optional. Copy `frontend/.env.example` to `frontend/.env.local` to point the UI at a
  different API URL (default `http://localhost:8000`). The backend's `CORS_ORIGINS` must include the
  frontend's origin.

### 4. Checks

```powershell
# backend (from backend/)
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .

# frontend (from frontend/)
npm test
npm run typecheck
npm run lint
npm run build
```

## Importing data locally

- Open **Data Import**, choose a `.csv` or `.xlsx` file, match columns, choose properties and formats, confirm.
- Sample files for trying the wizard: `data/sample/synthetic_reviews_sample.csv` and `.xlsx` (synthetic, 465 rows;
  regenerate with `python -m scripts.generate_sample_files` from `backend/`).
- Settings read from the environment: `MAX_UPLOAD_MB` (default 20), `MAX_IMPORT_ROWS` (default 100000) and
  `UPLOAD_DIR` (default `data/uploads`, git-ignored). An uploaded file exists there only between preview and
  commit and is then deleted; previews abandoned for 24 hours are purged.
- After pulling changes that add migrations, run `python -m alembic upgrade head` again. Restart the backend
  afterwards so it loads the new code.

## Database migrations

- Schema changes are made in `backend/app/models`, then:
  `python -m alembic revision --autogenerate -m "describe change"` → review the generated file →
  `python -m alembic upgrade head`.
- `python -m alembic check` confirms models and migrations are in sync.
- Tests build a fresh database with the real migrations, so an incorrect migration fails the test suite.

## Testing against PostgreSQL (done in Phase 8, 2026-11-24)

The hosted database will be PostgreSQL, so the whole test suite can run against it. Set `TEST_DATABASE_URL` to an
**empty, disposable** database. Every test wipes its `public` schema and rebuilds it with the real migrations, so
**never point it at data you want to keep**. Without the variable the tests use throwaway SQLite files as before.

```powershell
# from backend/ (psycopg is in requirements.txt)
$env:TEST_DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/azzurro_test"
.venv\Scripts\python.exe -m pytest
Remove-Item Env:TEST_DATABASE_URL

# time import, analysis and the dashboard endpoints on PostgreSQL (also wipes that database)
.venv\Scripts\python.exe -m scripts.benchmark --reviews 50000 --database-url "postgresql+psycopg://user:password@localhost:5432/azzurro_test"
```

How it was run here: a temporary local PostgreSQL started from the `pgserver` Python package in a separate virtual
environment (no Docker or system install needed). Any empty PostgreSQL works.

**Result (2026-11-24):** all 334 backend tests pass on PostgreSQL and on SQLite (the first run found two *test*
assumptions, not application bugs: one asserted the backend name "sqlite", and one used a label too long for its column
so PostgreSQL raised a different error type; both tests were fixed). All four migrations apply on PostgreSQL.
Benchmark on a local PostgreSQL (same laptop, so no network latency; synthetic repeated text; median of 5 runs):

| Reviews | Import (store) | Analysis | Slowest dashboard endpoint | Generate insights |
|---|---|---|---|---|
| 10,000 | 2.5 s | 11.3 s | 0.08 s | 1.2 s |
| 49,815 | 13.2 s | 60.2 s | 0.45 s (review text search), overview 0.42 s | 4.1 s |

Not measured: a *remote* managed PostgreSQL (network adds a round trip per query; the dashboard makes a handful of
queries per page), and memory use under analysis load on the hosting plan.

## Hosted deployment (Phase 8: prepared and checked locally, **not executed**)

Nothing has been deployed yet, and nothing in this section claims a live system exists. Click-by-click steps for the
chosen setup are in `docs/GO_LIVE.md`; `render.yaml` holds the API's settings.

### Shape of the deployment

Three pieces, each independent:

| Piece | What | Start command |
|---|---|---|
| Database | PostgreSQL | managed by the host |
| API | FastAPI app in `backend/` | `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Web | Next.js app in `frontend/` | build `npm ci && npm run build`, start `npm run start` (or the host's native Next.js support) |

**Release step for the API (every deploy):** `python -m alembic upgrade head` before starting the new code. Render's free
plan has no pre-deploy command, so `render.yaml` runs it at the start of the start command (`alembic upgrade head && uvicorn ...`;
checked locally with the production settings). Pin `PYTHON_VERSION=3.11.9`: Render's default is newer and untested here. Use
Neon's **direct** (non-pooled) connection string, which Neon recommends for migrations.
Build step: `pip install -r requirements.txt` (runtime dependencies only, includes the PostgreSQL driver).

### Configuration for production

| Variable | Where | Value |
|---|---|---|
| `APP_ENV` | API | `production` |
| `DATABASE_URL` | API | the host's PostgreSQL URL. `postgres://` and `postgresql://` are accepted and completed to `postgresql+psycopg://` automatically |
| `CORS_ORIGINS` | API | the exact web origin(s), e.g. `https://your-app.example` (comma-separated, no trailing slash) |
| `UPLOAD_DIR` | API | a writable folder; a file lives there only between preview and commit |
| `NEXT_PUBLIC_API_BASE_URL` | Web, **at build time** | the public URL of the API. It is baked into the build, so changing it needs a rebuild |
| `LLM_PROVIDER` / `LLM_API_KEY` | API | leave unset: there is no LLM adapter |

Secrets (database URL with password) go in the host's secret settings, never in the repository. `.env` files are git-ignored.

### Constraints to know about

- **Run exactly one API instance.** The uploaded file is kept on the instance's local disk between "preview" and
  "import"; two instances would lose it. This is fine for a demo and must be revisited before scaling.
- **There is no login.** Anyone who can open the web address can import, delete and regenerate data. For a public
  demo that is acceptable only with synthetic data (risk R14). Options if more protection is wanted: host behind the
  platform's password protection, share the address privately, or add a read-only mode / simple access code (not built;
  needs a decision).
- **Free plans sleep.** The first request after idle can take about a minute to wake the API; the UI then shows its
  "Service unreachable" state briefly and recovers on retry.
- **Only synthetic data is deployed** unless the owner approves otherwise. Load it from Settings -> Load demo data.

### Hosting options and their limits

Checked on 2026-11-24 from the vendors' own pages where they could be read and from third-party summaries otherwise.
**Verify each figure on the vendor's page before choosing; plans change.** Nothing here has been signed up for.

| Option | Role | Free-plan limits found | Cost to go beyond |
|---|---|---|---|
| Vercel Hobby | Web | Personal, non-commercial use only; commercial use needs a paid plan | Pro is paid |
| Render free web service | API | Sleeps after 15 min idle (about 1 min wake-up); 750 instance hours/month; reported 512 MB RAM; Render reportedly advises against production use of free instances | paid instances remove sleep |
| Neon free | PostgreSQL | 1 GB storage and 100 compute-hours per project; compute suspends when a limit is reached | pay-as-you-go |

All three can be used at no charge for a demo, but an account (and possibly a payment card on file) is needed, which is
why this step waits for the owner. The API uses about 65 MB resident on the development machine after start-up
(Windows; not measured under analysis load), so a 512 MB plan is plausible but **untested**.

### After deploying: smoke test (not yet run)

1. `GET <api>/api/health` returns `status: ok` and `database_backend: postgresql`.
2. Open the web address: header shows **Service connected**.
3. Settings -> Load demo data; Overview shows 465 reviews labelled "Synthetic demo data".
4. Data Import: upload `data/sample/synthetic_reviews_sample.csv`; the report counts add up; undo it.
5. Insights -> Generate insights; open an insight's evidence.
6. Record the date, the URLs and any problem in `PROJECT_PROGRESS.md`. Do not claim the deployment works until this is done.

### Decisions made by the project owner (2026-11-24)

1. Hosts: Vercel (web) + Render (API) + Neon (PostgreSQL), all free plans. The owner creates the accounts.
2. Access: **public and fully interactive**, no login; mitigated by upload caps (5 MB, 5,000 rows) and synthetic data only.
3. Genuine data is never hosted. The Neon free plan is 1 GB, so uploads are capped.

## Troubleshooting

### `ImportError: DLL load failed ... An Application Control policy has blocked this file` (SQLAlchemy)

Windows Smart App Control / Application Control may block SQLAlchemy's optional compiled (Cython)
extensions. Do not disable the security policy; reinstall SQLAlchemy as pure Python instead (fully
supported by SQLAlchemy, slightly slower, functionally identical):

```powershell
$env:DISABLE_SQLALCHEMY_CEXT = "1"
.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps --no-binary sqlalchemy sqlalchemy==2.1.9
Remove-Item Env:DISABLE_SQLALCHEMY_CEXT
```

Verify with `python -c "from sqlalchemy.util._has_cython import HAS_CYEXTENSION; print(HAS_CYEXTENSION)"` → `False`.

### `Permission denied` running `.venv\Scripts\pip.exe`, `alembic.exe`, `uvicorn.exe`

The same policy can block the small `.exe` launcher scripts that pip generates. Run the tools as modules
instead: `python -m pip`, `python -m alembic`, `python -m uvicorn`, `python -m pytest`.

### Frontend shows "Service unreachable"

The backend is not running, or it runs on a different URL/port than `NEXT_PUBLIC_API_BASE_URL`, or the
frontend origin is missing from the backend's `CORS_ORIGINS`.

### `npm run typecheck` reports errors in `.next/types/validator.ts` after deleting a page

Those types are generated by Next.js. Run `npm run build` (or `npm run dev`) once to regenerate them.
