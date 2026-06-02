# Deployment Guide

Instructions for deploying NEPSE Signal Desk to production (Render) or running it locally with Docker.

---

## Local Development

### Backend only

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend only

```bash
cd frontend
npm install
cp .env.example .env.local
# Set VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

### Both with Docker Compose

```bash
docker-compose up
# Backend: http://localhost:8000
# Volumes: ./data → /app/data, ./outputs → /app/outputs
```

---

## Render Deployment

### 1. Backend — Web Service

- **Source:** root of this repo
- **Runtime:** Use the existing `Dockerfile`
- **Port:** `8000`
- **Health check:** `GET /health`

**Required environment variables:**

```
ENV=production
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://<your-frontend>.onrender.com
```

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

The repo ships with two workflows:

### `daily-pipeline.yml`

Runs every day at **12:15 UTC** (6:00 PM Nepal time):
1. Checks out repo
2. Installs Python dependencies
3. Validates Python code with `compileall` and `pytest`
4. Runs `automation/daily_pipeline.py`
5. Commits updated data files back to the repo
6. Uploads pipeline artifacts

The pipeline driver performs scraping when needed and includes both BUY and SELL model training before backtesting and reporting.

Manual trigger: **Actions → Daily Pipeline → Run workflow**

### `keep-alive.yml`

Runs every **Monday at 06:00 UTC**. Only creates a commit if the last real commit was more than 50 days ago — prevents GitHub from disabling scheduled workflows on inactive repos.

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `ENV` | `development` | `development` or `production` |
| `DEBUG` | `false` | Enable FastAPI debug mode |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `API_HOST` | `0.0.0.0` | Bind host |
| `API_PORT` | `8000` | Bind port |

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
[ ] Frontend loads and fetches from API without CORS errors
[ ] data/processed/models/ contains .pkl files
[ ] Daily pipeline ran successfully at least once
[ ] Logs are readable in Render dashboard
```
