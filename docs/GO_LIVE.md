# Go live: the demo URL, step by step

Goal: a public web address that shows the app with the **synthetic demo data**, running on free plans:

| Piece | Service | Needs |
|---|---|---|
| Database | **Neon** (PostgreSQL) | free account |
| API | **Render** (free web service) | free account, GitHub access to this repository |
| Web app | **Vercel** (Hobby) | free account, GitHub access to this repository |

The deployment settings are already in the repository (`render.yaml`; the web app needs only one setting). **You create
the accounts and complete any password, e-mail verification or payment-card step yourself**; nothing here needs a
paid plan, but a provider may ask for a card, so stop and tell me if one does. Do the steps in this order, because
each address is needed by the next step.

Public-demo choices already made: **fully interactive** (visitors can import, undo and regenerate; uploads are capped
at 5 MB and 5,000 rows), **synthetic data only**, no login (risk R37). Free-plan behaviour: the API sleeps after
15 minutes idle, so the first visit can take about a minute (the page shows "Service unreachable", then recovers on
retry).

## 1. Neon: the database

1. Sign up at neon.com and create a project (name `azzurro-demo`). Pick a region close to Render's `oregon`
   (for example AWS US West 2 / Oregon).
2. Open **Connect**. **Turn "Connection pooling" OFF** so the host name has no `-pooler` in it. (Neon recommends the
   direct connection for migrations, and the API runs them at start-up.)
3. Copy the connection string (it starts with `postgresql://` and contains the password). **Keep it private**: you
   paste it only into Render in the next step. Do not paste it into chat or into any file in this repository.

## 2. Render: the API

1. Sign up at render.com and connect your GitHub account, allowing access to the repository
   `azzurro-review-intelligence-dashboard`.
2. **New -> Blueprint**, pick the repository and branch `main`. Render reads `render.yaml` and proposes one free web
   service `azzurro-api`.
3. It asks for two values:
   - `DATABASE_URL`: paste the Neon string from step 1.
   - `CORS_ORIGINS`: type `https://placeholder.invalid` for now (you replace it in step 4).
4. Apply. Wait for the first deploy to finish (a few minutes). Open `https://<your-service>.onrender.com/api/health`.
   It should show `"status":"ok"` and `"database_backend":"postgresql"`. Copy the service's address.
   If the service name `azzurro-api` is taken, Render adds a suffix; use whatever address it shows.

## 3. Vercel: the web app

1. Sign up at vercel.com with GitHub and allow access to the repository.
2. **Add New -> Project**, import the repository. Click **Edit** next to **Root Directory** and choose `frontend`.
   Framework: Next.js (detected).
3. Under **Environment Variables** add `NEXT_PUBLIC_API_BASE_URL` with the Render address from step 2, for example
   `https://azzurro-api.onrender.com` (**https, no trailing slash**). This value is built into the app, so if it is
   wrong or changes you must redeploy.
4. Deploy. Copy the production address (`https://<project>.vercel.app`).

## 4. Tell the API the web address

In Render, open the service -> **Environment**, edit `CORS_ORIGINS` to the exact Vercel address (no trailing slash),
save (it redeploys). Without this the browser blocks the web app's calls to the API.

## 5. Load the demo data and hand the addresses to me

Open the Vercel address: the header should say **Service connected** (wait a minute if the API was asleep). Go to
**Settings -> Load demo data**. Then give me the two addresses (Vercel and Render). They are public, not secrets.
I will run the smoke test in `docs/DEPLOYMENT.md`, record the results and the URL in the docs, and commit them.

If you would rather not click through the dashboards alone: sign in yourself in the built-in browser pane (you type any
password; I never do), and I can drive the remaining clicks. Anything involving a card, a verification code or a
password stays with you.

## Keeping it healthy

- **Reset the demo:** Settings -> Clear demo data, or undo an import from Data Import. Clearing and re-loading
  restores the clean 465-review demo.
- **Neon free storage is 1 GB:** the demo uses a few MB. Visitors' uploads count against it; the caps above limit that.
- **Redeploys:** pushing to `main` redeploys the API on Render and the web app on Vercel automatically.
- **Switch it off:** delete the Render service and the Vercel project, or the Neon project, in their dashboards.
