# Deployment Guide

Instructions for running NEPSE Signal Desk locally, and for its two supported production paths: the current Azure VM deployment, and Render as an alternative.

---

## Local Development

### Backend only

```bash
pip install -r requirements.txt
cp .env.example .env
# set DATABASE_URL for accounts/watchlist/holdings; everything else has defaults
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend only

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000, talks to http://localhost:8000 by default
```

### Both with Docker Compose

```bash
docker-compose up
# Backend: http://localhost:8000
# Reads DATABASE_URL/SECRET_KEY/GOOGLE_*/etc. from a local .env via env_file
```

---

## Azure VM Deployment (current production)

The live deployment runs on an Azure VM via `docker-compose.prod.yml`, pulling the image `ghcr.io/sudeepsigdel/fyp:latest` built by `deploy.yml`. Backend and frontend are on separate subdomains (e.g. `fyp.example.com` for the frontend, `fyp-api.example.com` for the backend), each with its own TLS termination — this repo doesn't manage the reverse proxy/certs, only the containers.

### One-time VM setup

```bash
# On the VM, alongside docker-compose.prod.yml:
scp docker-compose.prod.yml youruser@<vm>:/home/youruser/
scp .env youruser@<vm>:/home/youruser/.env   # never committed — see .env.example for the full list
ssh youruser@<vm> "chmod 600 /home/youruser/.env"
```

### Deploy / redeploy

