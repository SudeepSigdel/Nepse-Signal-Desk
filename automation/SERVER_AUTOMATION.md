# Server Automation

You can run the full scrape + pipeline automatically on your hosted server.

## Option 1: Cron (simple)

1. Upload project to server (example path: `/opt/final-year-project`).
2. Ensure venv exists at `/opt/final-year-project/venv`.
3. Make scripts executable:
   - `chmod +x automation/run_daily_pipeline.sh`
   - `chmod +x automation/install_cron.sh`
4. Install cron entry (default 16:30 daily):
   - `PROJECT_ROOT=/opt/final-year-project RUN_AT=16:30 SOURCE=sharesansar DELAY=0.2 ./automation/install_cron.sh`

Logs:
- `outputs/logs/cron_daily_pipeline.log`
- `outputs/logs/daily_pipeline_*.log`

## Option 2: systemd timer (recommended for VPS)

1. Copy templates:
   - `sudo cp automation/systemd/nepse-daily-pipeline.service /etc/systemd/system/`
   - `sudo cp automation/systemd/nepse-daily-pipeline.timer /etc/systemd/system/`
2. Edit service file values if needed:
   - `WorkingDirectory`
   - `Environment=PROJECT_ROOT`
   - `User` and `Group`
3. Enable timer:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now nepse-daily-pipeline.timer`
4. Check status:
   - `systemctl status nepse-daily-pipeline.timer`
   - `systemctl list-timers | grep nepse-daily-pipeline`

Manual run:
- `sudo systemctl start nepse-daily-pipeline.service`

## Notes

- The runner sets `MPLBACKEND=Agg` so scripts using matplotlib can run headless.
- A lock file prevents overlapping runs.
- If your host is shared hosting (no cron/systemd), use provider scheduled jobs and execute:
  - `/bin/bash /opt/final-year-project/automation/run_daily_pipeline.sh`
