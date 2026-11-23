# Deployment

Status: **Not yet deployed. Nothing below has been executed yet** – this is the plan, to be replaced by
verified instructions in Phases 2 and 8.

## Environment requirements (local)

- Python 3.11+ (developed on 3.11.9)
- Node.js 20+ (developed on 24.x) and npm
- Git

## Planned local setup

```powershell
# backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Configuration: copy `.env.example` to `.env` and adjust. No secrets are required for the default
configuration (SQLite, VADER, LLM disabled).

## Planned hosted deployment (to be evaluated in Phase 8)

- Frontend: Vercel (Next.js native hosting).
- Backend: a Python host that supports FastAPI (candidates: Render, Railway, Fly.io) – choose after
  checking current free-tier limits (sleep behaviour, memory for NLP dependencies).
- Database: managed PostgreSQL (candidates: Neon, Supabase) via `DATABASE_URL`.
- Only synthetic data is deployed unless the project owner approves otherwise.

## Troubleshooting

To be written from real issues encountered during setup and deployment.