```bash
ssh youruser@<vm>
cd /home/youruser
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

`--force-recreate` matters: `env_file` values are only read when a container is *created*, so a plain `docker compose restart` won't pick up `.env` changes.

### Database migrations

Migrations aren't run automatically as part of the container lifecycle. After schema changes, run once (from a machine with `DATABASE_URL` pointed at the production DB, or via `docker exec` into the running container):

```bash
alembic upgrade head
```

### Known issue: watchtower

`docker-compose.prod.yml` also runs `containrrr/watchtower` for auto-updates, but its bundled Docker client can lag behind the host's Docker API version and crash-loop (`client version X is too old`) — check `docker logs watchtower` if the deployed image seems stale despite new pushes. When that happens, redeploy manually with the commands above rather than relying on watchtower.

### Frontend

The frontend isn't containerized in `docker-compose.prod.yml` — build it separately and serve the static output behind your reverse proxy:

```bash
cd frontend
npm ci
npm run build   # reads .env.production for VITE_API_BASE_URL
# deploy dist/ behind your web server / CDN
```

---

## Render Deployment (alternative)

### 1. Backend — Web Service

- **Source:** root of this repo
- **Runtime:** Use the existing `Dockerfile`
- **Port:** `8000`
- **Health check:** `GET /health`

**Required environment variables:** see the [full reference below](#environment-variables-reference) — at minimum `ENV=production`, `DEBUG=false`, `CORS_ORIGINS`, `SECRET_KEY`, and `DATABASE_URL` if accounts/watchlist/portfolio should work.

### 2. Frontend — Static Site

- **Root directory:** `frontend/`
- **Build command:** `npm run build`
- **Publish directory:** `frontend/dist`

**Required environment variable:**

```
VITE_API_BASE_URL=https://<your-backend>.onrender.com
```

Rebuild the static site whenever the API URL changes.

### 3. Persistent Storage

The backend reads model files and processed parquet files from disk. Attach a persistent disk to:

- `data/processed/` — trained model `.pkl` files + parquet datasets
- `outputs/` — backtest charts and reports

Without persistent storage, a redeploy will lose generated artifacts and degrade the API.

### 4. Daily Pipeline (Cron Job)

Create a Render Cron Job that runs once per day after NEPSE market close (~12:15 UTC / 6 PM Nepal):

**Command:**
```bash
bash automation/run_daily_pipeline.sh
```

Or run the Python entry point directly:
```bash
python automation/daily_pipeline.py
```

### 5. Keep API Awake

On Render's free tier, services sleep after inactivity. Use an external uptime monitor (e.g. UptimeRobot) to ping `GET /health` every 5 minutes.

---

## GitHub Actions CI/CD

The repo ships with three workflows:

### `daily-pipeline.yml`

Validates the frontend (type-check + build) and backend (`compileall` + `pytest`) on every push/PR. On a schedule (**12:15 UTC** / 6:00 PM Nepal time), manual dispatch, or push to `main`, it also:
1. Runs `automation/daily_pipeline.py` (scrape + XGBoost BUY/SELL + relative strength + backtest + report)
2. Commits only the data and latest model bundles required by the Azure API
3. Uploads small research reports/logs with three-day retention

### `deploy.yml`

On push to `main`: runs the backend test suite, then (only if it passes) builds and pushes the Docker image to `ghcr.io/sudeepsigdel/fyp:latest`. This is the image the Azure VM deployment pulls.

Daily scheduled runs use XGBoost plus relative strength. Random Forest runs
separately every Sunday at 18:00 UTC using the latest prepared data, keeping
each job within hosted-runner limits. Manual runs can select either family or
`both`. Every resulting bot commit triggers `deploy.yml`, rebuilding the
backend image and rolling it out to the Azure VM; Cloudflare builds the
frontend separately from `frontend/`.

Manual trigger: **Actions → Daily Pipeline → Run workflow**

### `keep-alive.yml`

Runs every **Monday at 06:00 UTC**. Only creates a commit if the last real commit was more than 50 days ago — prevents GitHub from disabling scheduled workflows on inactive repos.

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `ENV` | `development` | `development` or `production`. Startup **fails fast** if `production` and `CORS_ORIGINS` still resolves to `*` — see `app/config.py`. |
| `DEBUG` | `false` | Enable FastAPI debug mode |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins. Must be an explicit list in production. |
| `API_HOST` | `0.0.0.0` | Bind host |
| `API_PORT` | `8000` | Bind port |
| `SECRET_KEY` | dev placeholder | Signs JWTs and the OAuth session cookie — set a real random value in production (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days) | JWT lifetime |
| `DATABASE_URL` | unset | Postgres connection string for accounts/watchlist/holdings. Run `alembic upgrade head` after setting this (see `alembic/`) before starting the app. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | unset | Google OAuth credentials. Google login routes return 503 until both are set. |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/auth/google/callback` | The **backend's own** domain + `/api/auth/google/callback` — if frontend and backend are on separate (sub)domains, this is the backend's, not the frontend's. Must also be registered exactly under "Authorized redirect URIs" in the Google Cloud Console. |
| `FRONTEND_URL` | `http://localhost:3000` | The **frontend's** domain — where the backend redirects the browser after a successful Google login |
| `MODEL_FAMILY` | `random_forest` | `random_forest` or `xgboost` — which trained model artifacts the API serves |
| `NEPSE_SCRAPER_START_DATE` | `2020-01-01` | Earliest date the scraper backfills from when no existing raw data is present |

If backend and frontend are deployed on separate (sub)domains, `docker-compose.prod.yml`'s `backend` service loads secrets via `env_file: .env` — that `.env` must exist on the VM next to the compose file (never committed) with all of the above set. The frontend's own build-time config lives in `frontend/.env.production` (`VITE_API_BASE_URL`, no secrets, safe to commit).

Frontend:

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL |

---

## Production Verification Checklist

```
[ ] GET /health returns 200
[ ] GET /api/stocks returns stock list
[ ] GET /api/signal/{symbol} returns buy_confidence + sell_confidence
[ ] GET /api/auth/me returns 401 when unauthenticated (confirms DATABASE_URL + migrations are wired up)
[ ] Frontend loads and fetches from API without CORS errors
[ ] Signup/login works end-to-end and the watchlist/portfolio persist across a reload
[ ] Google login redirects correctly (if GOOGLE_CLIENT_ID is set)
[ ] data/processed/models/ contains .pkl files
[ ] Daily pipeline ran successfully at least once
[ ] Logs are readable (docker compose logs / Render dashboard)
```
