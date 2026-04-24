# Step 80 — Backups

Install the local-only backup script and backup schedule.

## Actions

1. Render `templates/backups/backup-local.sh.tmpl` into `{{BACKUP_DIR}}/backup-local.sh`.
2. Make it executable.
3. Choose a schedule with the user if none was provided. Default: daily at 02:30.
4. Install a cron entry or platform-equivalent job to run it.
5. Retain recent local archives only. Do not configure cloud upload in v1.

## Verify

- `test -x {{BACKUP_DIR}}/backup-local.sh`
- `{{BACKUP_DIR}}/backup-local.sh`
- `ls -1 {{BACKUP_DIR}} | grep fayaasrv`
