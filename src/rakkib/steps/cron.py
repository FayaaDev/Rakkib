"""Step 6 — Cron Jobs.

Install local backup scripts, backup scheduling, and lightweight health
monitoring jobs.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from rakkib.render import render_file
from rakkib.state import State
from rakkib.steps import VerificationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_dir() -> Path:
    """Return the package data directory (contains ``templates/``)."""
    return Path(__file__).resolve().parent.parent / "data"


def _crontab_lines(user: str | None = None) -> list[str]:
    """Return current crontab lines, or empty list if none."""
    cmd = ["crontab", "-l"] if user is None else ["crontab", "-u", user, "-l"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()


def _write_crontab(lines: list[str], user: str | None = None) -> None:
    """Write lines back to crontab."""
    cmd = ["crontab", "-"] if user is None else ["crontab", "-u", user, "-"]
    subprocess.run(cmd, input="\n".join(lines) + "\n", text=True, check=True)


def _install_cron_entry(
    lines: list[str],
    marker: str,
    schedule: str,
    command: str,
) -> list[str]:
    """Idempotently install or replace a single cron entry by marker."""
    new_lines: list[str] = []
    for line in lines:
        if line.endswith(marker):
            continue
        new_lines.append(line)
    new_lines.append(f"{schedule} {command}  {marker}")
    return new_lines


def _is_root() -> bool:
    return os.geteuid() == 0


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def run(state: State) -> None:
    repo = _repo_dir()
    data_root = Path(state.get("data_root", "/srv"))
    backup_dir = Path(state.get("backup_dir", str(data_root / "backups")))
    platform = state.get("platform", "linux")
    admin_user = state.get("admin_user")
    selected = set(state.get("selected_services", []) or [])

    backup_dir.mkdir(parents=True, exist_ok=True)
    healthchecks_dir = backup_dir / "healthchecks"
    healthchecks_dir.mkdir(parents=True, exist_ok=True)

    log_path = data_root / "logs" / "cron.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Render backup scripts ---------------------------------------------
    render_file(
        repo / "templates" / "backups" / "backup-local.sh.tmpl",
        backup_dir / "backup-local.sh",
        state,
    )
    render_file(
        repo / "templates" / "backups" / "restore-local.sh.tmpl",
        backup_dir / "restore-local.sh",
        state,
    )

    (backup_dir / "backup-local.sh").chmod(0o755)
    (backup_dir / "restore-local.sh").chmod(0o755)

    # --- Render healthcheck scripts ----------------------------------------
    healthcheck_scripts: list[Path] = []
    for tmpl in (repo / "templates" / "backups" / "healthchecks").glob("*.tmpl"):
        script_name = tmpl.name.replace(".tmpl", "")
        dst = healthchecks_dir / script_name
        render_file(tmpl, dst, state)
        dst.chmod(0o755)
        healthcheck_scripts.append(dst)

    # Copy healthcheck scripts to user bin dir for cron accessibility
    user_bin = Path.home() / ".local" / "bin"
    user_bin.mkdir(parents=True, exist_ok=True)
    for script in healthcheck_scripts:
        shutil.copy2(script, user_bin / script.name)
        (user_bin / script.name).chmod(0o755)

    # --- Install cron entries -----------------------------------------------
    crontab_user = admin_user if _is_root() and admin_user else None
    lines = _crontab_lines(crontab_user)

    # Backup schedule (default daily 02:30)
    backup_schedule = state.get("backup.schedule", "30 2 * * *")
    lines = _install_cron_entry(
        lines,
        "# RAKKIB: backup-local",
        backup_schedule,
        str(backup_dir / "backup-local.sh"),
    )

    # Cloudflared health check every 5 minutes
    cf_script = user_bin / "cloudflared-healthcheck.sh"
    if cf_script.exists():
        lines = _install_cron_entry(
            lines,
            "# RAKKIB: cloudflared-healthcheck",
            "*/5 * * * *",
            f"bash {cf_script}",
        )

    _write_crontab(lines, crontab_user)

    log_path.write_text("cron step completed\n")


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify(state: State) -> VerificationResult:
    data_root = Path(state.get("data_root", "/srv"))
    backup_dir = Path(state.get("backup_dir", str(data_root / "backups")))
    admin_user = state.get("admin_user")
    crontab_user = admin_user if _is_root() and admin_user else None

    for script in (backup_dir / "backup-local.sh", backup_dir / "restore-local.sh"):
        if not script.exists():
            return VerificationResult.failure("cron", f"Missing script {script}")
        if not os.access(script, os.X_OK):
            return VerificationResult.failure("cron", f"Script {script} is not executable")

    healthchecks_dir = backup_dir / "healthchecks"
    for script in healthchecks_dir.glob("*.sh"):
        if not os.access(script, os.X_OK):
            return VerificationResult.failure("cron", f"Healthcheck script {script} is not executable")

    # Verify cron entries exist
    lines = _crontab_lines(crontab_user)
    crontab_text = "\n".join(lines)

    required_markers = ["# RAKKIB: backup-local"]

    cf_script = Path.home() / ".local" / "bin" / "cloudflared-healthcheck.sh"
    if cf_script.exists():
        required_markers.append("# RAKKIB: cloudflared-healthcheck")

    for marker in required_markers:
        if marker not in crontab_text:
            return VerificationResult.failure("cron", f"Missing cron entry for {marker}")

    return VerificationResult.success("cron", "Cron jobs installed and scripts are executable")
