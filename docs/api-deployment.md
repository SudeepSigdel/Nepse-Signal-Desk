# API and Deployment

## API Surface
- `GET /health` - health check
- `GET /api/stocks` - ranked stock list
- `GET /api/stocks/{symbol}` - detailed OHLCV and indicators
- `GET /api/signal/{symbol}` - signal verdict and explanation
- `GET /api/summary` - top signal summary

## Deployment Notes
- Run the backend behind a stable host or container runtime.
- Build the frontend with Vite and serve the generated `dist/` directory.
- Keep CORS aligned between the frontend URL and backend API URL.
- If using scheduled automation, validate the daily pipeline scripts before enabling the job.

## Operational Checklist
- Confirm the backend responds on the configured port.
- Confirm the frontend can reach the API base URL.
- Confirm fresh model outputs are written to `data/processed/` and `outputs/` when the pipeline runs.

## Render Deployment Checklist

### 1. Deploy the backend as a Render Web Service
- Use the root of this repo as the service source.
- Prefer the existing Dockerfile for the backend service.
- Expose port `8000` and point Render health checks at `/health`.
- Set the runtime environment to production values.

Recommended environment variables:
- `ENV=production`
- `DEBUG=false`
- `LOG_LEVEL=INFO`
- `CORS_ORIGINS=https://<your-frontend-domain>.onrender.com`
- Any other secret or provider-specific values you add later

### 2. Deploy the frontend as a separate Render Static Site
- Build the frontend from the `frontend/` folder.
- Use Vite production build output from `frontend/dist`.
- Set `VITE_API_BASE_URL` to the Render backend URL.
- Rebuild the site whenever the API URL changes.

### 3. Keep the API from sleeping
- If you are on a Render plan that can sleep, use an external uptime monitor against `GET /health`.
- A 5-minute ping interval is fine for monitoring, but it is not a guarantee on free tiers.
- If you need always-on behavior, use a paid web service instead of relying only on pings.

### 4. Run the daily automation pipeline
- Create a separate Render Cron Job for the pipeline.
- Run the existing automation script instead of writing a new pipeline entry point.
- Use `automation/run_daily_pipeline.sh` or directly run `automation/daily_pipeline.py` in the job command.
- Schedule it once per day after market close or at whatever time you want fresh data.

Suggested cron job command:
- `bash automation/run_daily_pipeline.sh`

### 5. Persist generated artifacts
- Attach persistent storage for `data/processed/` and `outputs/` if you want the latest models and reports to survive redeploys.
- The API reads model files and processed features from disk, so losing those files will degrade the service.
- If persistent disks are not available in your Render setup, move generated artifacts to external storage.

### 6. Verify the full production flow
- Open the backend `/health` endpoint.
- Confirm `/api/stocks` returns results.
- Confirm a sample `/api/stocks/{symbol}` and `/api/signal/{symbol}` response works.
- Open the frontend and verify it can fetch the API successfully.
- Run the daily pipeline once manually in Render before enabling the schedule.

### 7. Final production checks
- Confirm logs are readable in Render.
- Confirm the pipeline creates fresh files in `data/processed/` and `outputs/`.
- Confirm the frontend uses the correct backend URL.
- Confirm CORS accepts the Render frontend domain.