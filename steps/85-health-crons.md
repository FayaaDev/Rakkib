# Step 85 — Health Crons

Install lightweight health monitoring jobs.

## Actions

1. Always install the cloudflared health check.
2. If `openclaw` is selected, install the claw health check.
3. If `openclaw` is selected and the user wants memory alerts, install the memory alert helper.
4. Write the scripts to a user-owned directory such as `~/.local/bin` and make them executable.
5. Add cron entries with conservative cadence.

## Default Cadence

- cloudflared health check: every 5 minutes
- claw health check: every 5 minutes
- claw memory alert: every 10 minutes

## Verify

- `crontab -l`
- `bash ~/.local/bin/cloudflared-healthcheck.sh`
- if selected: `bash ~/.local/bin/claw-healthcheck.sh`
